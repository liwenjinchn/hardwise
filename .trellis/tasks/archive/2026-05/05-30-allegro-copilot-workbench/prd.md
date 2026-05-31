# Allegro-first Copilot workbench

## Goal

Build an Allegro-first design-validation workbench with a Copilot-style AI panel.
The workbench should let an interviewer open a local Hardwise project view, see
deterministic component validation, and ask focused questions about the selected
component, datasheet requirements, evidence, and refdes safety.

The same panel must support two modes:

- `serve-workbench`: localhost real-time AI mode backed by Hardwise tools and an
  Anthropic-compatible endpoint, suitable for an internal/offline company model.
- `design-validator-ui --ai-snapshot`: single-file no-backend demo mode with the
  same Copilot UI and deterministic offline answers, suitable for no-network
  interviews.

## User Value

- Shows Hardwise as a product workbench, not just a markdown report generator.
- Makes Allegro/PST + BOM the primary enterprise-facing path.
- Demonstrates that AI answers are grounded in deterministic validation and
  evidence, not free-form hallucination.
- Lets a hardware newcomer or interviewer ask "why is this component risky?",
  "what evidence supports that?", and "is this refdes on the board?" without
  manually digging through datasheets first.

## Confirmed Code Facts

- `design-validator-ui` already accepts Allegro/Telesis netlists or
  Capture/Allegro PST inputs plus BOM and renders the three-pane project
  workbench through `render_project_workbench()`.
- `_load_allegro_design()` already converts Allegro netlist/PST inputs into the
  unified `Design` IR.
- `Design` exposes component-centric Allegro facts; `BoardRegistry` is still the
  guard/relational-tool registry contract with `has_refdes()`.
- `run_component_validation` already works from `Design` plus explicit
  refdes-to-profile targets.
- `Runner` currently assumes a relational `Session`, a `BoardRegistry`, and the
  full five-tool manifest. Those contracts are part of the current guard/tool
  discipline and should stay stable for this slice.
- The agent system prompt still describes a KiCad project and an older tool
  catalogue, so workbench chat needs a scoped Allegro/workbench prompt.
- `pyproject.toml` does not currently include `fastapi` or `uvicorn`.
- The main demo fixture is
  `tests/fixtures/allegro/mixed_controller_power_stage.net` plus
  `tests/fixtures/allegro/mixed_controller_power_stage_bom.csv`; the existing
  `design-validator-ui` path auto-matches four local profiles for this fixture.

## Requirements

- Allegro-first: v1 acceptance is based on Allegro/Telesis netlist or
  Capture/Allegro PST plus BOM. KiCad must not regress, but KiCad real-time
  Copilot support is not a v1 acceptance target.
- Copilot UI: the workbench has a right-bottom floating AI button that opens a
  smooth right-side chat panel with messages, suggestions, an input box,
  loading state, and front-end typewriter animation.
- Same UI in both modes: live mode and offline snapshot mode share the same
  visual panel and interaction model.
- Live mode entrypoint: add `serve-workbench` as a separate command rather than
  overloading static HTML generation.
- Static mode entrypoint: add `design-validator-ui --ai-snapshot`; without this
  flag, the current static workbench output remains unchanged.
- Context scope: v1 chat is centered on the selected component. It also supports
  global refdes-existence checks such as `U999`.
- Agent compatibility: run the existing Agent/Runner on Allegro by adapting
  `Design` into a `BoardRegistry` shim and relational `Session`, not by changing
  the Runner registry/session contract or broadening the refdes-guard interface.
- Tool scope: expose the existing five tools in live mode. The panel should
  steer the model toward `run_component_validation` for validator questions and
  `search_datasheet` for datasheet questions. If vector search is not configured,
  `search_datasheet` remains available but returns its existing structured
  "not configured" result.
- Safety: every user-visible answer and trace must pass the existing
  BoardRegistry-backed refdes guard. Unknown refdes-shaped tokens are shown as
  wrapped tokens such as `<?U999>` in plain ASCII planning docs and as the
  project-standard wrapped form in UI output.
- Evidence trace: every answer includes a default-collapsed Evidence / Tool
  trace section showing tool name, refdes, status, evidence tokens, and wrapped
  refdes count when applicable.
- Chat state: keep chat history in the browser session only. Do not persist
  backend chat history in v1.
- Response behavior: do not implement token streaming in v1. The backend returns
  one JSON response, and the front-end renders it with loading plus typewriter
  animation.
- Fake mode: live mode must support `--fake-ai` without bypassing Runner. The
  fake model drives real Runner tool calls; tests and demos do not require an
  API key, but the tool dispatch, trace, and guard path stay real.
- Real mode: non-fake live mode uses `.env` / process environment for
  `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`, and existing model-tier variables.
  The browser never receives API keys or model endpoint secrets.
- Language: answer language follows the user's question where practical.
- Public safety: do not use or encourage company-internal hardware data in this
  public repo. Use public fixtures and public datasheet/profile artifacts only.

## Acceptance Criteria

- [ ] `uv run hardwise serve-workbench tests/fixtures/allegro/mixed_controller_power_stage.net tests/fixtures/allegro/mixed_controller_power_stage_bom.csv --fake-ai` starts a localhost workbench without requiring an API key.
- [ ] The localhost workbench shows the existing three-pane validator UI plus a
  right-bottom AI button and right-side Copilot panel.
- [ ] In fake live mode, asking about the selected component returns an answer
  grounded in its deterministic validation status and evidence through a real
  Runner `run_component_validation` tool call.
- [ ] In fake live mode, asking about `U999` demonstrates refdes guard behavior
  through the real Runner/guard path and does not fabricate a component.
- [ ] Each live answer includes a collapsed Evidence / Tool trace that can be
  expanded in the panel.
- [ ] If vector search is not configured, the panel still answers from
  validation/profile evidence and reports datasheet search as unavailable rather
  than failing.
- [ ] `design-validator-ui --ai-snapshot` writes a single HTML file with the
  same Copilot panel in offline snapshot mode.
- [ ] A static snapshot HTML can be opened via `file://` with no server and
  still supports selected-component questions, suggestion clicks, boundary
  fallback text, and trace expansion.
- [ ] Running `design-validator-ui` without AI flags keeps the existing static
  workbench path free of Copilot UI and preserves current tests.
- [ ] Fast tests do not call a live model and do not require network access.
- [ ] `uv run pytest -q` and `uv run ruff check .` pass before implementation is
  reported complete.

## Out of Scope

- Token-by-token SSE/WebSocket streaming.
- Backend chat-history persistence, user accounts, auth, or multi-user sessions.
- Browser-direct model calls or exposing API keys in HTML/JS.
- Full arbitrary board-level reasoning, fault-tree generation, or cross-module
  diagnosis beyond selected-component context and refdes existence checks.
- KiCad real-time Copilot parity in v1.
- Changing the Runner registry/session contract or replacing the
  BoardRegistry-backed refdes guard contract.
- Allegro `.brd`, boardview, placement, routing, PCB geometry, PLM, lifecycle,
  pricing, or availability integration.
- Company-internal hardware data in repo, tests, docs, or demo artifacts.
- Rewriting component validators or changing validation rule semantics unless a
  bug blocks this feature.

## Open Questions

No blocking product questions remain from the interview. Implementation can
choose conservative defaults for port, panel copy, and exact module names while
staying inside this PRD.
