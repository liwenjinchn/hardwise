# C4b MMBT3904 transistor validation

## Goal

Add reviewed public MMBT3904 profile and prove Q10-Q15 in the public-safe synthetic Allegro fixture move from L3 manual coverage gap to L1 deterministic BJT validation rows.

## Requirements

- Use only public datasheet/profile facts and the public-safe synthetic Allegro
  fixture. Do not introduce private hardware data.
- Add a reviewed `MMBT3904` ready profile that dispatches through the existing
  `recommended.topology_family="bjt"` validator.
- Do not change BJT dispatch semantics or broaden into generic transistor,
  MOSFET, beta/current-gain, base-resistor sizing, thermal, simulation, or PCB
  layout checks.
- Align the Q10-Q15 fixture pins with the public SOT-23 MMBT3904 pinout before
  treating them as deterministic rows.
- Preserve C4 LED behavior and existing deterministic findings.
- Keep the fixture narrative as public-safe synthetic Allegro, not a real public
  project board.

## Acceptance Criteria

- [x] Q10-Q15 match `data/datasheet_profiles/mmbt3904.json` and produce L1
      deterministic BJT validation rows.
- [x] `recommend-next-family` no longer ranks the MMBT3904 transistor group as
      the highest uncovered family.
- [x] Focused tests prove the public MMBT3904 pinout and existing BJT validator
      behavior for the new profile.
- [x] CLI/ranking tests reflect the changed validated/manual counts without
      changing non-transistor validation truth.
- [x] `docs/interview_qa.md`, `docs/learning_log.md`, and Trellis task records
      capture the C4b result and boundary.
- [x] `uv run pytest -q`, `uv run ruff check .`, and a C4b smoke pass.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
