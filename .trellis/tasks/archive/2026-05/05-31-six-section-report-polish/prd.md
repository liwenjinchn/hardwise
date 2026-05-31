# Six-section report polish

## Goal

Polish deterministic validator reports into a six-section hardware-review artifact
using existing `ValidationReport` truth. The output should look closer to a real
schematic-review report: model check, pin summary, pin function/connectivity with
topology path, pin consistency, compliance matrix, evidence/page details, and
final summary.

This slice is presentation-only. It must not change validator verdicts, add a
new agent tool, or introduce grounded-LLM review.

## User Value

- Makes the current deterministic engine's strongest findings easier to see in
  interviews: `U12` XL1509 diode/inductor, `U8` STM32 SWD swap, and `U3` EG2132
  bootstrap diode.
- Narrows the gap between Hardwise and the reference design-validator screenshot
  without weakening the anti-hallucination story.
- Gives the user a more credible artifact for "this is a hardware review", not
  only a flat validation table.
- Keeps the next grounded-LLM step separate so the trust boundary stays clear.

## Confirmed Code Facts

- Multi-component detail rendering lives in
  `src/hardwise/report/validator_multi_ui.py` and
  `src/hardwise/report/validator_multi_ui_sections.py`.
- Markdown downloads use
  `src/hardwise/report/component_validation_markdown.py`.
- Project workbench rendering in `src/hardwise/report/validator_project_ui.py`
  reuses `_detail_panels()` from the multi-validator renderer for validated rows.
- `ValidationReport` already carries pin rows and component-level checks.
- Existing profiles carry pin evidence tokens and profile-level evidence tokens
  such as `datasheet:xl1509.pdf#p9`, `datasheet:eg2132.pdf#p6`, and
  `datasheet:stm32g030.pdf#p33`.
- `Design.nets` and `Component.pins` are available at render time, so connection
  paths can be derived in the report layer.
- Current no-profile/gap workbench text explicitly says no-profile rows are not
  converted into electrical judgements. This slice must preserve that boundary.

## Requirements

- Preserve deterministic truth:
  - Do not change validator logic, status rollups, profile candidate matching,
    or agent tool behavior.
  - Do not add `review_unprofiled_component` or any sixth tool in this task.
  - Do not make no-profile rows produce electrical judgements.
- Six-section report shape for validated components:
  - Keep existing model check and pin-check summary.
  - Add a pin consistency section comparing profiled pins to schematic pins.
  - Add a connection-path column or equivalent topology path presentation in
    pin function/connectivity.
  - Keep component-level topology/peripheral checks visible as a separate part
    of the compliance section.
  - Add an evidence/details section that surfaces existing datasheet/profile
    evidence tokens. If page-level thermal facts are not present, render the gap
    explicitly rather than inventing thermal data.
  - Keep final summary issue-first and concise.
- Markdown parity:
  - The downloaded markdown report must include the new pin consistency and
    evidence/details sections.
  - Markdown should stay readable in GitHub/plain text and keep source tokens as
    inline code.
- UI compatibility:
  - Validated project workbench rows must still open issue-first detail panels.
  - Zero-profile/gap workbench rendering must remain unchanged in behavior and
    messaging.
  - Existing Copilot panel integration must remain optional and unaffected.
- Public safety:
  - Use only existing public fixtures and existing source tokens.
  - Do not add vendor datasheet PDFs or new claimed thermal facts in this slice.
  - Do not reverse-engineer or copy any external product UI/code.

## Acceptance Criteria

- [ ] `render_multi()` output for `mixed_regulators` includes the new pin
      consistency section and evidence/details section.
- [ ] `design-validator-ui` for
      `tests/fixtures/allegro/mixed_controller_power_stage.net` still reports
      `25 components`, `validated=4`, and `PASS/WARN/ERROR=1/0/3`.
- [ ] The validated detail for `mixed_controller_power_stage` still surfaces the
      existing deterministic hard errors (`U12`, `U8`, `U3`) without changing
      their verdicts.
- [ ] Connection paths are derived from schematic topology and render even when
      directionality cannot be inferred; no path may imply PCB layout,
      placement, routing, or boardview facts.
- [ ] Markdown component-validation output includes the new sections and keeps
      evidence tokens visible.
- [ ] Gap/no-profile workbench still states that no-profile rows are not
      converted into electrical judgements.
- [ ] `uv run pytest -q` and `uv run ruff check .` pass.

## Out of Scope

- Grounded-LLM review for no-profile components.
- New agent tools, prompt-tool-count changes, or Runner dispatch changes.
- Trust-tier data model changes beyond report labels for existing deterministic
  results.
- New deterministic family validators.
- Adding SS8050/Q12 datasheet evidence or any vendor PDF.
- Hosted upload/login/project persistence.
- PCB layout, `.brd`, boardview, placement, routing, PLM, lifecycle, pricing,
  availability, or supplier-risk scope.

## Open Questions

No blocking product questions remain. The implementation can choose conservative
rendering defaults for connection-path ordering and evidence/detail labels as
long as it preserves the deterministic/report-only boundary.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
