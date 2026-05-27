# Hardwise Architecture

> v1.5 — V3.3 adds deterministic XL1509 buck-converter validation. Allegro netlists provide topology; BOM rows provide component identity by refdes join; an optional CSV/TSV document index maps BOM item identity to public datasheet/document links; profile JSON carries per-pin name/category/function/limits/recommended-topology/evidence facts plus profile-level recommended DCDC limits; `validation/component.py` orchestrates pin checks and family-specific topology checks; `validation/dcdc.py` checks XL1509 output-net inductor and freewheel-diode facts; `report/validator_ui.py` wraps the same deterministic facts in a component index + detail-pane HTML artifact. `.brd`, boardview, placement, routing, PCB geometry, live supplier lookup, lifecycle/pricing/availability, hosted app state, and PLM-grade BOM governance remain out of scope.

## Data flow

```
KiCad project ─┐
               ├─→ adapters/kicad.py ─→ store/relational.py (SQLite)
Allegro schematic netlist ─→ adapters/allegro_netlist.py / allegro_pst.py ─→ ir/build.py
Allegro schematic BOM ─────→ bom/parser.py + bom/matcher.py
                                              │
Local document index CSV/TSV ─→ documents/index.py + documents/matcher.py
                                              │
                                              ├─→ report/allegro_bom_markdown.py
                                              │   + report/allegro_document_markdown.py
                                              │   → reports/*-bom-intake-*.md
                                              │
Datasheet PDFs ─→ ingest/pdf.py     ─→ store/vector.py (Chroma)
               └─→ ir/profile.py    ─→ report/pin_profile_markdown.py
                         │
                         └─→ validation/component.py
                                ↑
Allegro schematic topology + optional BOM identity ───────────────┘
                                │
                                └─→ report/component_validation_markdown.py
                                      + report/validator_ui.py
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
Adapter pattern at the EDA boundary. `base.py` defines the first stable KiCad registry shapes: `ComponentRecord` and `BoardRegistry`. `kicad.py` parses KiCad S-expression files directly, extracts schematic symbol instances plus PCB footprints, and merges them into a refdes registry. V2.5 adds two Allegro schematic-netlist adapters: `allegro_netlist.py` parses Telesis third-party ASCII netlists (`$PACKAGES`, optional `$A_PROPERTIES`, `$NETS`), and `allegro_pst.py` parses Capture/Allegro PST handoff files (`pstxprt.dat`, `pstxnet.dat`, optional `pstchip.dat`). Both feed IR aggregation without parsing PCB data. Borrowed from Wrench Board's "adding a format = one new file" parser pattern, but Hardwise does not copy Wrench Board code.

### `bom/`
Component identity matching layer for schematic-exported BOMs. `parser.py` reads Cadence-style tabular `.BOM` reports plus simple CSV/TSV exports, expands grouped reference cells (`R1,R2` and multiline continuations) into one `BomRow` per refdes, and preserves value/manufacturer/part-number fields when present. `matcher.py` joins those rows to `Design.components` by refdes and reports matched, BOM-only, design-only, duplicate, and quantity-mismatch cases; `apply_bom_to_design()` can attach identity fields without changing pins, nets, or topology. This is a pre-Layout component-matching aid, not PLM, pricing, lifecycle, supplier-risk, or PCB parsing.

### `documents/`
Local datasheet/document indexing layer for netlist-only Allegro review intake. `index.py` parses a user-supplied CSV/TSV document index with flexible aliases for MPN, manufacturer, value, title, and URL/path columns; each row gets a short `doc:<file>#line<N>` source token. `matcher.py` matches each BOM item group by MPN first, or by a part-like value when MPN is absent, then filters by manufacturer when both sides provide it. The result is an explicit evidence state (`matched`, `no_result`, `ambiguous`, or `manual_needed`) for each BOM item. It never fetches live supplier data and never judges lifecycle, pricing, availability, or electrical correctness.

### `report/`
Human-readable report renderers. `markdown.py` and `html.py` render checklist findings, while `component_markdown.py` groups KiCad review findings by component. `allegro_bom_markdown.py` renders `Design + BomMatchReport` as a component-centric intake artifact: prefix-level counts, BOM item groups, mismatch sections, and an optional full component table with refdes, BOM match status, value/MPN/manufacturer/package, connected pin count, bounded net list, BOM source row, and design source token. V2.8 adds `summary_only` and `mismatch_only` modes so a 4000-component design can be triaged before opening the full table. V2.9 adds `allegro_document_markdown.py`, which renders optional datasheet/document match summary and per-BOM-item document rows when `report-allegro-bom --document-index` is supplied. V3.0 adds `pin_profile_markdown.py`, a structured datasheet pin facts report for `DatasheetProfile.pins`. V3.1 adds `component_validation_markdown.py`, which renders one selected component's pin-level PASS/WARN/ERROR rows from deterministic validation output. V3.2 adds `validator_ui.py`, a self-contained static HTML artifact with component index, selected validation detail, schematic-net topology pane, scope boundary pane, and a markdown download link. The intake/profile reports remain factual artifacts; component validation is the first narrow electrical judgement layer and is limited to schematic pins, inferred net voltages, and structured profile limits.

### `ir/profile.py`
Structured datasheet profile models. `DatasheetProfile` keeps the older scalar maps (`abs_max`, `recommended`, `pin_function`) used by DS001, and V3.0 adds `PinProfile` rows for per-pin facts: pin number, pin name, category, function, limits, recommended topology, and evidence tokens. This keeps profile data deterministic and source-tokened before V3.1 pin-level PASS/WARN/ERROR validation consumes it.

### `validation/`
Deterministic component validation layer. `component.py` joins one `Design.components[refdes]` record, optional BOM identity already attached by `apply_bom_to_design()`, and one structured `DatasheetProfile`. `pins.py` owns generic pin rules: profiled pin presence, connected net presence, recognized ground nets, power-input voltage against structured min/max/abs-max limits, fixed power-output nominal voltage checks, feedback net voltage checks, enable-pin voltage checks, and explicit WARN for unsupported categories. `dcdc.py` is the first family-specific topology template: when a profile declares `recommended.topology_family="buck"` or part `XL1509-12E1`, it validates the switch-output net for an inductor and a freewheel diode, then classifies obvious Schottky/non-Schottky diode families and inductor value range from BOM identity. `types.py` keeps the shared `ValidationReport` shape; pin counts remain pin-only for backward compatibility, while `component_checks` records topology/peripheral results. This layer does not inspect PCB layout, boardview, placement, routing, supplier data, PLM, lifecycle, pricing, or availability.

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
| `parse_allegro_netlist(path)` in `adapters/allegro_netlist.py` | Read schematic topology from Allegro/Telesis text netlists | `.net` / `.txt` third-party ASCII netlist with `$PACKAGES` + `$NETS` | `AllegroNetlistRegistry` with packages, optional properties, nets, and `refdes_set` | Proves the IR is not KiCad-only while staying inside pre-Layout schematic-review evidence | 11 adapter tests cover quoted names, `$A_PROPERTIES`, continuation, duplicate/unknown refdes errors |
| `build_design_from_netlist(registry)` in `ir/build.py` | Aggregate Allegro netlist records into V2 IR | `AllegroNetlistRegistry` | `Design(source_eda="allegro_netlist")` with components, nets, connected pins | Keeps parsing and semantic aggregation separate; datasheet fields stay empty instead of guessed | 7 IR tests cover component count, pins, nets, and duplicate pin-on-two-nets rejection |
| `parse_allegro_pst(path)` in `adapters/allegro_pst.py` | Read schematic topology from Capture/Allegro PST exports | Directory or member file containing `pstxprt.dat` + `pstxnet.dat`, with optional `pstchip.dat` | `AllegroPstRegistry` with placed parts, nets, pin names, primitive properties, and `refdes_set` | Covers the common OrCAD/Capture-to-Allegro handoff format while staying pre-Layout | 7 adapter tests plus a public smoke parse of 4010 components / 3422 nets |
| `build_design_from_pst(registry)` in `ir/build.py` | Aggregate PST records into V2 IR | `AllegroPstRegistry` | `Design(source_eda="allegro_netlist")` with components, nets, connected pins, and primitive properties | Reuses the same component-centric IR for both Allegro text formats | 6 IR tests cover property mapping, pin names, nets, and duplicate pin-on-two-nets rejection |
| `inspect-allegro-netlist` in `cli.py` | Human-visible smoke test for V2.5 adapter | Telesis netlist path, PST directory, or PST member file + optional net print limit | Component/net/property counts plus largest nets | Shows netlist topology without implying `.brd` or boardview support | Synthetic Telesis fixture; synthetic PST fixture; public PST directory smoke |
| `parse_bom(path)` in `bom/parser.py` | Read schematic-exported BOM identity rows | Cadence `.BOM`, CSV, or TSV with Reference/Quantity/Part fields | `Bom` with grouped `BomItem`s and expanded one-refdes `BomRow`s | Netlist-only inputs need value/MPN identity separate from topology | Parser tests cover multiline Reference cells, digitless refdes like `VA`, CSV identity columns, and invalid quantities |
| `match_bom_to_design(bom, design)` in `bom/matcher.py` | Join BOM identity to schematic topology | Parsed `Bom` + `Design.components` registry | `BomMatchReport` with matched, BOM-only, design-only, duplicate, quantity-mismatch lists | Keeps BOM matching deterministic and registry-verified before any agent/report use | Matcher tests cover clean match, missing/extra refdes, duplicate BOM refs, quantity mismatch, and non-topology identity attachment |
| `inspect-bom-match` in `cli.py` | Human-visible smoke test for V2.6 matcher | Allegro netlist/PST input + schematic BOM path | Refdes counts, mismatch counts, and bounded mismatch samples | Answers "does this netlist+BOM pair line up?" without claiming PLM governance | Synthetic PST fixture plus public PST+BOM smoke: 4010 design refdes / 4010 BOM rows / 4010 matched |
| `report-allegro-bom` in `cli.py` | Generate a component-centric intake report for netlist-only Allegro projects | Allegro netlist/PST input + schematic BOM path + optional output path/mode flags | Markdown report with intake status, prefix summary, BOM item groups, mismatch sections, and optionally one row per design component | Turns the V2.6 deterministic join into a review-meeting artifact without adding unsupported electrical/PCB conclusions | Renderer and CLI tests; public PST+BOM smoke writes 4010 matched component rows, 194-line summary, and 27-line mismatch triage |
| `parse_document_index(path)` in `documents/index.py` | Read local public datasheet/document links | CSV/TSV with URL/link/path plus optional MPN/manufacturer/value/title/description columns | `DocumentIndex` entries with normalized fields and `doc:<file>#line<N>` source tokens | Keeps document discovery deterministic and auditable instead of doing live supplier lookup | Parser tests cover alias mapping and missing link-column failure |
| `match_documents_to_bom(bom, index)` in `documents/matcher.py` | Attach document-match evidence state to BOM item groups | Parsed schematic BOM + local `DocumentIndex` | `DocumentMatchReport` with `matched / no_result / ambiguous / manual_needed` counts and candidates | Separates component identity indexing from electrical validation, lifecycle, pricing, availability, and PLM | Matcher tests cover all four states, manufacturer conflict, passive manual-needed, and unindexed MPN |
| `report-allegro-bom --document-index` in `cli.py` | Render datasheet/document index sections inside the Allegro+BOM intake report | Allegro netlist/PST + schematic BOM + local document-index CSV/TSV | Markdown sections `Datasheet / Document Match Summary` and `Datasheet / Document Matches` | Shows which BOM item groups have usable public documents before any pin-level validation is attempted | CLI tests and fixed synthetic fixture smoke write a summary report with one matched document row |
| `PinProfile` in `ir/profile.py` | Store source-tokened datasheet facts for one pin | One structured pin row inside a `DatasheetProfile` JSON file | Pydantic row with number/name/category/function/limits/topology/evidence | Gives V3.1 deterministic pin comparison a profile input instead of free-text datasheet guessing | Profile tests cover JSON round-trip and legacy v1 compatibility |
| `report-pin-profile` in `cli.py` | Generate a pin-profile markdown artifact | `data/datasheet_profiles/*.json` profile path + optional output path | Markdown with pin summary/detail tables and scope boundary text | Lets reviewers inspect structured datasheet pin facts before validation rules consume them | CLI + renderer tests; smoke on public `l78.json` writes a 3-pin profile report |
| `validate_component_against_profile` in `validation/component.py` | Compare one schematic component against one structured pin profile | `Component`, `DatasheetProfile`, and `Design.nets` | `ValidationReport` with per-pin `PASS/WARN/ERROR`, component-level checks, net, summary, and evidence tokens | Keeps judgement deterministic and testable before any model-written diagnosis | Validation tests cover nominal L78, wrong ground, unknown input voltage, missing profiled pin, and XL1509 DCDC topology checks |
| `report-component-validation` in `cli.py` | Generate one component validation report | Allegro netlist/PST input, refdes, profile JSON, optional schematic BOM, optional output path | Markdown report with component identity, overall status, counts, scope boundary, and pin validation rows | Turns V3.0 pin facts plus V2.5/V2.6 topology/identity into the first component-level validator artifact | CLI + renderer tests; smoke on synthetic public L78 fixture writes PASS/WARN/ERROR=3/0/0 |
| `validation/dcdc.py` | Validate XL1509-style buck converter peripheral topology | Selected component, profile `recommended` DCDC limits, and schematic output-net neighbors | Component-level PASS/WARN/ERROR checks for output inductor and freewheel diode | Catches deterministic buck mistakes that do not belong in one pin row | Tests cover bad `1N4007W + 6.8uH`, nominal Schottky + inductor range, missing inductor, unknown diode type, and wrong feedback rail |
| `report-validator-ui` in `cli.py` | Generate a local static validator UI | Allegro netlist/PST input, schematic BOM, selected refdes, profile JSON, optional output path | Single-file HTML with component index, selected validation detail, component checks, schematic-net pane, scope pane, and markdown download link | Mirrors the target product workflow without adding a server, WebSocket, boardview canvas, or frontend build stack | Renderer + CLI tests cover L78 PASS and XL1509 ERROR fixture paths |

**Hardware-engineer explanation:** this module is the project's 位号台账 plus a PCB-side diagnostic net reader. Before AI can review a board, it must know which U/C/R/D/J designators really exist. The parser turns KiCad files into that trusted table. Later, if the model says "U999 has a decoupling issue", Refdes Guard can reject it because `U999` is not in `BoardRegistry`.

**What it does not do yet:** it does not parse DRC/ERC results, datasheet PDFs beyond the existing profile/vector flow and local document indexes, Allegro `.brd`, boardview data, placement, routing, or PCB geometry. `pcb_nets` come from `.kicad_pcb` and are post-Layout diagnostics only. The Allegro adapters read schematic-exported topology only; the BOM matcher can add schematic BOM identity by refdes, the document matcher can attach local public datasheet/document links, and pin profiles expose source-tokened datasheet pin facts. V3.1 component validation makes narrow schematic-side PASS/WARN/ERROR conclusions from deterministic inputs. V3.2 renders those same facts into a static UI artifact. V3.3 adds one family template for XL1509-style buck converters; it does not generalize to MCU, gate-driver, LED, transistor, simulation, thermal-layout, or supplier decisions. These layers do not make PLM-grade lifecycle/cost/supplier/availability decisions. A net literally named `NC` is still just a net name unless a future format supplies explicit no-connect semantics.

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
uv run hardwise report-pin-profile data/datasheet_profiles/l78.json --output reports/l78-pin-profile.md
uv run hardwise report-component-validation tests/fixtures/allegro/l78_regulator.net U1 data/datasheet_profiles/l78.json --bom tests/fixtures/allegro/l78_regulator_bom.csv --output reports/u1-component-validation.md
uv run hardwise report-validator-ui tests/fixtures/allegro/l78_regulator.net tests/fixtures/allegro/l78_regulator_bom.csv U1 data/datasheet_profiles/l78.json --output reports/l78-validator-ui.html
uv run hardwise ask data/projects/pic_programmer "U3 是什么器件？"
uv run hardwise ask data/projects/pic_programmer "U4 这颗器件有几个 NC 脚？" --max-iterations 6
uv run hardwise ask data/projects/pic_programmer "找一下 U3 最大输入电压" --vector
uv run hardwise inspect-allegro-netlist tests/fixtures/allegro/pst
uv run hardwise inspect-bom-match tests/fixtures/allegro/pst /tmp/pst.csv
uv run hardwise report-allegro-bom tests/fixtures/allegro/pst /tmp/pst.csv --output reports/pst-bom-intake.md
uv run hardwise report-allegro-bom tests/fixtures/allegro/pst /tmp/pst.csv --summary-only
uv run hardwise report-allegro-bom tests/fixtures/allegro/pst /tmp/pst.csv --mismatch-only
uv run hardwise report-allegro-bom tests/fixtures/allegro/pst tests/fixtures/allegro/document_match/bom.csv --summary-only --document-index tests/fixtures/allegro/document_match/docs.csv
```

`inspect-kicad` is the first EDA adapter demo: it prints the registry count and the first N sorted components. On `pic_programmer`, it extracts 121 registry items.

`review` runs the requested rules over the schematic-side records, applies Refdes Guard + Evidence Ledger, writes a markdown report aligned to《SCH_review_feedback_list 汇总表》, and (by default) appends Sleep Consolidator candidates to `memory/rules.md`, populates a SQLite store at `reports/<project>.db` with components + NC pins, and appends one machine-readable run record to `trace.jsonl`. On `pic_programmer` with `--rules R001,R002,R003`, the output is 28 findings (6 R002 missing-voltage findings + 22 R003 NC findings after connector aggregation) and 2 candidate rules (R002 medium + R003 medium). `--no-consolidate` skips the memory write; `--memory-output PATH`, `--db-path PATH`, and `--trace-output PATH` redirect their respective outputs.

`ingest-datasheet` chunks a PDF page-by-page and upserts into Chroma at `data/chroma/` (default), tagging every chunk with `part_ref=<refdes>`. `query-datasheet` runs a top-k semantic query and prints `[source_pdf pN part=Ux]` provenance — these are the building blocks for the Slice 4 `datasheet:<pdf>#p<N>` evidence token.

`report-pin-profile <profile.json>` writes a structured datasheet pin-profile report from `DatasheetProfile.pins`. It shows pin number/name/category/function, per-pin limits, recommended topology notes, and evidence tokens. It deliberately stops before schematic validation or PASS/WARN/ERROR judgement; V3.1 consumes these facts.

`report-component-validation <netlist_or_pst> <refdes> <profile.json>` writes one deterministic component validation report. It loads Allegro schematic topology, optionally joins schematic BOM identity, checks the selected refdes against structured pin facts, and renders overall status plus pin-level PASS/WARN/ERROR rows. The first shipped profile path validates an L78-style regulator's VI/GND/VO pins; broader MCU, gate-driver, DCDC, MOSFET, diode, and connector templates are future work, not implied by this command.

`report-validator-ui <netlist_or_pst> <bom> <refdes> <profile.json>` writes a self-contained HTML validator UI. It reuses the same deterministic component validation object, then adds a component index table, selected detail pane, schematic-net members for the selected component, a scope boundary tab, and an embedded markdown download link. It opens directly from disk and needs no local server.

`verify-api --tier {fast,normal,deep}` exercises the `ModelRouter` against the upstream API and prints the resolved model id + token counts.

`ask <project_dir> "<question>"` is the Slice 4 entry point to the agent loop: parses the KiCad project, builds an in-memory SQLite session + registry, optionally opens a Chroma collection (`--vector`), constructs a `Runner`, runs `messages.create(tools=TOOL_DEFINITIONS, ...)` in a finite tool-use loop, and prints the answer + one line per tool call + a token line (including `cache_create/read` when nonzero). Three live runs on pic_programmer with `mimo-v2.5` exercise (1) known-refdes `get_component`, (2) unknown-refdes `get_component → ComponentNotFound` (model honors anti-fabrication), and (3) `get_nc_pins --refdes_filter U4` returning 2 NC pins — all three runs report nonzero `cache_read_input_tokens`.

`report-allegro-bom <netlist_or_pst> <bom>` writes the Allegro intake report. It loads schematic topology from Telesis or PST netlists, joins a schematic BOM by refdes, then writes markdown with prefix counts, BOM item groups, mismatch sections, and a component table with BOM identity fields, connected pins/nets, and source tokens. `--summary-only` keeps the index sections and omits the full component table; `--mismatch-only` emits just status plus mismatch sections for fast triage. `--document-index <csv-or-tsv>` adds local datasheet/document match sections keyed by BOM item identity; it is intentionally rejected with `--mismatch-only` because mismatch triage omits all index sections. The command deliberately says "intake" rather than "review" because it does not run electrical checklist rules, parse `.brd`, inspect boardview/PCB geometry, fetch live supplier data, or make PLM-grade BOM judgments.

## Module explanation template

Every shipped module should be documented with this minimum:

1. **Purpose** — what hardware workflow step it automates.
2. **Input** — exact files, CLI arguments, database rows, or tool calls it consumes.
3. **Output** — exact object, file, table row, report section, or CLI text it produces.
4. **Why this design** — why this module exists instead of being folded into another one.
5. **Verification** — command or test that proves it works.
6. **Interview sentence** — one concise sentence the author can say in an interview.
