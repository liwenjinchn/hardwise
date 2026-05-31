# Evidence-first UI

## Goal

Add an evidence-first presentation layer to the existing deterministic validator
workbench and Copilot surfaces. The UI should make provenance visible at the
point of review: trust tier, source-token/page chips, schematic topology path,
and tool trace should sit beside each finding or answer rather than being hidden
inside raw markdown/JSON-looking text.

This task is a C2 presentation/contract slice after C1 six-section report
polish. It must not add grounded-LLM review, new validators, new profile facts,
or new PASS/WARN/ERROR semantics.

## User Value

- Makes the anti-hallucination story visible to interviewers without requiring
  them to inspect raw JSON, markdown downloads, or backend traces.
- Bridges the current deterministic report (`L1`) toward the future constrained
  LLM roadmap by introducing trust labels before any `L2 grounded` output ships.
- Helps users scan why a finding is trustworthy: deterministic validator result,
  datasheet/profile evidence token, schematic topology path, or manual/no-profile
  coverage gap.
- Keeps the next grounded-LLM work honest by reserving clear UI space for
  `grounded` and `manual` states without producing grounded claims yet.

## Confirmed Code Facts

- C1 shipped `ValidatorUiResult.profile` and profile-backed evidence/details
  rendering in `src/hardwise/report/validator_multi_ui.py` and
  `src/hardwise/report/validator_multi_ui_sections.py`.
- Shared report-only helpers now live in
  `src/hardwise/report/component_validation_details.py`, including bounded
  schematic connection paths and pin consistency.
- Markdown parity lives in
  `src/hardwise/report/component_validation_markdown.py`.
- Project workbench rendering in
  `src/hardwise/report/validator_project_ui.py` supports validated detail panels
  and zero-profile/gap panels.
- The Copilot panel is rendered by `src/hardwise/report/copilot_panel.py` with
  CSS/JS in `src/hardwise/report/copilot_panel_assets.py`.
- Copilot trace data already has a typed `EvidenceTrace` shape in
  `src/hardwise/workbench/chat.py`: `tool`, `input`, `summary`, `status`,
  `evidence`, and `wrapped`.
- The current Copilot UI renders trace rows as a collapsed details block with a
  raw-ish `input=... evidence=... wrapped=...` code string.
- Reporting spec guidance in `.trellis/spec/backend/reporting-guidelines.md`
  says renderers may surface existing profile/validation evidence but must not
  mutate `ValidationReport` or infer missing facts.

## Requirements

- Preserve deterministic truth:
  - Do not change validator logic, status rollups, family dispatch, agent tool
    behavior, or profile candidate matching.
  - Do not add grounded-LLM findings, new agent tools, or Runner dispatch paths.
  - Do not convert no-profile/manual rows into electrical judgements.
- Add trust-tier display:
  - Existing deterministic validation findings and pin/check rows should render
    as `deterministic` / `L1`.
  - No-profile/manual rows should render as `manual` / `L3` or equivalent
    coverage-gap language.
  - `grounded` / `L2` may appear only as a reserved legend/state, not as an
    actual emitted finding in this task.
- Add source-token chips:
  - Datasheet/profile evidence tokens such as `datasheet:xl1509.pdf#p9` should
    render as compact chips near the row they support.
  - Chips should remain text-searchable and copyable in the static HTML.
  - Markdown downloads should keep plain inline code tokens rather than trying
    to mimic visual chips.
- Improve trace readability:
  - Evidence / Tool trace rows should separate tool name, status, evidence
    tokens, refdes wrapping count, and tool input into readable fields.
  - Unknown-refdes guard behavior must remain visible for `U999`-style cases.
- Keep topology display honest:
  - Topology path remains schematic/netlist-derived display context only.
  - No wording may imply current flow, PCB placement, routing, or board geometry.
- UI compatibility:
  - Static no-AI `design-validator-ui` output remains Copilot-free unless
    `--ai-snapshot` is used.
  - Existing validated workbench counts for `mixed_controller_power_stage`
    remain `25 components`, `validated=4`, `PASS/WARN/ERROR=1/0/3`.
  - Zero-profile/gap workbench remains a coverage artifact.

## Acceptance Criteria

- [x] Validated detail rows in the multi/project validator UI show an explicit
      `L1 deterministic` trust label for pin rows, component checks, or section
      groupings.
- [x] Profile evidence tokens render as compact source chips in HTML and remain
      visible/copyable as text.
- [x] No-profile/manual project rows render a `manual`/coverage trust state
      without producing PASS/WARN/ERROR electrical judgement.
- [x] Copilot `Evidence / Tool trace` rows are more readable than the current
      raw `input=... evidence=... wrapped=...` string and still expose wrapped
      refdes count.
- [x] `U999` snapshot/live fake paths still visibly demonstrate Refdes Guard
      wrapping.
- [x] `design-validator-ui` without AI flags remains free of Copilot UI.
- [x] `design-validator-ui` for `mixed_controller_power_stage` still reports
      `25 components`, `validated=4`, and `PASS/WARN/ERROR=1/0/3`.
- [x] Markdown component-validation output keeps evidence tokens visible and
      readable.
- [x] `uv run pytest -q` and `uv run ruff check .` pass.

## Out of Scope

- Grounded-LLM long-tail review or L2 claim generation.
- New validators, new datasheet/profile facts, or new family coverage.
- New agent tools, tool-count changes, prompt-tool contracts, or Runner dispatch
  changes.
- Hosted upload/login/project persistence.
- Live supplier lookup, PLM, lifecycle, pricing, availability, or supplier-risk
  scope.
- `.brd`, boardview, placement, routing, PCB geometry, simulation, or current
  flow analysis.
- Reverse-engineering or copying any external product UI/code.

## Decisions

- C2 includes both validator report detail and Copilot panel trace polish.
- The Copilot work remains trace presentation only. It does not add L2 grounded
  LLM claims, new tools, new fake-client behavior, or Runner dispatch changes.
