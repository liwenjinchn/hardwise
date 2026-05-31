# C4 LED Indicator Deterministic Validation

## Goal

Use C3's diode-family coverage ranking to convert the `LTST-C190KGKT`
LED-indicator group from L3 manual/no-profile coverage into L1 deterministic
validation rows.

## Requirements

1. Add a reviewed, ready structured profile for `LTST-C190KGKT`.
2. Keep validator dispatch on `recommended.topology_family == "diode"`.
3. Add LED-indicator-specific diode checks keyed only by structured profile
   fields such as `recommended.diode_role == "led_indicator"`.
4. Validate `D10`-`D17` in `motor_sensor_controller` via the new profile.
5. Add at least one must-catch LED indicator fixture with a stable
   polarity/current-path finding.
6. Update tests and docs to prove C3 ranking drove an L3-to-L1 C4 slice.

## Non-Goals

- Do not create a generic LED validator or a parallel `led.py` dispatch path.
- Do not cover TVS, Schottky/freewheel, optical, thermal, brightness, or current
  magnitude sizing.
- Do not key behavior by MPN text.
- Do not use L2 grounded LLM logic or auto-generate datasheet profiles.
- Do not change existing non-LED diode, buck, gate-driver, MCU, MOSFET, BJT, or
  connector validator semantics.

## Acceptance Criteria

- `LTST-C190KGKT` profile has `review_status="ready"` and
  `recommended.topology_family="diode"`.
- LED-specific checks run only when `recommended.diode_role` is
  `led_indicator`.
- Existing `SS34` diode tests keep their current expected counts.
- `motor_sensor_controller` validated rows increase only because `D10`-`D17`
  now match the LED profile.
- `recommend-next-family` diode uncovered count drops after the profile lands.
- A focused fixture proves a reversed/invalid LED indicator path yields a stable
  deterministic finding.
- `uv run pytest -q` and `uv run ruff check .` pass.

