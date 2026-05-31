# Implementation Plan

1. Add the four reviewed public analog IC profiles.
2. Extend generic pin validation for `analog_output` and
   `open_collector_output` connectivity-only categories.
3. Add focused tests for profile pinouts and nominal generic validation.
4. Update CLI/ranking expectations for the motor sensor controller fixture.
5. Update validation spec, interview Q&A, and learning log with the C4c result
   and boundary.
6. Verify with targeted tests, C4c smoke, full pytest, and ruff.

## Verification Commands

```bash
uv run pytest -q tests/validation/test_component.py tests/test_cli_validator_ui.py tests/validation/test_profile_candidates.py
uv run hardwise design-validator-ui tests/fixtures/allegro/motor_sensor_controller.net tests/fixtures/allegro/motor_sensor_controller_bom.csv --document-index data/document_indexes/family_v1_3_docs.csv --index-json /tmp/c4c-final-index.json -o /tmp/c4c-final.html
uv run hardwise recommend-next-family /tmp/c4c-final-index.json -o /tmp/c4c-final-next.md
uv run pytest -q
uv run ruff check .
```

## Stop Conditions

- Stop if the slice requires a behavior-level analog IC validator.
- Stop if datasheet pinout facts conflict with the fixture package assumptions.
- Stop if existing deterministic LED/BJT/power findings change unexpectedly.
