# TLP250 optocoupler driver validator

## Goal

Add TLP250 optocoupler gate driver as a new validated component family, filling the isolation boundary gap in the design-validator workbench.

## Requirements

- Public structured profile at `data/datasheet_profiles/tlp250.json` (schema v2 with pins[])
- Pins: VCC, GND, LED anode, LED cathode, VO, GND_out (6 pins, input/output sides separated)
- `topology_family: optocoupler_driver`
- Family validator checks: VCC supply range on output side, LED side current-limiting resistor presence, input/output ground isolation (GND ≠ GND_out), VO connectivity to gate load
- Synthetic Allegro+BOM fixture in `tests/fixtures/allegro/`
- Dispatch registered in `validation/component.py`
- `design-validator-ui` auto-matches TLP250 in mixed fixture

## Acceptance Criteria

- [ ] Profile JSON passes schema v2 validation
- [ ] Validator produces PASS for nominal fixture (VCC=15V, LED has series resistor, GND isolated from GND_out, VO reaches Q-device gate)
- [ ] Validator produces ERROR for shorted grounds (GND = GND_out), missing LED resistor, or out-of-range VCC
- [ ] `uv run pytest -q` passes (new tests added)
- [ ] `uv run ruff check .` passes

## Constraints

- Pre-Layout schematic review only
- No PCB/layout/supplier/PLM scope
- No CMTI (common-mode transient immunity) or propagation delay analysis
