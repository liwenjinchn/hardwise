# LM358 op-amp validator

## Goal

Add LM358 dual op-amp as a new validated component family, filling the general-purpose amplifier gap in the design-validator workbench.

## Requirements

- Public structured profile at `data/datasheet_profiles/lm358.json` (schema v2 with pins[])
- Pins: VCC, VEE/GND, IN_A+, IN_A-, OUT_A, IN_B+, IN_B-, OUT_B (8 pins — dual op-amp)
- `topology_family: op_amp`
- Family validator checks: VCC supply range (3V–32V single or ±1.5V–±16V dual), VEE/GND connection, both channels' IN+/IN-/OUT connectivity, unused channel handling (output tied to IN- for unity-gain buffer, or inputs not floating)
- Synthetic Allegro+BOM fixture in `tests/fixtures/allegro/`
- Dispatch registered in `validation/component.py`
- `design-validator-ui` auto-matches LM358 in mixed fixture

## Acceptance Criteria

- [ ] Profile JSON passes schema v2 validation
- [ ] Validator produces PASS for nominal fixture (VCC=12V, VEE=GND, both channels have feedback path, unused channel properly terminated)
- [ ] Validator produces ERROR for out-of-range VCC, floating inputs on unused channel, or disconnected output
- [ ] `uv run pytest -q` passes (new tests added)
- [ ] `uv run ruff check .` passes

## Constraints

- Pre-Layout schematic review only
- No PCB/layout/supplier/PLM scope
- No gain calculation, bandwidth, or slew rate verification (out of scope)
