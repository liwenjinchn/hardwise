# Six-section report polish implementation plan

## Pre-Implementation Gate

Do not edit product code until this plan is reviewed and the task is activated
with `task.py start`.

Before implementation, load `trellis-before-dev` for backend/reporting specs.

## Ordered Checklist

1. Renderer inventory
   - Re-read `validator_multi_ui.py`, `validator_multi_ui_sections.py`,
     `validator_project_ui.py`, and `component_validation_markdown.py`.
   - Re-read `ir/profile.py`, `validation/types.py`, and
     `validation/project_index.py` to keep the evidence data boundary clear.
   - Confirm the current callers of `ValidatorUiResult` and markdown `render()`.
   - Search for tests asserting exact section text or table layout.

2. Pin consistency section
   - Add a report-only helper comparing profiled pin count to schematic pin
     count.
   - Render a small PASS/WARN-style table without changing `ValidationReport`.
   - Add markdown parity.

3. Evidence/details section
   - Implement Path A from `design.md`: load/carry `DatasheetProfile` for
     validated rows.
   - Extend `ValidatorUiResult` with an optional
     `profile: DatasheetProfile | None = None`.
   - Render profile-level `abs_max`, `recommended`, pin `limits`,
     `recommended_topology`, and `profile.evidence` tokens where available.
   - Show an explicit missing-data note for thermal/package facts when not
     present; do not convert missing thermal facts into inferred claims.
   - Avoid adding new thermal claims or vendor datasheet PDFs.

4. Connection path display
   - Add a private helper that derives bounded schematic paths from `Design.nets`.
   - Add a Path / Topology Path column to the pin function/connectivity section.
   - If direction ordering is ambiguous, present the result as a schematic path,
     not current flow.

5. Detail panel order
   - Reorder validated detail panels into the six-section review shape from the
     design doc.
   - Keep zero-profile/gap detail behavior unchanged.

6. Markdown download parity
   - Update `component_validation_markdown.render()` with
     `profile: DatasheetProfile | None = None`.
   - Pass loaded profile data from `report-component-validation`,
     `validator_multi_ui`, and any single-component UI download path.
   - Ensure single-component CLI reports and embedded UI downloads include the
     same new sections.

7. Tests
   - Update `tests/report/test_validator_ui.py` for new sections/path/evidence.
   - Update `tests/report/test_component_validation_markdown.py` and focused CLI
     component-validation tests if section text changes.
   - Add assertions that profile-level tokens such as
     `datasheet:xl1509.pdf#p9`, `datasheet:eg2132.pdf#p6`, or
     `datasheet:stm32g030.pdf#p33` remain visible in the evidence/details
     section.
   - Keep gap/no-profile assertions intact.

8. Verification
   - Run focused report tests first.
   - Run final project checks.

## Verification Commands

Focused checks:

```bash
uv run pytest tests/report/test_validator_ui.py -q
uv run pytest tests/report/test_component_validation_markdown.py -q
uv run pytest tests/test_cli_component_validation_report.py -q
uv run pytest tests/test_cli_validator_ui.py -q
```

Final gate:

```bash
uv run pytest -q
uv run ruff check .
```

Optional manual artifact smoke:

```bash
uv run hardwise design-validator-ui \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --output /tmp/hardwise-six-section-report.html
```

## Stop-and-Ask Conditions

- A section requires adding unverified datasheet/thermal facts to profiles.
- Connection-path rendering would imply PCB layout, current direction, or
  placement/routing.
- No-profile rows would need to become electrical judgements to satisfy a UI
  expectation.
- Implementing report polish would require adding a new agent tool or changing
  Runner dispatch.
- Test updates reveal that validator verdicts or PASS/WARN/ERROR counts changed.

## Follow-Up Tasks

- Grounded-LLM long-tail review, with a separate task for `GroundedReview`,
  structured claims, post-LLM evidence ledger, and chat-only demo.
- Optional thermal/profile evidence schema after public source tokens are
  verified.
- Hosted upload/login shell after local trust story is stable.
