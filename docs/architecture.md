# Hardwise Architecture

> v0.3 — Slice 2 ships R002 (cap rated-voltage field completeness) + Sleep Consolidator. Sections marked TBD fill in as modules ship.

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
| `parse_project(project_dir)` in `adapters/kicad.py` | Merge schematic and PCB views into one registry | KiCad project directory containing `.kicad_sch` / `.kicad_pcb` | `BoardRegistry` sorted for human-readable CLI output | Agent tools should ask one registry, not parse files ad hoc every time | `inspect-kicad` extracts 121 registry items from `pic_programmer` |
| `inspect-kicad` in `cli.py` | Human-visible smoke test for EDA ingestion | Project path + optional print limit | Registry count and first N components | Lets user see the parser result without reading code or opening KiCad | `uv run hardwise inspect-kicad data/projects/pic_programmer --limit 10` |

**Hardware-engineer explanation:** this module is the project's 位号台账. Before AI can review a board, it must know which U/C/R/D/J designators really exist. The parser turns KiCad files into that trusted table. Later, if the model says "U999 has a decoupling issue", Refdes Guard can reject it because `U999` is not in `BoardRegistry`.

**What it does not do yet:** it does not parse nets, BOM rows, DRC/ERC results, or datasheet PDFs. It only establishes the component registry foundation.

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

### `store/`
- `relational.py` — SQLite via SQLAlchemy. Tables: `components`, `nets`, `bom_rows`, `drc_findings`. Refdes is the join key.
- `vector.py` — Chroma local mode. Holds datasheet chunks with metadata `(part_no, page, source_pdf, section)`.

### `agent/`
- `tools.py` — tool definitions for the Claude tool-use loop. Each tool takes a Pydantic input model, returns a Pydantic output model, and is registered in a single manifest.
- `runner.py` — main loop: pick model tier (mechanism 4), call tools, assemble report.
- `prompts.py` — system prompts and review templates. The "no claim without source token" rule is encoded here, then enforced by `guards/`.

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
| 1. Refdes Guard | `guards/refdes.py` |
| 2. Evidence Ledger | `guards/evidence.py` + `agent/prompts.py` |
| 3. Sleep Consolidator | `memory/consolidator.py` + `memory/rules.md` |
| 4. Tiered Model Routing | `agent/runner.py` + `.env` (`HARDWISE_MODEL_FAST/NORMAL/DEEP`) |
| 5. Prompt Caching | `agent/runner.py` (Anthropic `cache_control` in system prompt + datasheet blocks) |

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
uv run hardwise verify-api
uv run hardwise inspect-kicad data/projects/pic_programmer --limit 25
uv run hardwise review data/projects/pic_programmer --rules R001,R002
uv run hardwise review data/projects/pic_programmer --rules R001,R002 --no-consolidate
uv run hardwise review data/projects/pic_programmer --rules R001,R002 --memory-output /tmp/rules.md
```

`inspect-kicad` is the first EDA adapter demo: it prints the registry count and the first N sorted components. On `pic_programmer`, it currently extracts 121 registry items.

`review` runs the requested rules over the schematic-side records, applies Refdes Guard + Evidence Ledger, writes a markdown report aligned to《SCH_review_feedback_list 汇总表》, and (by default) appends Sleep Consolidator candidates to `memory/rules.md`. On `pic_programmer` with `--rules R001,R002`, the output is 7 findings (6 medium + 1 info, all R002) and 1 candidate rule emitted. `--no-consolidate` skips the memory write; `--memory-output PATH` redirects it (used by tests).

## Module explanation template

Every shipped module should be documented with this minimum:

1. **Purpose** — what hardware workflow step it automates.
2. **Input** — exact files, CLI arguments, database rows, or tool calls it consumes.
3. **Output** — exact object, file, table row, report section, or CLI text it produces.
4. **Why this design** — why this module exists instead of being folded into another one.
5. **Verification** — command or test that proves it works.
6. **Interview sentence** — one concise sentence the author can say in an interview.
