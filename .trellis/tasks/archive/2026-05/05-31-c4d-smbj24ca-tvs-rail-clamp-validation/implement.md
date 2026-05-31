# Implementation Plan

1. Add the reviewed public SMBJ24CA bidirectional TVS profile.
2. Extend the existing diode validator for `diode_role="bidirectional_tvs"`.
3. Add focused diode tests for profile pinout, nominal clamp, and rail above
   standoff.
4. Update CLI/ranking expectations for the motor sensor controller fixture.
5. Update validation spec, interview Q&A, and learning log with the C4d result
   and boundary.
6. Verify with targeted tests, C4d smoke, full pytest, and ruff.

## Verification Commands

```bash
uv run pytest -q tests/validation/test_diode.py tests/test_cli_validator_ui.py tests/validation/test_profile_candidates.py
uv run hardwise design-validator-ui tests/fixtures/allegro/motor_sensor_controller.net tests/fixtures/allegro/motor_sensor_controller_bom.csv --document-index data/document_indexes/family_v1_3_docs.csv --index-json /tmp/c4d-final-index.json -o /tmp/c4d-final.html
uv run hardwise recommend-next-family /tmp/c4d-final-index.json -o /tmp/c4d-final-next.md
uv run pytest -q
uv run ruff check .
```

## Stop Conditions

- Stop if this requires generic inductor validation or fixture-only inductor
  profiles.
- Stop if SMBJ24CA public data cannot support a reviewed profile.
- Stop if existing LED/BJT/analog IC findings change unexpectedly.
