# Electrical Validator Fix Implementation Plan

## Checklist

1. Load backend validation/reporting specs via `trellis-before-dev`.
2. Add regression tests first:
   - buck misplaced freewheel diode terminal;
   - BAS316 used as buck freewheel diode;
   - MOSFET negative Vds overstress;
   - needs-review profile direct validation;
   - gate-driver wording expectations.
3. Update `validation/topology.py` Schottky classification.
4. Update `validation/dcdc.py` to prove buck inductor/diode second-terminal
   paths before PASS.
5. Update `validation/mosfet.py` Vds stress handling and wording.
6. Update `validation/gate_driver.py` summaries/check labels conservatively
   without changing schema.
7. Add the needs-review component-level WARN in `validation/component.py`.
8. Run focused tests, then full `uv run pytest -q` and `uv run ruff check .`.
9. Update learning/spec notes only if implementation reveals a new reusable
   rule beyond the existing path-evidence guideline.

## Validation Commands

- `uv run pytest tests/validation -q`
- `uv run pytest tests/agent/test_validation_bridge.py tests/report/test_component_validation_markdown.py tests/report/test_validator_ui.py -q`
- `uv run pytest -q`
- `uv run ruff check .`

## Risk / Rollback

- Risky modules: `src/hardwise/validation/dcdc.py`,
  `src/hardwise/validation/topology.py`, `src/hardwise/validation/mosfet.py`,
  `src/hardwise/validation/gate_driver.py`, and
  `src/hardwise/validation/component.py`.
- If path inference becomes too strict for existing nominal fixtures, prefer
  WARN with explicit "cannot prove path" wording over broad PASS.
- Do not broaden into PCB layout, SI/PI, thermal, switching loss, or full
  protocol compliance.

