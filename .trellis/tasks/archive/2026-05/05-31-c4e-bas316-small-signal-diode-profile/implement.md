# Implementation Plan

1. Add reviewed public BAS316 diode profile.
2. Add focused diode tests for pinout, nominal reverse-voltage PASS, and reverse
   overstress ERROR.
3. Update CLI/ranking expectations for the motor sensor controller fixture.
4. Update interview Q&A and learning log with the C4e result and BAV99 boundary.
5. Verify with targeted tests, C4e smoke, full pytest, and ruff.

## Verification Commands

```bash
uv run pytest -q tests/validation/test_diode.py tests/test_cli_validator_ui.py tests/validation/test_profile_candidates.py
uv run hardwise design-validator-ui tests/fixtures/allegro/motor_sensor_controller.net tests/fixtures/allegro/motor_sensor_controller_bom.csv --document-index data/document_indexes/family_v1_3_docs.csv --index-json /tmp/c4e-final-index.json -o /tmp/c4e-final.html
uv run hardwise recommend-next-family /tmp/c4e-final-index.json -o /tmp/c4e-final-next.md
uv run pytest -q
uv run ruff check .
```

## Stop Conditions

- Stop if C4e requires modeling BAV99 or any other three-pin dual-diode package.
- Stop if BAS316 public data cannot support a reviewed profile.
- Stop if existing LED/BJT/analog IC/TVS findings change unexpectedly.
