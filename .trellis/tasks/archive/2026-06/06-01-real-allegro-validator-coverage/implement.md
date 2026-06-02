# Implementation Plan

## Ordered Checklist

1. Document the coverage plan in `docs/validator_coverage_plan.md`.
2. Add generic passive parsing and validation helpers with unit tests.
3. Wire generic passive validation into `build_project_validation_index()` only
   when no ready profile matched.
4. Add UI term labels for `generic_passive` and generic passive reasons.
5. Add `74lv165.json` profile and `shift_register_piso` validator.
6. Add tests proving 74LV165 serial-chain continuity through one series
   resistor and common clock/load fanout.
7. Add `ln2312lt1g.json` profile and a smoke test that it matches the real BOM
   identity.
8. Add `pca9617a.json` profile and `i2c_level_shift_repeater` validator.
9. Add tests for VCCA/VCCB range and bus-side pair connectivity.
10. Add diode pack profiles only for parts that fit existing diode checks.
11. Regenerate the real Allegro index/workbench and verify coverage counts.
12. Run full quality gates.
13. Update `docs/learning_log.md` and `docs/interview_qa.md` with measured
    facts learned from the real board.

## Validation Commands

```bash
uv run pytest -q
uv run ruff check .
uv run hardwise design-validator-ui "<real allegro path>" --fake-ai --output /tmp/hardwise-real-allegro-workbench.html
uv run hardwise inspect-validation-index /tmp/hardwise-real-allegro-index.json
```

If the exact CLI command names differ, inspect `uv run hardwise --help` and use
the existing real-board smoke path that emits the project validation index.

## Review Gates

- Do not start code edits until the task is `in_progress`.
- Treat generic passive coverage as light deterministic coverage; do not market
  it as datasheet-backed deep validation.
- Do not let anonymous net names become fabricated voltage assumptions.
- Do not add diode profiles that require unimplemented polarity/current logic.
- Stop and revise planning if a selected public datasheet cannot be sourced or
  if the real board pinout contradicts the assumed profile.

## Risky Files

- `src/hardwise/validation/project_index.py`: coverage count and row truth.
- `src/hardwise/validation/component.py`: topology-family dispatch.
- `src/hardwise/report/*`: UI labels must preserve existing validated truth.
- `data/datasheet_profiles/*.json`: ready profiles immediately affect
  candidate matching.
