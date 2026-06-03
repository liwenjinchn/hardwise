# Allegro AI topology and document discovery

## Goal

Integrate three independently verifiable workbench/C-stage deliverables into one
auditable closeout:

- A topology tool surface for the right-bottom Workbench AI.
- A deterministic document-coverage provider over local public document indexes.
- D1 mainboard profile-gap analysis that turns a real public-safe Allegro/PST
  folder plus Chinese `.xlsx` BOM into grouped coverage and next-family
  planning artifacts.

This parent task records the cross-child contract. Each child owned its own
implementation, verification, and acceptance evidence.

## Completed Child Deliverables

1. `06-03-workbench-ai-topology-tools`
   - Added `get_component_context`, `get_net_context`, `search_nets`, and
     `summarize_project_topology`.
   - Answers are bounded to parsed Allegro/PST component-pin-net facts.
2. `06-03-document-discovery-provider`
   - Added workbench AI document provider tools over existing local public
     document-index state.
   - Added `serve-workbench --document-index` parity with static workbench
     input.
3. `06-03-mainboard-profile-gap-analysis`
   - Added narrow Chinese `.xlsx` BOM intake for `RFMS5H2TABom(13).xlsx`.
   - Produced mainboard D1 workbench/index/document-candidate/next-family
     artifacts.

## Integrated Commit

The three child deliverables landed together in:

```text
9e0df0d feat(workbench): expose document and topology context
```

Final gates before that commit:

```text
uv run pytest -q      # 482 passed, 7 deselected
uv run ruff check .   # passed
git diff --check      # passed
```

## Acceptance Criteria

- [x] Workbench AI topology questions use structured parsed-topology tools
      rather than model memory.
- [x] Workbench AI document-coverage questions use deterministic local
      document-index provider tools.
- [x] Missing document indexes fail closed as structured `not_configured`
      results instead of invented document candidates.
- [x] D1 mainboard topology imports successfully: 8180 components, 6918 nets,
      and 24563 properties.
- [x] D1 Chinese `.xlsx` BOM maps `位号 -> refdes`, `数量 -> quantity`,
      `名称 -> value/description`, and keeps `编号` as source item number
      rather than MPN.
- [x] D1 mainboard grouped coverage artifacts are generated:
      8180 components, 7248 BOM matched, 6573 validated, 1607 manual,
      195 component groups, 75 document candidates, and 6 next-family advisory
      families.
- [x] No child deliverable adds PCB/layout, boardview, PLM, supplier, lifecycle,
      price, availability, or internal hardware scope.
- [x] No manual/no-profile D1 rows are promoted to PASS/WARN/ERROR without a
      reviewed profile and deterministic validator.

## D2 Handoff

The next D slice should not start with the `unknown` family bucket even though
it is large. D2 should first use the three `try_existing_validator_profile`
families from D1:

- `ic`: 141 uncovered refdes across 31 groups.
- `transistor`: 143 uncovered refdes across 3 groups.
- `diode`: 81 uncovered refdes across 10 groups.

Recommended split:

- D2a: select one top family from the D1 advisory.
- D2b: backfill public document-index evidence for that selected family.
- D2c: implement one reviewed profile/validator slice only after evidence is
  sufficient.
- D2d: rerun the mainboard smoke and record whether manual coverage moved.

## Out Of Scope

- New validator/profile implementation in this parent closeout.
- Live datasheet search, supplier lookup, PLM, lifecycle, pricing, or stock.
- PDF fact extraction or L2 grounded-LLM verdicts.
- PCB `.brd`, boardview, placement, routing, simulation, or post-layout
  conclusions.
