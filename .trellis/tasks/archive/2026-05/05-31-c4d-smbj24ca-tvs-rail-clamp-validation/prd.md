# C4d SMBJ24CA TVS rail clamp validation

## Goal

Close one remaining C4c diode coverage gap by adding reviewed public SMBJ24CA
bidirectional TVS rail-clamp validation for D20 in the public-safe synthetic
Allegro fixture.

## Requirements

- Use only public Littelfuse SMBJ/SMBJ24CA datasheet facts and the public-safe
  synthetic Allegro fixture. Do not introduce private hardware data.
- Add a reviewed `SMBJ24CA` ready profile that dispatches through the existing
  `recommended.topology_family="diode"` validator.
- Use a structured sub-role such as `recommended.diode_role="bidirectional_tvs"`
  for TVS-only checks. Do not add a new dispatch family or MPN fallback branch.
- Validate only deterministic schematic-level facts for this slice:
  terminal connectivity, one terminal tied to a recognized ground
  reference, and protected rail voltage not exceeding the profile working
  standoff voltage when the rail voltage can be inferred.
- Do not validate surge-current sizing, ESD standard coverage, clamping
  waveform behavior, capacitance suitability, thermal behavior, PCB/layout,
  placement, routing, or connector protection completeness.
- Preserve C4/C4b/C4c LED, BJT, and analog IC behavior.
- Keep the fixture narrative as public-safe synthetic Allegro, not a real public
  project board.

## Acceptance Criteria

- [x] D20 matches `data/datasheet_profiles/smbj24ca.json` and produces an L1
      deterministic TVS validation row.
- [x] `recommend-next-family` no longer lists `SMBJ24CA` in the remaining diode
      identity sample.
- [x] Focused tests prove the public SMBJ24CA bidirectional TVS profile, nominal
      rail-to-ground clamp PASS, and rail-above-standoff ERROR.
- [x] CLI/ranking tests reflect the changed validated/manual counts without
      changing non-D20 validation truth.
- [x] `docs/interview_qa.md`, `docs/learning_log.md`, and Trellis task records
      capture the C4d result and boundaries.
- [x] `uv run pytest -q`, `uv run ruff check .`, and a C4d smoke pass.

## Notes

- Public source URLs checked for profile facts:
  - https://www.littelfuse.com/products/overvoltage-protection/tvs-diodes/surface-mount/smbj/smbj24ca
  - https://www.littelfuse.com/assetdocs/tvs-diodes-smbj-series-datasheet?assetguid=ba555e99-a12d-4f72-a0b6-86b06c67171e
