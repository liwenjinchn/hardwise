# Implementation Plan

## Checklist

1. Read applicable specs and existing validator patterns.
2. Add shared `is_ground_net()` to `src/hardwise/validation/pins.py` and update internal use.
3. Update `src/hardwise/validation/mcu.py` to import and use `is_ground_net()`.
4. Add pure-function `src/hardwise/validation/diode.py`.
5. Add pure-function `src/hardwise/validation/connector.py`.
6. Update `src/hardwise/validation/component.py` with family-only `diode` and `connector` dispatch branches.
7. Add SS34 and connector profiles from `origin/try/trellis`.
8. Add Allegro fixtures from `origin/try/trellis`.
9. Add focused tests for diode and connector behavior.
10. Run targeted tests, then full `pytest` and `ruff`.
11. Update validation spec if the new shared helper/dispatch convention needs durable capture.
12. Commit with a conventional message; do not push.

## Validation Commands

```bash
uv run pytest tests/validation/test_diode.py tests/validation/test_connector.py -q
uv run pytest tests/validation/test_component.py -q
uv run pytest -q
uv run ruff check .
```

## Risky Files

- `src/hardwise/validation/component.py`: only add family-only branches for new families.
- `src/hardwise/validation/pins.py`: expose helper without changing voltage semantics.
- `src/hardwise/validation/mcu.py`: refactor ground helper only; preserve checks.
- `data/datasheet_profiles/*.json`: copied profiles must load under current Pydantic model.

## Stop Conditions

- Tests reveal migrated connector/diode profiles are incompatible with current parser assumptions.
- New family dispatch requires MPN fallback to pass tests.
- Ground helper refactor changes existing MCU expected behavior unexpectedly.
