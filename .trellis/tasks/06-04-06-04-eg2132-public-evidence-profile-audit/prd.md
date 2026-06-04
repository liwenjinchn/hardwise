# EG2132 public evidence profile audit

## Goal

Audit EG2132 profile fields against public official datasheet evidence and adjust only source-backed contract/test/docs.

## Requirements

- Use only public official EGmicro evidence for EG2132 datasheet contract
  fields. Prefer the official PDF over conflicting product-page parameter text.
- Keep the profile `ready` only for facts directly supported by public
  page-level evidence: pinout, VCC operating range, VCC absolute maximum,
  HIN/LIN logic thresholds, and bootstrap topology.
- Do not keep board-level bootstrap diode voltage policy as a datasheet profile
  field unless a public source states the numeric requirement directly.
- Preserve deterministic gate-driver validation where schematic topology proves
  a high-side/switch-node rail voltage; otherwise warn instead of guessing.
- Keep the scope to schematic-side validation. Do not add timing/deadtime,
  MOSFET loss, PCB/layout, supplier, PLM, pricing, or lifecycle checks.

## Acceptance Criteria

- [x] `data/datasheet_profiles/eg2132.json` reflects official PDF-backed
      VCC/logic limits and no longer claims a datasheet-backed bootstrap diode
      reverse-voltage minimum.
- [x] `gate_driver_bootstrap` derives diode reverse-voltage requirements from
      schematic switch-node/high-side rail evidence when available.
- [x] EG2132 focused tests cover the corrected public profile fields, the
      high-side-rail-derived diode error path, and the no-rail-evidence WARN
      path.
- [x] Existing EG2132/mixed workbench smoke output still reports deterministic
      errors when the fixture contains enough schematic evidence.
- [x] Full verification passes: focused EG2132 tests, `uv run pytest -q`,
      `uv run ruff check .`, and `git diff --check`.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
