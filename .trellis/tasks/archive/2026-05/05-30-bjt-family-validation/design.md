# BJT Family Validation Design

## Architecture

Add one family validator that reuses MOSFET's pin/reference discipline and diode's one-direction overstress shape:

```text
DatasheetProfile(recommended.topology_family="bjt")
  -> validate_component_against_profile()
  -> _validate_component_topology()
  -> validate_bjt(component, profile, design)
  -> list[ComponentValidation]
```

No new report object is needed. `ValidationReport` already aggregates generic pin checks plus component-level checks and all existing CLI/UI paths consume that object.

## Pin Model

Use profile pin names only to find profile pin numbers, then lookup schematic pins by number:

- Base: control input (`analog_input` or `logic_input`)
- Collector: switched/output current path (`switch_output`)
- Emitter: reference/current return node (`switch_node`)

The implementation must not use `component.pin_by_name()` for schematic pins.

## Electrical Checks

Minimum component checks:

- `bjt_base_connectivity`
- `bjt_collector_connectivity`
- `bjt_emitter_connectivity`
- `bjt_vebo_rating` if profile has `abs_max.vebo`
- `bjt_vceo_rating` if profile has `abs_max.vceo`

`Vbe = voltage(base) - voltage(emitter)`. If either voltage is unknown, return WARN and explicitly state that Hardwise is not assuming emitter is ground. For NPN low-side cases this naturally becomes base-to-ground only because emitter is actually on a ground net.

Do **not** check `abs(Vbe)` like MOSFET `Vgs`. Positive forward `Vbe ~= 0.6-0.7 V` is normal diode-junction operation; forward overstress is primarily a current / base-resistor sizing problem and is out of this phase. The BJT abs-max check is reverse base-emitter breakdown: for the first NPN family, compute `reverse_be_voltage = emitter_voltage - base_voltage`; if `reverse_be_voltage > abs_max.vebo`, return ERROR. This follows the same one-direction shape as diode reverse voltage.

`Vce = voltage(collector) - voltage(emitter)`. If unknown, return WARN. If profile has `abs_max.vceo`, ERROR when `Vce > abs_max.vceo`. Keep polarity/simple NPN semantics for the first family; do not model PNP in this slice.

All numeric tests for `Vbe` / `Vce` should inject `Net.voltage_hint` for base, emitter, and collector as needed. Realistic values such as `0.7 V` cannot be expressed reliably through the current net-name parser.

## Profile Choice

Use one common public NPN BJT profile, preferably 2N3904 (classic small-signal NPN with clear `VCEO`, `VEBO`, and `VCBO` absolute maximum ratings). Before writing facts, verify the datasheet source and page tokens. The profile should include:

- `recommended.topology_family = "bjt"`
- top-level `abs_max.vebo` for reverse emitter-base breakdown
- top-level `abs_max.vceo` for collector-emitter voltage
- pin rows for Base / Collector / Emitter
- evidence tokens per pin and abs-max fact

Abs-max family facts live in the profile's top-level `abs_max` dictionary, not in each pin's `limits`. Pin `limits` are consumed by generic pin validators; BJT family checks read `profile.abs_max`.

## Compatibility

`component.py` gets one new dispatch branch:

```python
if family == "bjt":
    from hardwise.validation.bjt import validate_bjt
    return validate_bjt(component, profile, design)
```

No MPN fallback is allowed. Tests must mutate `profile.part_number` and still hit the BJT branch.

The agent `run_component_validation` tool needs no extra wiring for BJT. It already calls `validate_component_against_profile()`; assigning a BJT profile to a refdes is sufficient.

## Rollback

If public profile facts are ambiguous, keep the validator and fixtures synthetic only inside tests, but do not ship a tracked profile claiming unverified datasheet evidence. In that case, stop and ask before widening scope.
