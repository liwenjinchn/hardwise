# Electrical Domain Review Design

## Boundaries

This task is a professional correctness audit, not a feature implementation.
The deliverable is a findings-first review of Hardwise's electrical-domain
modeling and validation algorithms.

The audit must respect the repository's public-demo boundary:

- Use repository code, tests, fixtures, and public/releasable references,
  including the user-provided directories after the user's public-status
  clarification.
- Do not derive rules from any material later found to be private, confidential,
  or not reproducible outside the user's environment.
- Treat interface standards and public datasheets as background references,
  but keep findings grounded in local code lines and tests.

## Review Targets

- Profile schema and structured electrical facts:
  `src/hardwise/ir/profile.py`
- Generic pin validation and net-voltage inference:
  `src/hardwise/validation/pins.py`
- Component validation dispatcher and shared report shape:
  `src/hardwise/validation/component.py`,
  `src/hardwise/validation/types.py`
- Family-specific validators:
  `dcdc.py`, `gate_driver.py`, `mcu.py`, `i2c_mux.py`, `diode.py`,
  `connector.py`, `mosfet.py`, `bjt.py`, and helper modules.
- Report wording that may overclaim electrical evidence:
  component validation markdown, validator UI, and project workbench renderers.
- Tests under `tests/validation/`, `tests/report/`, and relevant CLI tests.

## Correctness Lens

Each finding should classify the issue as one of:

- correctness bug: a check computes the wrong electrical quantity or polarity
- overclaiming risk: wording implies unsupported PCB/SI/PI/timing/thermal/PLM
  capability
- missing model: a real electrical dimension is intentionally out of scope but
  needs clearer WARN/manual handling
- test gap: code appears reasonable but lacks a regression for a professional
  edge case
- acceptable MVP limitation: correct to defer, no code change needed

## Review Output

The final response should lead with actionable findings ordered by severity,
with local file links and line references. If no serious issues are found,
state that clearly and list residual risk areas.
