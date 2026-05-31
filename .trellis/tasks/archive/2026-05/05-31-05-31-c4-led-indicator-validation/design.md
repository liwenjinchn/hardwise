# Design

## Boundary

This is an L1 deterministic slice for LED indicators only. It is not a generic
diode expansion and does not introduce L2/LLM claims.

## Profile Contract

The new profile uses the existing diode dispatch contract:

```json
{
  "review_status": "ready",
  "recommended": {
    "topology_family": "diode",
    "diode_role": "led_indicator",
    "requires_current_limit": true
  }
}
```

The profile's pin names remain `Anode` and `Cathode`, so existing diode helpers
can find pins by profile name.

## Validator Contract

`validate_diode()` keeps the existing three checks for all diode profiles:

- cathode connectivity
- anode connectivity
- reverse voltage

For `diode_role == "led_indicator"`, it appends LED-specific checks:

- LED polarity/current path: when net voltages are inferable, anode voltage must
  be greater than cathode voltage; if not inferable, return WARN.
- Current limiting: when `requires_current_limit` is true, the anode or cathode
  net must have a resistor neighbor other than the LED itself; otherwise return
  ERROR.

This is schematic connectivity only. It does not infer current magnitude or
thermal/optical behavior.

## Fixtures

Use existing `motor_sensor_controller` to prove C3 gap closure for D10-D17.
Add a focused tiny fixture for must-catch LED failure.

## Allowed Count Changes

- `motor_sensor_controller` validated count may increase by D10-D17.
- Manual count may decrease by D10-D17.
- Existing deterministic rows such as U12/U8/U3 must keep their current
  statuses.
- Recommendation diode uncovered count should drop; other family ranking logic
  should not be altered.

