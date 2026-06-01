# Fix electrical validator assumptions

## Goal

Fix the electrical-validator false PASS risks found in the 2026-06-01 domain
audit, so deterministic PASS means the relevant schematic electrical path was
actually validated rather than inferred from a nearby refdes prefix or part
family string.

## Requirements

- Tighten XL1509-style buck topology validation so the output inductor and
  freewheel diode checks verify the relevant second terminals and return WARN
  or ERROR when the path cannot be proven.
- Stop classifying BAS-family small-signal switching diodes as Schottky-style
  buck freewheel candidates unless a future profile explicitly supports that
  role.
- Fix MOSFET Vds validation so large negative drain-to-source stress is not a
  PASS under the current generic MOSFET scope.
- Reduce gate-driver overclaiming by avoiding "gate load" / "switch node"
  language unless the reached Q-prefixed component pin role is known; otherwise
  keep the check as a conservative topology reachability check.
- Prevent `review_status="needs_review"` profiles from surfacing as fully
  deterministic PASS in direct validation paths.
- Preserve the pre-layout schematic-review boundary: no PCB geometry, SI/PI,
  timing, thermal, loss, firmware, supplier, lifecycle, or PLM claims.
- Add or update regression tests for each corrected behavior.

## Acceptance Criteria

- [ ] A buck fixture where the freewheel diode's other terminal is not on a
      recognized return/clamp path no longer reports PASS for the diode path.
- [ ] A buck fixture using `BAS316` as the external freewheel diode no longer
      reports a Schottky-style PASS.
- [ ] A MOSFET fixture with source above drain by more than Vds rating no longer
      reports Vds PASS.
- [ ] Gate-driver output/switch-node summaries no longer imply a proven gate pin
      unless the code has proven pin role from structured data.
- [ ] A `needs_review` profile passed directly to component validation cannot
      return an overall deterministic PASS without an explicit warning/error.
- [ ] Existing nominal validator fixtures still pass where their electrical path
      is actually proven.
- [ ] `uv run pytest tests/validation -q`, targeted affected CLI/report tests,
      `uv run pytest -q`, and `uv run ruff check .` pass before completion.

## Notes

- Source audit:
  `.trellis/tasks/archive/2026-06/06-01-electrical-domain-review/review.md`.
- Existing unrelated planning task left untouched:
  `.trellis/tasks/06-01-windows-compatibility-audit/`.
