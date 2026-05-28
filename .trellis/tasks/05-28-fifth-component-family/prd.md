# Add 4 component family validators (parent)

## Goal

Expand Hardwise design-validator from 4 validated component families to 8, filling gaps in analog, isolation, timer, and amplifier categories. The demo workbench should show richer "已验证" coverage to match the target product screenshot.

## Requirements

- Each child task adds one component family: profile JSON + family-specific validator + synthetic fixture + dispatch registration + demo fixture integration
- All validators follow the existing dispatch pattern: `topology_family` string in profile JSON routes to family validator
- Each family has a public datasheet profile in `data/datasheet_profiles/`
- Each family has a synthetic Allegro+BOM fixture in `tests/fixtures/allegro/`
- `design-validator-ui` workbench auto-matches and validates all 8 families in one mixed fixture
- All existing tests + lint still pass after each child merges

## Child Tasks

| # | Family | topology_family | Profile | Key Checks |
|---|---|---|---|---|
| A | INA180 current sense amp | `current_sense_amp` | `ina180.json` | VCC/GND supply range, IN+/IN- common-mode, OUT load |
| B | TLP250 optocoupler driver | `optocoupler_driver` | `tlp250.json` | LED side current limiting, output VCC/GND, isolation boundary |
| C | NE555 timer | `oscillator_timer` | `ne555.json` | VCC/GND/TRIG/THRESH/OUT/DISCH/CTRL 7-pin complete check |
| D | LM358 op-amp | `op_amp` | `lm358.json` | VCC/VEE/IN+/IN-/OUT, dual-channel symmetry |

## Acceptance Criteria

- [ ] All 4 child tasks archived successfully
- [ ] `design-validator-ui` workbench shows 8 validated families in mixed fixture
- [ ] `uv run pytest -q` passes
- [ ] `uv run ruff check .` passes
- [ ] `docs/PLAN.md` discharged entry for V3.11

## Scope Boundary

- Pre-Layout schematic review node only
- No `.brd`, boardview, placement, routing, PCB geometry
- No supplier/PLM/lifecycle/pricing
- No firmware, clock-tree, timing simulation
