# BJT family validation

## Goal

Ship `docs/PLAN.md` post-migration roadmap Phase 3: add one deterministic BJT component-family validator that reuses the three-terminal reference-node lesson without copying MOSFET's symmetric gate-limit math.

The credibility target is narrow and hardware-correct: Hardwise should catch a reverse base-emitter breakdown risk (`Vebo`) by computing `Vbe = V_base - V_emitter`, not by comparing base voltage to ground. A positive forward `Vbe ~= 0.6-0.7 V` is a normal operating point, not an absolute-voltage-overstress check.

## Confirmed Facts

- `docs/PLAN.md` Phase 3 says: `validation/bjt.py` reusing the reference-node pattern (`Vbe = base - emitter`); P-channel/body-diode notes stay backlog; dispatch stays `topology_family`-only.
- `src/hardwise/validation/mosfet.py` already implements the reusable pin/reference discipline: pin lookup by profile pin number, differential voltage checks, WARN when either reference voltage is unknown, and no assumption that source/emitter is ground.
- `src/hardwise/validation/diode.py` is the closer template for the B-E overstress check because it checks one voltage direction (`reverse_voltage = cathode - anode`) rather than `abs(...)`.
- `src/hardwise/validation/pins.py` only infers voltages from ground aliases, rail-like net names, or `Net.voltage_hint`; tests with realistic `~0.7 V` base/emitter values must inject `voltage_hint`.
- `.trellis/spec/backend/validation-guidelines.md` already says three-terminal control devices must use Gate/Base as control input and Source/Emitter as `switch_node`, and explicitly forbids generalizing low-side source/emitter to ground.
- `src/hardwise/validation/component.py` dispatches validators by `profile.recommended["topology_family"]` only. This must stay true for BJT.
- Existing validator tests build `Design` from Allegro netlist + BOM fixtures, then call `validate_component_against_profile()`.
- The existing `run_component_validation` agent tool calls `validate_component_against_profile()`; once a BJT refdes has an assigned profile, no extra agent/tool wiring is needed.

## Requirements

- Add a BJT validator under `src/hardwise/validation/bjt.py`.
- Add a BJT datasheet profile under `data/datasheet_profiles/` using public datasheet facts only.
- Add Allegro netlist + BOM fixtures for one nominal BJT case and at least one bad base-drive case.
- Add tests proving:
  - nominal BJT validation passes,
  - a high-side / non-ground-emitter case measures `Vbe` against emitter, not ground,
  - a real reverse B-E breakdown case errors by checking `Vebo` (`emitter - base > abs_max.vebo` for NPN),
  - unknown base/emitter voltage returns WARN rather than assuming ground,
  - dispatch works by `topology_family="bjt"` even if `part_number` changes.
- Keep scope to deterministic schematic-side validation. No PCB, simulation, SPICE, supplier, PLM, lifecycle, pricing, or thermal modeling.
- Update docs that record shipped evidence (`docs/interview_qa.md`, `docs/learning_log.md`, `docs/PLAN.md`). Update validation spec if implementation teaches a reusable BJT convention.

## Acceptance Criteria

- [ ] `validate_component_against_profile()` dispatches BJT profiles by `recommended.topology_family == "bjt"`.
- [ ] BJT validator emits component checks for base/collector/emitter connectivity, reverse B-E breakdown (`Vebo`), and collector-emitter voltage (`Vceo`) if profile facts support it.
- [ ] Tests include a non-ground-emitter PASS case that requires `Vbe = base - emitter` and uses explicit `voltage_hint` for base/emitter voltages.
- [ ] Tests include a reverse B-E breakdown case that base-to-ground logic would miss but emitter-referenced `Vbe` catches as `ERROR`.
- [ ] Numeric `Vbe`/`Vce` tests inject `voltage_hint` rather than relying on realistic `0.7 V` values in net names.
- [ ] `uv run pytest tests/validation/test_bjt.py -q` passes.
- [ ] `uv run pytest -q` and `uv run ruff check .` pass.
- [ ] `docs/PLAN.md` discharged audit trail records Phase 3 completion.

## Out of Scope

- P-channel MOSFET implementation.
- MOSFET body-diode modeling.
- BJT saturation / beta / base-resistor sizing calculations; positive forward `Vbe` overvoltage is treated as a current/topology problem, not an abs-max voltage comparison in this phase.
- LLM extraction from datasheets.
- New CLI command surface unless existing reports already pick up the family automatically.
