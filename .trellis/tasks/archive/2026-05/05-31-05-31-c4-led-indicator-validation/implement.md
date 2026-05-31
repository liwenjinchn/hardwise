# Implementation Plan

1. Add `data/datasheet_profiles/ltst-c190kgkt.json` with ready LED indicator
   profile fields.
2. Read and preserve existing `diode.py` behavior for generic diode profiles.
3. Extend `diode.py` with `diode_role == "led_indicator"` checks only.
4. Adjust `motor_sensor_controller` LED nets if needed so the nominal fixture
   has a bounded current-limited path.
5. Add focused LED tests for:
   - nominal LED indicator path
   - missing current-limit path
   - reversed/inverted polarity path when voltages are inferable
   - SS34 generic diode counts unchanged
6. Extend CLI/coverage tests to prove `D10`-`D17` are validated and diode
   uncovered count drops.
7. Update `docs/interview_qa.md`; add `docs/learning_log.md` only for real
   surprises.
8. Run:

```bash
uv run pytest -q tests/validation/test_diode.py tests/test_cli_validator_ui.py tests/validation/test_coverage_priority.py
uv run pytest -q
uv run ruff check .
```

## Stop Conditions

- The implementation would require dispatching by MPN or part-number text.
- Current-path detection requires broad graph search beyond immediate schematic
  neighbors.
- Existing non-LED validator counts change.
- The profile would need unverifiable private or non-public datasheet claims.

