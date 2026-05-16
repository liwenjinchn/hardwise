# Hardwise Architecture

> v0.6 — Review runs now append a machine-readable `trace.jsonl` record beside the report. This gives rules-list / demo / audit views a stable source of truth instead of parsing CLI stdout.

## Data flow

```
KiCad project ─┐
               ├─→ adapters/kicad.py ─→ store/relational.py (SQLite)
                                              │
Datasheet PDFs ─→ ingest/pdf.py     ─→ store/vector.py (Chroma)
                                              │
                                              ▼
                                       agent/runner.py  ←─ tools.py
                                              │
                                              ▼
                                       guards/refdes.py + guards/evidence.py
                                              │
                                              ▼
                                       reports/<project>-<date>.md
                                              │
                                              ├─→ trace.jsonl (run record)
                                              │
                                              ▼
                                       memory/consolidator.py → memory/rules.md
```

## Modules (one paragraph each as they ship)

### `adapters/`
Adapter pattern at the EDA boundary. `base.py` defines the first stable data shapes: `ComponentRecord` and `BoardRegistry`. `kicad.py` is the v0.1 implementation: it parses KiCad S-expression files directly, extracts schematic symbol instances plus PCB footprints, and merges them into a refdes registry. Future `cadence.py` is one new file, not a rewrite. Borrowed from Wrench Board's "adding a format = one new file" boardview parser pattern.

#### Day 2 shipped module I/O

| Module / function | Purpose | Input | Output | Why it exists | Verification |
|---|---|---|---|---|---|
| `ComponentRecord` in `adapters/base.py` | Standard shape for one parsed component-like item | One symbol or footprint parsed from EDA files | Pydantic object with `refdes`, `value`, `footprint`, `datasheet`, `source_file`, `source_kind` | Keeps schematic, PCB, and future Cadence data in the same shape | Constructed indirectly by parser tests |
| `BoardRegistry` in `adapters/base.py` | Reliable refdes registry for tools and guards | A project directory plus parsed component records | `components` list + `refdes_set` + `has_refdes()` | This is the future source of truth for Refdes Guard; model output must be checked against it | Test asserts `U3/C1/D11` exist and `U999` does not |
| `parse_schematic(path)` in `adapters/kicad.py` | Read KiCad schematic symbol instances | `.kicad_sch` text file | List of `ComponentRecord(source_kind="schematic")` | Schematic owns logical design intent: reference, value, datasheet, declared footprint | Covered by `test_parse_pic_programmer_registry` |
| `parse_pcb(path)` in `adapters/kicad.py` | Read placed PCB footprints | `.kicad_pcb` text file | List of `ComponentRecord(source_kind="pcb")` | PCB owns placed package footprint; can backfill or cross-check schematic footprint | Covered by `test_merges_pcb_footprint_into_schematic_record` |
| `parse_project(project_dir)` in `adapters/kicad.py` | Merge schematic and PCB views into one registry | KiCad project directory containing `.kicad_sch` / `.kicad_pcb` | `BoardRegistry` sorted for human-readable CLI output, including `pcb_nets` when a PCB file exists | Agent tools should ask one registry, not parse files ad hoc every time | `inspect-kicad` extracts 121 registry items from `pic_programmer` |
| `parse_pcb_nets(path)` in `adapters/kicad.py` | Read already-laid-out PCB connectivity | `.kicad_pcb` text file | `PcbNetRecord` list with `(refdes, pad)` members | Diagnostic only: this is post-Layout data, not legal pre-Layout schematic-review evidence | Tests lock 111 PCB nets on `pic_programmer` |
| `inspect-kicad` in `cli.py` | Human-visible smoke test for EDA ingestion | Project path + optional print limit, plus optional `--net` | Registry count and first N components, or PCB-side net summary | Lets user see the parser result without reading code or opening KiCad | `uv run hardwise inspect-kicad data/projects/pic_programmer --net` |

**Hardware-engineer explanation:** this module is the project's 位号台账 plus a PCB-side diagnostic net reader. Before AI can review a board, it must know which U/C/R/D/J designators really exist. The parser turns KiCad files into that trusted table. Later, if the model says "U999 has a decoupling issue", Refdes Guard can reject it because `U999` is not in `BoardRegistry`.

**What it does not do yet:** it does not parse schematic-side nets, BOM rows, DRC/ERC results, or datasheet PDFs. `pcb_nets` come from `.kicad_pcb` and are post-Layout diagnostics only; R005/R006/R007 need a separate `.kicad_sch` parser that resolves wires, labels, power symbols, hierarchical labels, and symbol pin endpoints.

**Slice 1 work item (per PLAN DR-008):** `parse_project()` currently merges `.kicad_pcb` footprints into `.kicad_sch` records when the schematic field is empty (see `kicad.py:30-31`). This backfill is correct for Refdes Guard but **breaks R001's "footprint-empty → new-component candidate" judgement** — every PCB-laid-out part stops looking new. Slice 1 must either (a) add `BoardRegistry.schematic_records` / `pcb_records` raw fields and have R001 read `schematic_records`, or (b) have R001 bypass `BoardRegistry` and call `parse_schematic` directly. Pick one in Slice 1, document the choice here.

### `checklist/`
Slice 1 ships:
- `loader.py` — reads `data/checklists/sch_review.yaml` into `RuleSpec` Pydantic models. `RuleSpec.status` filters out `planned`/`deprecated` rules at load time; agent only sees `active` ones.
- `finding.py` — defines the **`Finding` Pydantic model**, the shared contract used by every rule, every guard, and the report writer:
  ```
  Finding(
      rule_id: str,            # "R001" | "R002" | ...
      severity: Literal["critical","high","medium","low","info"],
      refdes: str | None,      # may be None for net-relation findings
      net: str | None,         # may be None for refdes-only findings
      message: str,            # the human-readable problem statement
      evidence_tokens: list[str],  # ["sch:pic_programmer.kicad_sch#U23", "datasheet:PIC16F876.pdf#p23", ...]
      suggested_action: str,
      status: Literal["open","accepted","rejected","closed"] = "open",
  )
  ```
  Every `check_function` returns `list[Finding]`. Refdes Guard inspects `findings[].refdes` and `findings[].message` for hallucinated tokens. Evidence Ledger rejects any `Finding` with empty `evidence_tokens`. Markdown report iterates `findings` to render one row per finding aligned to《SCH_review_feedback_list 汇总表》.
- `checks/r001_new_component_candidate.py` — first concrete rule.

Slice 2 ships:
- `checks/r002_cap_voltage_derating.py` — **scope intentionally narrow**: only the value-side rated-voltage parse. Each cap (`C*`, skipping `#PWR*` and `value=""` / `value="0"`) becomes either:
  - **`info` finding** when `value` carries `/<num>V` (regex `r"/\s*(\d+(?:\.\d+)?)\s*V\b"`) — reviewer must manually confirm the 80% rule against the cap's net's working voltage.
  - **`medium` finding** when `value` lacks the suffix — the rule cannot be evaluated; ask the schematic author to suffix `/<num>V`.
  The `high` branch (full 80% derating comparison) is **deferred to Slice 3+**: it needs `working_voltage` from a KiCad net parser, which is not yet built. The yaml `R002.rule` text reflects this two-stage split so the rule doc never lies about what the code actually does. Same DR-008 raw-schematic input contract as R001.
- Slice 3+ adds `checks/r003_*.py` etc.; no new finding shape allowed (per DR-008).

Slice 3 ships:
- `checks/r003_nc_pin_handling.py` — **EDA-only stage**. Consumes `BoardRegistry.nc_pins` (populated by `adapters/kicad_pins.py`) and emits one medium finding per pin marked NC in the schematic. Severity is medium because the Slice 3 check cannot tell whether NC is correct without datasheet semantic comparison; the message and `suggested_action` push the reviewer to verify against the datasheet. The `high` branch (datasheet contradicts schematic NC handling) is **deferred to Slice 4+**: it needs vector-store semantic query against `datasheet.section.NC_pin_handling`. The yaml `R003.rule` text reflects this two-stage split, mirroring the R002 pattern.

### `adapters/kicad_pins.py` (Slice 3)
Pin + no_connect parser, split from `kicad.py` to stay under the 300-line module limit. Verified algorithm:
- `pin.at` in `lib_symbols` IS the connectable endpoint (wire attachment point). `length` is geometry only — do NOT add `length × direction`.
- Absolute position = `symbol_at + rotate(pin.at, symbol_rotation_deg)`; standard 2D rotation; tolerance 0.01 mm.
- Multi-unit symbols: `<libname>_<unit>_<bodystyle>`; instance's `(unit N)` selects unit-N + shared unit-0 pins.

Public surface: `parse_nc_pins(path: Path) -> list[NcPinRecord]`. `parse_project()` calls it on every `*.kicad_sch` and populates `BoardRegistry.nc_pins`. On `pic_programmer`: 6 NC pins on the main sheet (J1 DB9 pins 4/5/6/9 + LT1373/U4 pins FB- and S/S) + 71 NC pins on `pic_sockets.kicad_sch` (PIC socket area) = 77 total. The pre-existing `grep -c no_connect` count is 77; the parser is exact, not approximate.

See `docs/learning_log.md` (2026-05-12 entry) for the anchor-convention debugging story.

### `store/` (Slice 3)
Two storage backends — relational for refdes-keyed structured data, vector for datasheet text.

- `relational.py` — SQLite via SQLAlchemy 2.0 ORM. Tables: `components` (refdes unique-indexed, plus value/footprint/datasheet/source_file/source_kind), `nc_pins` (refdes, pin_number, pin_name, pin_electrical_type, source_file), `pcb_nets`, and `pcb_net_members`. Public API: `create_store(db_path) -> Session`, `populate_from_registry(session, registry) -> (n_comp, n_pin)`, `query_components(session) -> list[ComponentRecord]`, `query_nc_pins(session) -> list[NcPinRecord]`, `query_pcb_nets(session) -> list[PcbNetRecord]`. `populate_from_registry` truncates first → idempotent over reruns of the same project. The R003 check does NOT read from SQLite — it consumes the in-memory `BoardRegistry`; the store is a parallel proof that the data round-trips through a relational backend and refdes is queryable. `pcb_nets` are explicitly post-Layout data and must not feed pre-Layout schematic-review rules.
- `vector.py` — Chroma 0.5+ local persistent mode. Default embedder is the bundled ONNX `all-MiniLM-L6-v2` (no separate `sentence-transformers` install needed; see `docs/learning_log.md` 2026-05-12). Public API: `create_collection(persist_dir, name) -> Collection`, `ingest_chunks(collection, chunks, part_ref) -> int`, `query_chunks(collection, query, top_k) -> list[dict]`. Each ingested chunk metadata: `{part_ref, source_pdf, page, chunk_index}`. `part_ref` is the join key with the relational store — a finding can reference both `sch:<file>#<refdes>` and `datasheet:<pdf>#p<N>` evidence tokens, and the refdes is the same on both sides.

### `ingest/` (Slice 3)
- `pdf.py` — `extract_chunks(pdf_path, chunk_size=500, overlap=100) -> list[ChunkRecord]`. Uses `pdfplumber` for page-level text extraction; each page is split into one or more overlapping chunks via `_split_text`. `ChunkRecord` carries `(text, source_pdf, page, chunk_index)` and a `.evidence_token` property formatted `datasheet:<filename>#p<N>`.

### `agent/` (Slice 3 — router; Slice 4 — tools + runner + prompts)
- `router.py` — `ModelRouter(env).select(tier)`. Reads `HARDWISE_MODEL_FAST/NORMAL/DEEP` from the env dict (default `os.environ`); falls back to NORMAL if the requested tier is unset, then to `mimo-v2.5` if NORMAL is also unset. `verify-api --tier {fast,normal,deep}` and `ask --tier` exercise it end-to-end. The agent code never hard-codes a model id — tier selection lives here, model id lives in `.env`.
- `tools.py` — Slice 4 prep: tool manifest for the tool-use loop. Four tools wired against the Slice 3 stores: `list_components` (relational read with optional value-substring / refdes-prefix filter), `get_component` (single-refdes lookup with a `Found{component}` / `NotFound{refdes, closest_matches}` discriminated-union return — `closest_matches` comes from `difflib.get_close_matches` over `BoardRegistry.refdes_set`, so the agent picks from suggestions, never fabricates), `get_nc_pins` (relational read, optional refdes filter), `search_datasheet` (Chroma vector query, optional `part_ref` filter, returns `DatasheetHit[]` with `page` + `source_pdf` + `part_ref` provenance). Inputs and outputs are Pydantic models; `TOOL_DEFINITIONS` exposes them in Anthropic-SDK `tools=[…]` shape consumed by runner.py. The module is the front-door for mechanisms #1 (Refdes Guard receives `closest_matches` here) and #2 (Evidence Ledger receives `source_pdf` + `page` here).
- `prompts.py` — Slice 4: the static system prompt. Spells out role + 4-tool catalogue + anti-fabrication rules + evidence discipline + Chinese-by-default output convention. `build_system_blocks()` wraps the prompt in a single `cache_control: ephemeral` text block — the upstream proxy (or Claude proper) can serve it from prompt cache across iterations. Mechanism #5 wiring lives here.
- `runner.py` — Slice 4: `Runner(client, router, session, registry, collection?, tier="normal")`. `run(user_message) -> RunResult` runs the finite tool-use loop — `messages.create(tools=TOOL_DEFINITIONS, system=cache_control_blocks, ...)`, dispatches `tool_use` blocks to the tools.py functions, feeds `tool_result` back, capped at `MAX_ITERATIONS=10`. Accumulates `input_tokens / output_tokens / cache_creation_tokens / cache_read_tokens` from each `response.usage`; returns a `ToolCallTrace[]` for audit. `collection=None` makes `search_datasheet` return a structured "not configured" payload — the agent learns to back off without crashing. Unknown tools and tool exceptions surface as `is_error=True` tool_result blocks so the model can self-correct.
- `cli.py:ask` — Slice 4: `hardwise ask <project_dir> "<question>"` builds session+registry, optionally opens Chroma (`--vector`), constructs Runner, prints answer + per-tool trace + token line (including cache create/read when nonzero). Live verified on MiMo-V2.5 via `xiaomimimo.com/anthropic`: `cache_read_input_tokens` ≠ 0 on three pic_programmer queries, confirming mechanism #5 has real numbers, not just wiring (see `learning_log.md` 2026-05-13 entry). A 2026-05-16 cold-start probe further showed immediate read hits (`cache_read_input_tokens=5440`) but MiMo leaves `cache_creation_input_tokens` null, so creation accounting requires another endpoint to verify.

### `run_trace.py`
Append-only JSONL trace for `hardwise review`. `ReviewRunSummary` collects structured facts inside the CLI before rendering the trace; `build_review_trace()` turns that summary into one stable Pydantic object: requested/running rules, report path, component and NC-pin counts, finding totals grouped by rule/severity/decision, guard counters, vector flag, store result, and consolidator result. `append_jsonl()` writes one JSON object per line to `<report-dir>/trace.jsonl` by default; `review --trace-output PATH` redirects it and `--no-run-trace` disables it. Trace write failures warn on stderr but do not fail the review, because the report is the primary artifact. P0 stores paths as supplied by the CLI and assumes single-process writes (no file lock). This is intentionally not a report renderer: it is the machine-readable run ledger that later `rules list` and CLI split work can consume without scraping human text.

### `guards/`
- `refdes.py` — defense layer 1: regex-scan output for refdes-shaped tokens (`\b[A-Z]{1,3}\d{1,4}\b`); verify each against the EDA registry; mark unverified as `⟨?XX99⟩`. Mirrors Wrench Board's `api/agent/sanitize.py`.
- `evidence.py` — defense layer 2: every claim must carry a source token; strip claims without tokens before the report is written.

### `memory/`
- `consolidator.py` — Sleep Consolidator (Slice 2 minimum). Pure statistical aggregation: groups findings by `(rule_id, severity)`; emits one `CandidateRule` per bucket whose count meets the `_THRESHOLD = 3`. Each emitted candidate becomes an appended block in `memory/rules.md` with `STATUS: candidate`, a project slug, a timestamp, and a suggested action (template-table lookup; falls back to a generic "produced N findings, worth investigating" when no template matches). No LLM, no embeddings, deterministic over the same input + pinned timestamp. Public signature: `consolidate(findings, project_slug, output_path=Path("memory/rules.md"), now=None) -> list[CandidateRule]`.
- `rules.md` — candidate-rule pool (gitignored under `memory/*.md`). The header explains the human gate: **candidates never auto-promote**. Promotion is a human action — edit the file, then migrate the candidate to `data/checklists/sch_review.yaml` with `status: active`.
- Slice 3+ will add smarter pattern extraction (rolling-log triggered). Slice 2's threshold-based stats is intentionally minimal — proves the mechanism without expanding scope.

## Why this shape

- **Adapter** at EDA boundary so Cadence/Allegro is a one-file extension
- **Two stores** because vector and relational have different query semantics; mixing them destroys refdes-as-join-key
- **Tool-discipline + guards**: anti-hallucination is enforced *structurally* (registry lookup + sanitizer) not by prompt-engineering
- **Memory consolidation with human gate**: rules cannot self-promote; protects against memory pollution
- **Tiered routing**: cheap models handle deterministic intent / lookup, expensive models reserved for actual reasoning

## Five mechanisms × file map

| Mechanism | Lives in |
|---|---|
| 1. Refdes Guard | `guards/refdes.py` + `agent/tools.py:get_component` (closest_matches) |
| 2. Evidence Ledger | `guards/evidence.py` + `agent/tools.py:search_datasheet` (source_pdf + page) + `agent/prompts.py` |
| 3. Sleep Consolidator | `memory/consolidator.py` + `memory/rules.md` |
| 4. Tiered Model Routing | `agent/router.py` + `.env` (`HARDWISE_MODEL_FAST/NORMAL/DEEP`) |
| 5. Prompt Caching | `agent/prompts.py:build_system_blocks` (cache_control=ephemeral) + `agent/runner.py` token accounting |

## KiCad file structure notes

> Day 1 task #4: open a real `.kicad_sch` from `data/projects/<chosen>` and document where elements / nets / BOM fields live. Fill below.

### `.kicad_sch` (schematic, S-expression)
Key token: instance-level `(symbol ...)` nodes containing `(property "Reference" "U1" ...)`, `(property "Value" "...")`, `(property "Footprint" "...")`, `(property "Datasheet" "...")`. Library symbol definitions also use `(symbol ...)`, so the parser must skip library definitions where the second item is a symbol name string like `"pic_programmer:74LS125"`.

### `.kicad_pcb` (board layout, S-expression)
Key token: `(footprint "Package:Name" ...)` nodes with child properties `Reference`, `Value`, `Datasheet`. The first parser uses PCB footprints to backfill missing schematic footprints and to catch placed board items. Nets and tracks remain TBD.

### `.net` / BOM CSV
TBD — KiCad's BOM is CSV-exported via plugin; document the columns we care about.

### `.drc` / `.erc` reports
TBD — text-format output from KiCad's design rule check; document parseable fields.

## Current CLI surface

```bash
uv run hardwise hello
uv run hardwise verify-api --tier normal
uv run hardwise inspect-kicad data/projects/pic_programmer --limit 25
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003 --no-consolidate
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003 --memory-output /tmp/rules.md
uv run hardwise review data/projects/pic_programmer --rules R003 --db-path /tmp/pic.db
uv run hardwise review data/projects/pic_programmer --rules R003 --trace-output /tmp/trace.jsonl
uv run hardwise ingest-datasheet data/datasheets/l78.pdf --part-ref U3
uv run hardwise query-datasheet "absolute maximum input voltage" --top-k 3
uv run hardwise ask data/projects/pic_programmer "U3 是什么器件？"
uv run hardwise ask data/projects/pic_programmer "U4 这颗器件有几个 NC 脚？" --max-iterations 6
uv run hardwise ask data/projects/pic_programmer "找一下 U3 最大输入电压" --vector
```

`inspect-kicad` is the first EDA adapter demo: it prints the registry count and the first N sorted components. On `pic_programmer`, it extracts 121 registry items.

`review` runs the requested rules over the schematic-side records, applies Refdes Guard + Evidence Ledger, writes a markdown report aligned to《SCH_review_feedback_list 汇总表》, and (by default) appends Sleep Consolidator candidates to `memory/rules.md`, populates a SQLite store at `reports/<project>.db` with components + NC pins, and appends one machine-readable run record to `trace.jsonl`. On `pic_programmer` with `--rules R001,R002,R003`, the output is 84 findings (7 R002 + 77 R003) and 2 candidate rules (R002 medium + R003 medium). `--no-consolidate` skips the memory write; `--memory-output PATH`, `--db-path PATH`, and `--trace-output PATH` redirect their respective outputs.

`ingest-datasheet` chunks a PDF page-by-page and upserts into Chroma at `data/chroma/` (default), tagging every chunk with `part_ref=<refdes>`. `query-datasheet` runs a top-k semantic query and prints `[source_pdf pN part=Ux]` provenance — these are the building blocks for the Slice 4 `datasheet:<pdf>#p<N>` evidence token.

`verify-api --tier {fast,normal,deep}` exercises the `ModelRouter` against the upstream API and prints the resolved model id + token counts.

`ask <project_dir> "<question>"` is the Slice 4 entry point to the agent loop: parses the KiCad project, builds an in-memory SQLite session + registry, optionally opens a Chroma collection (`--vector`), constructs a `Runner`, runs `messages.create(tools=TOOL_DEFINITIONS, ...)` in a finite tool-use loop, and prints the answer + one line per tool call + a token line (including `cache_create/read` when nonzero). Three live runs on pic_programmer with `mimo-v2.5` exercise (1) known-refdes `get_component`, (2) unknown-refdes `get_component → ComponentNotFound` (model honors anti-fabrication), and (3) `get_nc_pins --refdes_filter U4` returning 2 NC pins — all three runs report nonzero `cache_read_input_tokens`.

## Module explanation template

Every shipped module should be documented with this minimum:

1. **Purpose** — what hardware workflow step it automates.
2. **Input** — exact files, CLI arguments, database rows, or tool calls it consumes.
3. **Output** — exact object, file, table row, report section, or CLI text it produces.
4. **Why this design** — why this module exists instead of being folded into another one.
5. **Verification** — command or test that proves it works.
6. **Interview sentence** — one concise sentence the author can say in an interview.
