# D3b LN2312LT1G MOSFET pin-alias coverage

## Goal

Move the existing public-reviewed `LN2312LT1G` MOSFET profile from a
mainboard coverage gap into deterministic validation coverage for schematic
symbols that export MOSFET terminal labels (`G/S/D`) instead of datasheet
package pin numbers (`1/2/3`).

## Requirements

- Reuse the existing MOSFET validator family; do not add a new validation
  family.
- Keep datasheet pin facts as package pins `1=Gate`, `2=Source`, `3=Drain`;
  any local-symbol adaptation must be explicit and reviewable.
- Allow profile candidate matching to accept `LN2312LT1G` when all profile pins
  can resolve through explicit schematic pin aliases.
- Validate a focused Allegro fixture where `Q9.G/S/D` maps to the reviewed
  `LN2312LT1G` profile and produces a deterministic PASS.
- Do not touch the D3a MPQ8626 evidence-to-contract path, document cache,
  Datasheets.com adapter, HTML/PDF ingest pipeline, PLM, supplier, PCB, or
  simulation scope.

## Acceptance Criteria

- [x] `data/datasheet_profiles/ln2312lt1g.json` carries explicit
      `schematic_pin_aliases` for Gate/Source/Drain.
- [x] Candidate generation accepts `LN2312LT1G` when schematic pins are
      `G/S/D` and rejects only unresolved profile pins.
- [x] MOSFET pin-level and component-level checks resolve the aliases without
      changing the public datasheet pin numbers or evidence tokens.
- [x] A focused target manifest and UI smoke validate `Q9` as PASS.
- [x] Focused tests pass for MOSFET validation, profile candidates, profile
      contract storage, and the UI smoke.

## Notes

- This is a lightweight task; implementation notes live in `implement.md`.
