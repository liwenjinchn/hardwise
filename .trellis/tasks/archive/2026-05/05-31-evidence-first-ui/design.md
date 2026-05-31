# Evidence-first UI design

## Architecture Overview

C2 is a presentation-layer slice over existing deterministic artifacts:

```text
ValidationReport + DatasheetProfile + Design
  -> validator_multi_ui_sections / component_validation_markdown
  -> evidence-first rows, chips, and trust labels

WorkbenchChatService -> ChatResponse.trace[EvidenceTrace]
  -> copilot_panel_assets.js
  -> readable trace cards / chips
```

The source of truth remains unchanged. `ValidationReport` owns L1 deterministic
verdicts. `ProjectValidationIndex` owns no-profile/manual coverage gaps.
`EvidenceTrace` owns Copilot trace rows derived from Runner tool calls.

## Boundaries

### Validation Boundary

Do not modify `src/hardwise/validation/*`, `ValidationReport.status`,
`counts_by_status`, family dispatch, profile candidate matching, or agent tool
behavior. Trust labels are rendered labels, not a new validation state machine.

### Evidence Boundary

HTML may render existing evidence tokens as chips. Markdown remains plain text
with inline code tokens. No renderer may invent datasheet page facts or promote
missing evidence into a claim.

### Trust-Tier Boundary

For this task:

- `L1 deterministic`: existing `ValidationReport` pin rows and component checks.
- `L3 manual`: no-profile/manual coverage rows or explicit evidence gaps.
- `L2 grounded`: reserved legend/state only; no L2 claim is emitted yet.

This keeps the future constrained-LLM story visible without implementing the L2
engine.

### Copilot Boundary

Copilot changes are limited to trace rendering and optional label text. The
existing `ChatResponse` / `EvidenceTrace` Pydantic contracts remain sufficient;
avoid backend schema changes unless implementation proves that the current fields
cannot support readable display.

## Proposed Module Changes

- `src/hardwise/report/component_validation_details.py`
  - Add small display helpers for trust labels and source-token parsing if they
    are useful in both HTML and markdown.
  - Keep helpers report-only and side-effect-free.

- `src/hardwise/report/validator_multi_ui_sections.py`
  - Add trust-label display to pin summary, connectivity, pin consistency,
    compliance checks, and evidence details where it improves scanning.
  - Render evidence tokens through a shared chip helper instead of raw `<code>`
    where the row is evidence-first.
  - Keep schematic path wording as topology/display context only.

- `src/hardwise/report/validator_project_ui.py`
  - Add manual/L3 visual treatment to no-profile/gap coverage sections.
  - Keep the existing no-profile electrical-judgement disclaimer.

- `src/hardwise/report/component_validation_markdown.py`
  - Keep evidence tokens visible as inline code.
  - Add compact trust-tier text if needed for parity, but do not mimic visual
    HTML chips.

- `src/hardwise/report/copilot_panel_assets.py`
  - Replace raw trace code string with structured trace display:
    tool, status/summary, evidence chips, wrapped-refdes count, and compact input.
  - Preserve snapshot and live mode behavior.

- Tests
  - Update report renderer tests for trust labels, chip classes/text, manual
    coverage labeling, and Copilot trace markup.
  - Keep existing count/verdict/no-profile assertions.

## HTML Display Contracts

Evidence chips should remain copyable/searchable text. Suggested shape:

```html
<span class="evidence-chip" data-source="datasheet">datasheet:xl1509.pdf#p9</span>
```

Trust labels should be short and stable:

```html
<span class="trust trust-l1">L1 deterministic</span>
<span class="trust trust-l3">L3 manual</span>
```

Do not put truth into CSS class names only; tests and users should see the label
text.

## Copilot Trace Contract

Current trace data already includes:

- `tool`
- `input`
- `summary`
- `status`
- `evidence`
- `wrapped`

Rendering should display these fields separately. Example:

```text
run_component_validation · ERROR
Evidence: datasheet:xl1509.pdf#p9
Guard wraps: 0
Input: {"refdes":"U12"}
```

For unknown-refdes cases, the wrapped count and wrapped token should stay
visible.

## Compatibility

- `design-validator-ui` without `--ai-snapshot` must remain Copilot-free.
- `design-validator-ui --ai-snapshot` remains a single offline HTML file.
- `serve-workbench --fake-ai` continues using the real Runner path.
- Markdown downloads remain readable in GitHub/plain text.
- Existing static artifact generation must not require a browser or server.

## Risks and Mitigations

- Risk: trust labels look like new validator states.
  - Mitigation: label them as provenance/trust tier and keep PASS/WARN/ERROR
    unchanged.
- Risk: evidence chips hide text from search/copy.
  - Mitigation: chips are text spans, not icons-only widgets.
- Risk: Copilot trace polish drifts from backend `EvidenceTrace`.
  - Mitigation: consume the existing fields directly and test snapshot HTML.
- Risk: manual coverage rows look like electrical findings.
  - Mitigation: use `L3 manual`/coverage wording and keep the no-profile
    disclaimer.

## Rollback Shape

The change is isolated to report/Copilot rendering and tests. If the Copilot
trace work causes UI risk, keep trust labels and evidence chips in validator
detail first, then defer trace polish without changing backend contracts.
