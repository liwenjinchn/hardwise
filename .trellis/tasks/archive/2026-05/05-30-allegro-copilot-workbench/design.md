# Allegro-first Copilot workbench design

## Architecture Overview

This feature adds a workbench chat layer around the existing Allegro-first
validator workbench. The primary data source remains the deterministic
`Design` + `ProjectValidationIndex` path. The model, when enabled, is only an
assistant on top of that evidence.

```
Allegro netlist/PST + BOM + profiles
  -> existing Allegro loader and BOM/profile matching
  -> Design + ProjectValidationIndex + validation targets
  -> render_project_workbench(...)
  -> Copilot panel
       -> Design -> BoardRegistry shim + relational Session
       -> snapshot mode: baked Runner transcripts from fake model
       -> live mode: POST /api/workbench/chat to local FastAPI server
```

The browser never talks directly to the model endpoint. Live mode uses a local
Hardwise server so API keys, model base URL, tool execution, and sanitization
stay in Python.

## Boundaries

### EDA Boundary

Allegro/Telesis netlist and Capture/Allegro PST parsing continue to terminate at
the `Design` IR. The Copilot panel must not parse netlists, BOMs, or profile
files in JavaScript.

### Validation Boundary

`run_component_validation` remains the source of deterministic PASS/WARN/ERROR.
The chat layer formats and explains validation output; it does not invent new
electrical verdicts.

### Evidence Boundary

Profile evidence and validation evidence are available by default. Datasheet
vector search is optional and only enabled when `--vector` / `--persist-dir`
provides a collection. If disabled, responses must say that live datasheet
search is unavailable and fall back to reviewed profile evidence.

### Model Boundary

Real mode reuses the existing Anthropic-compatible SDK setup. Fake mode supplies
a deterministic Anthropic-compatible fake client that drives the real Runner
through real tool calls. Tests use fake mode.

### Guard Boundary

The refdes guard stays BoardRegistry-backed. Allegro compatibility is achieved by
building a `BoardRegistry` shim from `Design` and populating a relational session
from that shim. This avoids changing the Runner registry/session contract or the
guard's public shape while letting all existing agent tools run on Allegro facts.

## Proposed Modules and Responsibilities

- `src/hardwise/agent/prompts.py`
  - Add a scoped workbench prompt or make `build_system_blocks()` accept prompt
    text. The workbench prompt should describe the Allegro workbench context and
    the existing five-tool catalogue, including `run_component_validation`.

- `src/hardwise/agent/runner.py`
  - Keep the existing `session` and `registry: BoardRegistry` contract.
  - Add only the minimal prompt configurability needed for a workbench-specific
    system prompt.
  - Continue exposing the existing five-tool manifest in live mode.

- `src/hardwise/workbench/context.py` (new)
  - Own shared construction of `WorkbenchContext`: `design`, `bom_report`,
    `ProjectValidationIndex`, project metadata, `validation_targets`,
    `BoardRegistry` shim, and relational `Session`.
  - Reuse existing loader, BOM resolver, profile candidate, and project-index
    logic currently embedded in `design-validator-ui`.
  - Keep `design-validator-ui` and `serve-workbench` from duplicating the same
    setup code.
  - The only new ingest adapter is `board_registry_from_design(design)`.
    The context builder then calls `create_store(":memory:")` and the existing
    `populate_from_registry(session, registry)` path. Do not create a second
    Design-to-relational-row conversion path.
  - Build `validation_targets` from the same profile matching already used by
    `build_project_validation_index()`. If an extraction helper is needed, put
    it next to the project-index/profile-candidate owner rather than
    re-inferring refdes-to-profile matches in `context.py`.

- `src/hardwise/workbench/chat.py` (new)
  - Define request/response models for live chat.
  - Implement a deterministic fake Anthropic-compatible client that produces
    tool-use blocks and final text while letting Runner dispatch tools.
  - Fake response blocks must round-trip through Runner's message loop: simple
    attribute objects with `.type`, `.text`, `.name`, `.input`, and `.id` are
    enough, and `.usage` may be absent or zero-valued because Runner already
    handles missing usage.
  - Implement real-model responses through `Runner`.
  - Normalize tool trace into UI-friendly evidence trace objects.
  - Do not double-sanitize `RunResult.text` or Runner-generated traces; Runner
    already sanitized them. Sanitize only chat-layer text that does not come
    from Runner, such as fallback/boundary replies, suggestions, and baked
    snapshot copy.

- `src/hardwise/workbench/server.py` (new)
  - Create the FastAPI app.
  - Routes:
    - `GET /`: return the rendered workbench HTML in live mode.
    - `GET /api/workbench/state`: optional compact state for health/UI.
    - `POST /api/workbench/chat`: accept question + selected refdes + recent
      browser history; return answer JSON with trace.

- `src/hardwise/report/copilot_panel.py` and
  `src/hardwise/report/copilot_panel_assets.py` (new)
  - Render the AI button/panel and own CSS/JS.
  - Support two configurations:
    - snapshot mode: embedded facts/answers and no API URL.
    - live mode: `/api/workbench/chat` URL and lightweight embedded facts for
      suggestions/selected-refdes labels.

- `src/hardwise/report/validator_project_ui.py`
  - Add an optional `copilot_html=""` or `copilot_config=None` argument.
  - Default remains no Copilot UI.
  - Existing no-AI render path must remain stable.

- `src/hardwise/cli.py`
  - Add `--ai-snapshot` to `design-validator-ui`.
  - Add `serve-workbench` command with Allegro/PST + BOM inputs,
    `--fake-ai`, `--port`, `--host`, `--tier`, `--vector`, and
    `--persist-dir`.

- `pyproject.toml`
  - Add `fastapi` and `uvicorn`. Add a test client dependency only if endpoint
    tests require it.

## Data Contracts

### WorkbenchContext

Owned by `workbench/context.py`.

- `design: Design`
- `registry: BoardRegistry`
- `session: Session`
- `index: ProjectValidationIndex`
- `bom_report: BomMatchReport | None`
- `project_name: str`
- `netlist_source: Path`
- `generated_at: str`
- `validation_targets: dict[str, DatasheetProfile]`
- `document/vector metadata as needed`

### ChatRequest

- `question: str`
- `selected_refdes: str | None`
- `history: list[ChatMessage]` limited by caller/server

### ChatResponse

- `answer: str`
- `mode: "fake" | "real" | "snapshot"`
- `selected_refdes: str | None`
- `trace: list[EvidenceTrace]`
- `wrapped_count: int`
- `suggestions: list[str]`
- `datasheet_search_enabled: bool`

### EvidenceTrace

- `tool: str`
- `input: dict`
- `summary: str`
- `status: str | None`
- `evidence: list[str]`
- `wrapped: int`

Rendering code consumes these typed contracts rather than reparsing raw Runner
payloads in multiple places.

## Frontend Behavior

- The existing component selection flow remains the source of selected refdes.
  The current `activate(ref)` function should also update a shared selected
  state and dispatch a small browser event such as `hardwise:refdes-selected`.
- The Copilot panel listens to selected-refdes changes and updates suggested
  prompts.
- Submit flow:
  - Append user message.
  - Show loading text.
  - Snapshot mode answers locally from embedded facts.
  - Live mode posts JSON to `/api/workbench/chat`.
  - Render answer with typewriter animation.
  - Render trace under a collapsed details element.
- Unknown or unsupported questions return scoped guidance and suggested prompts,
  not a fabricated broad answer.

## Runtime Modes

### Snapshot Mode

`design-validator-ui --ai-snapshot` precomputes a small set of audited chat
transcripts by running Runner with the fake model against the Allegro-derived
`BoardRegistry` shim and `Design`. The resulting answers, suggestions, and
traces are embedded in the HTML. The page is self-contained and works via
`file://`.

### Fake Live Mode

`serve-workbench --fake-ai` uses the deterministic fake model through the real
`/api/workbench/chat` route and the real Runner. This is the default smoke-test
path.

### Real Live Mode

`serve-workbench` without `--fake-ai` builds a scoped `Runner`:

- `registry=board_registry_from_design(design)`
- `session=create_store(":memory:")` populated from that shim
- `design=design`
- `validation_targets` from the workbench context
- existing five-tool manifest
- optional vector collection; without it, `search_datasheet` returns its current
  structured not-configured response
- scoped workbench system prompt

The server returns a single JSON response per question. No token streaming in
v1.

## Compatibility

- `design-validator-ui` without AI flags must keep the existing workbench path
  free of Copilot UI.
- Existing KiCad `ask` and `review` commands must keep working.
- Existing runner tests that use `BoardRegistry` and relational stores must keep
  passing; workbench mode should add Allegro shim coverage rather than replacing
  those contracts.
- New workbench chat code should not require vector store setup unless the user
  enables `--vector`.

## Risks and Mitigations

- Risk: old KiCad prompt drift.
  - Mitigation: add explicit workbench prompt and tests asserting it describes
    Allegro/Design workbench use and all five current tools.
- Risk: frontend and backend disagree on selected refdes state.
  - Mitigation: one JS activation path owns selected refdes and dispatches one
    event consumed by the panel.
- Risk: static snapshot feels fake.
  - Mitigation: label it as an offline audited snapshot while preserving the
    same Copilot interaction shell.
- Risk: adding FastAPI expands dependencies.
  - Mitigation: keep server code isolated under `workbench/`; static HTML path
    remains independent.
- Risk: accidental model/network dependency in tests.
  - Mitigation: all automated tests use fake mode or fake Anthropic clients.

## Rollback Shape

If live server work becomes too broad, keep the `Design` -> `BoardRegistry` shim,
Copilot renderer, Runner-backed fake model, and `--ai-snapshot` path as a
smaller deliverable, then defer real `serve-workbench` model mode to a follow-up.
Do not ship browser-direct model calls as a shortcut.
