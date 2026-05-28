# INA180 current sense amp validator

## Goal

Add INA180 current-sense amplifier as a new validated component family, filling the analog signal-chain gap in the design-validator workbench.

## Requirements

- Public structured profile at `data/datasheet_profiles/ina180.json` (schema v2 with pins[])
- Pins: VCC, GND, IN+, IN-, OUT, REF (6 pins)
- `topology_family: current_sense_amp`
- Family validator checks: VCC supply range, GND connection, IN+/IN- common-mode within supply, OUT load presence
- Synthetic Allegro+BOM fixture in `tests/fixtures/allegro/`
- Dispatch registered in `validation/component.py`
- `design-validator-ui` auto-matches INA180 in mixed fixture

## Acceptance Criteria

- [ ] Profile JSON passes schema v2 validation
- [ ] Validator produces PASS for nominal fixture (VCC=5V, IN+/IN- within range, OUT connected)
- [ ] Validator produces ERROR for out-of-range VCC or disconnected IN+/IN-
- [ ] `uv run pytest -q` passes (new tests added)
- [ ] `uv run ruff check .` passes

## Constraints

- Pre-Layout schematic review only
- No PCB/layout/supplier/PLM scope
- No timing simulation or bandwidth analysis
