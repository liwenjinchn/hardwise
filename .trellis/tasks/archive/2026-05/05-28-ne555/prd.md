# NE555 timer validator

## Goal

Add NE555 timer as a new validated component family, filling the oscillator/timer gap in the design-validator workbench.

## Requirements

- Public structured profile at `data/datasheet_profiles/ne555.json` (schema v2 with pins[])
- Pins: VCC, GND, TRIG, THRESH, OUT, DISCH, CTRL (7 pins — the classic NE555 pinout)
- `topology_family: oscillator_timer`
- Family validator checks: VCC supply range (4.5V–16V), GND connection, TRIG/THRESH connectivity to RC network, OUT connectivity, DISCH connectivity to timing network, CTRL bypass capacitor presence
- Synthetic Allegro+BOM fixture in `tests/fixtures/allegro/`
- Dispatch registered in `validation/component.py`
- `design-validator-ui` auto-matches NE555 in mixed fixture

## Acceptance Criteria

- [ ] Profile JSON passes schema v2 validation
- [ ] Validator produces PASS for nominal astable fixture (VCC=12V, TRIG/THRESH connected to RC, OUT drives load, DISCH to timing R, CTRL has 100nF bypass)
- [ ] Validator produces ERROR for out-of-range VCC, floating TRIG/THRESH, or missing CTRL bypass cap
- [ ] `uv run pytest -q` passes (new tests added)
- [ ] `uv run ruff check .` passes

## Constraints

- Pre-Layout schematic review only
- No PCB/layout/supplier/PLM scope
- No frequency calculation or timing accuracy verification (that requires netlist math, out of scope)
