# C4e BAS316 small-signal diode profile

## Goal

Close the next remaining diode coverage gap by adding reviewed public BAS316
small-signal diode profile coverage for D21 in the public-safe synthetic Allegro
fixture.

## Requirements

- Use only public Nexperia BAS316 datasheet facts and the public-safe synthetic
  Allegro fixture. Do not introduce private hardware data.
- Add a reviewed `BAS316` ready profile that dispatches through the existing
  `recommended.topology_family="diode"` validator.
- Reuse the existing two-terminal diode checks. Do not add a new validator,
  dispatch branch, or MPN fallback.
- Prove D21 becomes an L1 deterministic diode row even though the CANH rail
  voltage is not statically inferable.
- Do not implement BAV99 dual-diode modeling in this slice.
- Preserve C4/C4b/C4c/C4d LED, BJT, analog IC, and TVS behavior.
- Keep the fixture narrative as public-safe synthetic Allegro, not a real public
  project board.

## Acceptance Criteria

- [x] D21 matches `data/datasheet_profiles/bas316.json` and produces an L1
      deterministic diode validation row.
- [x] `recommend-next-family` no longer lists `BAS316` in the remaining diode
      identity sample.
- [x] Focused tests prove the public BAS316 pinout, nominal reverse-voltage
      PASS, and reverse-voltage overstress ERROR.
- [x] CLI/ranking tests reflect the changed validated/manual counts without
      changing non-D21 validation truth.
- [x] `docs/interview_qa.md`, `docs/learning_log.md`, and Trellis task records
      capture the C4e result and boundaries.
- [x] `uv run pytest -q`, `uv run ruff check .`, and a C4e smoke pass.

## Notes

- Public source checked for profile facts:
  - https://assets.nexperia.com/documents/data-sheet/BAS316.pdf
