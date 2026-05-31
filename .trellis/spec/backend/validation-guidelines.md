# Validation Module Guidelines

> How to implement deterministic component validators safely.

---

## 1. Scope / Trigger

Applies to every validator under `src/hardwise/validation/` (e.g. `op_amp.py`, `timer.py`, `current_sense.py`, `optocoupler.py`, `gate_driver.py`, `dcdc.py`, `mcu.py`).

Trigger: adding or modifying a component-family validator, editing a datasheet profile JSON, or changing `component.py` dispatch.

---

## 2. Signatures

### Validator entry point (dispatched from `component.py`)

```python
def validate_xxx(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    ...
```

### Component-family dispatch

New validators MUST dispatch by `recommended.topology_family` only. Do not add
new `profile.part_number.upper() == "..."` fallback branches; MPNs belong in
profile data and candidate matching, not in dispatcher control flow.

```python
family = str(profile.recommended.get("topology_family", "")).lower()
if family == "connector":
    from hardwise.validation.connector import validate_connector

    return validate_connector(component, profile, design)
```

### Pin lookup

```python
# ALWAYS use pin number (from profile JSON)
pin = component.pin_by_number("8")   # ✅ correct
pin = component.pin_by_name("VCC")   # ❌ WRONG for non-NC pins
```

### Net voltage inference

```python
from hardwise.validation.pins import voltage_for_net

voltage = voltage_for_net(pin.net, self.design)   # ✅ needs design arg
voltage = voltage_from_net_name(pin.net)           # ❌ doesn't exist
```

**Recognized patterns** (returns float or None):
- `"+12V"` → `12.0`
- `"-5V"` → `-5.0`
- `"3V3"` → `3.3`
- `"VBUS"` → `5.0`
- `"GND"`, `"AGND"`, `"DGND"` → `0.0` (ground nets)
- `"SIGNAL_NET"` → `None` (cannot infer)

### Ground-net classification

```python
from hardwise.validation.pins import is_ground_net

if is_ground_net(pin.net): ...      # ✅ shared helper
pin.net.upper() in {"GND", ...}     # ❌ duplicated local ground list
```

`is_ground_net()` recognizes common ground aliases and tokenized variants such
as `HV_GND`. Validators must import it instead of maintaining local sets.

### Net connectivity (feedback / shared components)

```python
# Net.nodes is list[tuple[str, str]] — (refdes, pin_number)
out_components = {node[0] for node in out_net.nodes}   # ✅
out_components = {p.component_refdes for p in out_net.pins}  # ❌ Net has no .pins
```

---

## 3. Contracts

### Datasheet profile (schema v2)

- Every pin MUST have: `name`, `number`, `category`, `function`, `evidence`
- VCC/supply pins MUST use `category: "power_input"` (not `power_supply`) — `pins.py` only handles `power_input` for voltage validation
- Voltage limits go in a flat `limits` dict with keys: `abs_max_voltage`, `recommended_voltage_min`, `recommended_voltage_max`

### Pin category conventions by component type

**Two-terminal passive devices** (diodes, resistors, capacitors):
- Use `switch_node` for both pins (cathode/anode, terminal1/terminal2)
- Validator logic determines polarity based on voltage differential
- Do not infer package pin numbers from fixture wiring. Before marking a
  profile `review_status="ready"`, compare the public datasheet or public ECAD
  pin diagram against the `pin_function` map and add a regression that would
  fail if anode/cathode were swapped.
```json
{"name": "Cathode", "number": "1", "category": "switch_node"},
{"name": "Anode", "number": "2", "category": "switch_node"}
```

**LED indicators**:
- Keep dispatch on `recommended.topology_family: "diode"`; do not add a
  separate `led_indicator` dispatch branch.
- Use a structured sub-role for LED-only checks:
```json
{
  "recommended": {
    "topology_family": "diode",
    "diode_role": "led_indicator",
    "requires_current_limit": true
  }
}
```
- LED-only checks may verify anode/cathode polarity and the presence of a
  one-resistor-hop series-branch current-limit resistor, but must not infer
  current magnitude, brightness, optics, thermal behavior, TVS behavior, or
  Schottky/freewheel suitability.
- Current-limit checks must not treat any resistor attached to a global rail
  (for example `+3V3` or `GND`) as limiting the LED. Require the resistor on an
  LED branch net, and make shared resistor-bank summaries explicit.

**Bidirectional TVS rail clamps**:
- Keep dispatch on `recommended.topology_family: "diode"`; do not add a
  separate TVS dispatch branch.
- Use a structured sub-role for TVS-only checks:
```json
{
  "recommended": {
    "topology_family": "diode",
    "diode_role": "bidirectional_tvs",
    "working_standoff_voltage": 24.0
  }
}
```
- Bidirectional TVS terminals are not cathode/anode oriented. Use neutral pin
  names such as `Terminal 1` and `Terminal 2`.
- TVS checks may verify terminal connectivity, a recognized ground reference,
  and rail-to-ground working voltage against standoff voltage when the rail can
  be inferred. They must not infer surge-current sizing, ESD standard coverage,
  clamp waveform behavior, capacitance suitability, thermal behavior, connector
  completeness, placement, routing, or PCB geometry.

**Three-terminal control devices** (MOSFET, BJT):
- Gate/Base: `analog_input` (analog control) or `logic_input` (digital control)
- Drain/Collector: `switch_output` (switched high-side)
- Source/Emitter: `switch_node` — NOT `ground`. A low-side FET sits its source
  at ground, but a high-side FET sits it on the switch node (swings to the
  rail). Labelling the source `ground` makes the generic pin validator demand
  a ground net and false-ERROR every high-side device.
```json
{"name": "Gate", "number": "1", "category": "analog_input"},
{"name": "Drain", "number": "2", "category": "switch_output"},
{"name": "Source", "number": "3", "category": "switch_node"}
```
- **Vgs is gate-to-source, never gate-to-ground.** Compute
  `Vgs = voltage(gate) - voltage(source)`. The low-side case where source = GND
  is the *only* one where gate-to-ground coincides with Vgs; do not generalise
  it. When the gate or source net has no statically known voltage (PWM drive,
  floating switch node), return WARN — never assume the source is at ground.
  Same rule for `Vds = voltage(drain) - voltage(source)`.
- **BJT base-emitter overstress is directional, not `abs(Vbe)`.** Positive
  `Vbe ~= 0.6-0.7 V` is normal junction operation. For the first NPN validator,
  compute `Vbe = voltage(base) - voltage(emitter)` for reporting, but check
  reverse breakdown as `reverse_be_voltage = voltage(emitter) - voltage(base)`
  against top-level `profile.abs_max["vebo"]`. Do not compare positive forward
  Vbe against VEBO; base-current / resistor sizing is a separate topology check.
  `Vceo` also lives in top-level `profile.abs_max["vceo"]`, not in per-pin
  `limits`. Per-pin `limits` are for generic pin validators only.
- **Package pinout is part-specific.** Do not reuse a TO-92 `2N3904` profile for
  an SOT-23 `MMBT3904`: both may be NPN 3904-family devices, but their package
  pin numbering differs. Add a profile-level pinout regression when introducing
  package variants.

**Multi-pin connectors**:
- VCC pins: `power_input` with `limits` dict
- GND pins: `ground`
- Signal pins: `gpio` (general purpose I/O)
```json
{"name": "VCC", "number": "1", "category": "power_input", "limits": {"abs_max_voltage": 5.0}},
{"name": "GND", "number": "5", "category": "ground"},
{"name": "DATA", "number": "2", "category": "gpio"}
```

**Basic analog IC profiles**:
- Use these only for deterministic pin-level coverage when the slice is not
  adding a behavior-level op-amp, comparator, or current-sense validator.
- Do not invent a `topology_family` value for basic pin-profile-only coverage;
  use a non-dispatch metadata key such as
  `recommended.validation_scope="basic_pin_profile"`.
- Inputs: `analog_input`.
- Push-pull or amplifier outputs: `analog_output`.
- Open-collector comparator outputs: `open_collector_output`.
- Supply pins: `power_input`; add voltage limits only where a single-ended rail
  comparison is meaningful. Do not model dual-supply behavior in generic pin
  rules.
- These categories only prove that profiled pins are present and connected.
  They must not infer gain, comparator threshold, output swing, stability,
  shunt sizing, bandwidth, load current, or PCB/layout behavior.

### ComponentValidation output

- Each check returns exactly one `ComponentValidation` with `check`, `status`, `summary`, optional `evidence`
- Check names must match test expectations (e.g. `op_amp_vcc_range`, `op_amp_in_a_plus_connectivity`)
- `ValidationReport.summary` property returns component-check counts by status (PASS/WARN/ERROR)

---

## 4. Validation & Error Matrix

| Condition | Status | Summary pattern |
|-----------|--------|-----------------|
| Pin not found in component | ERROR | "pin not connected" |
| Pin found but no net | ERROR | "pin not connected" |
| Voltage cannot be inferred | WARN | "cannot infer voltage" |
| Voltage out of abs_max | ERROR | "exceeds maximum" / "below minimum" |
| Voltage out of recommended | WARN | "below recommended" / "above recommended" |
| Feedback path found via shared component | PASS | "feedback through R1_FB" |
| No feedback path | ERROR | "no feedback path" |

---

## 5. Good / Base / Bad Cases

**Good** (nominal op-amp profile, VCC within profile limits, both channels connected): all pin checks PASS.

**Base** (one channel unused, inputs tied to output as voltage follower): connectivity PASS, feedback PASS.

**Bad** (VCC=2V): VCC range check → ERROR "below minimum".

---

## 6. Tests Required

- Nominal fixture: assert `results.status == "PASS"`, `results.summary["PASS"] == N` (N = total check count)
- VCC out-of-range low: assert specific check returns ERROR with "below minimum"
- VCC out-of-range high: assert specific check returns ERROR with "exceeds maximum"
- Floating pins: assert connectivity checks return ERROR
- Disconnected output: assert output connectivity returns ERROR
- All tests must build design from inline netlist + BOM via `parse_allegro_netlist` → `build_design_from_netlist` → `apply_bom_to_design`

---

## 7. Wrong vs Correct

### Wrong

```python
# Using pin_by_name for non-NC pins — always returns None
vcc_pin = component.pin_by_name("VCC")

# Accessing Net.pins — attribute doesn't exist
for p in net.pins: ...

# Using power_supply category for VCC
{"category": "power_supply", "abs_max": {"voltage": 36.0}}

# Pin on two different nets in one test fixture
'FB_B' ; U31.6, U31.7
'OUTPUT_B' ; U31.7
```

### Correct

```python
# Use pin_by_number with the number from the profile
vcc_pin = component.pin_by_number("8")

# Use Net.nodes (list of (refdes, pin_number) tuples)
for node in net.nodes:
    refdes, pin_num = node

# Use power_input category with flat limits dict
{"category": "power_input", "limits": {"abs_max_voltage": 36.0, "recommended_voltage_min": 3.0, "recommended_voltage_max": 32.0}}

# One pin per net — merge into single net for voltage follower
'OUTPUT_B' ; U31.7, U31.6
```

---

## Common Mistakes

### Mistake: `pin_by_name()` returns None for schematic pins

**Symptom**: All connectivity checks ERROR even though pins are connected in the netlist.

**Cause**: `Component.pin_by_name()` only populates NC pin names in V2.1. Schematic pin names are empty strings.

**Fix**: Always use `pin_by_number()` with the number from the profile JSON.

### Mistake: `Net.pins` AttributeError

**Symptom**: `AttributeError: 'Net' object has no attribute 'pins'`

**Cause**: `Net` model has `nodes: list[tuple[str, str]]`, not `pins`.

**Fix**: Use `{node[0] for node in net.nodes}` to get component refdes set.

### Mistake: VCC pin WARN instead of PASS

**Symptom**: VCC pin returns "Pin category has no deterministic V3.3 validation rule yet."

**Cause**: Category `power_supply` is not handled by `pins.py`.

**Fix**: Use `category: "power_input"` with `limits` dict containing `abs_max_voltage`, `recommended_voltage_min`, `recommended_voltage_max`.

### Mistake: Control pin (gate/base) uses power_input category

**Symptom**: Gate pin validation WARNs even though voltage is within range.

**Cause**: `power_input` category expects supply pins, not control signals. Control pins need different validation logic.

**Fix**: Use `category: "analog_input"` for analog control signals (MOSFET gate, op-amp inputs) or `category: "logic_input"` for digital control signals (enable pins, reset pins).

### Mistake: Voltage measurement path includes resistors

**Symptom**: `voltage_for_net` returns `None` for nets with voltage dividers or series resistors.

**Cause**: `voltage_for_net` only recognizes direct voltage sources (nets named `+12V`, `GND`, etc.), not voltage drops across components.

**Fix**: In test fixtures, connect voltage source directly to the pin being measured. For real circuits, add `voltage_hint` to the Net object or use `design.nets[net_name].voltage_hint`.

### Mistake: Two-terminal device uses power_input/output categories

**Symptom**: Diode validation fails or produces incorrect results.

**Cause**: Diodes (and other two-terminal passive devices) should use `switch_node` for both pins, not `power_input` or `power_output`.

**Fix**: Use `category: "switch_node"` for both cathode and anode pins. Let the validator logic determine polarity based on voltage differential.

**Example**:
```json
{
  "name": "Cathode",
  "number": "1",
  "category": "switch_node"
},
{
  "name": "Anode",
  "number": "2",
  "category": "switch_node"
}
```
