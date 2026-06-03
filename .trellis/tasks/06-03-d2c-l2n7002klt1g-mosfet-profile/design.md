# D2c Design

## Scope

D2c adds one reusable reviewed datasheet profile:
`data/datasheet_profiles/l2n7002klt1g.json`.

The mainboard is the smoke target, not the identity source of truth. The profile
must be reusable by public MPN on any future project, while the mainboard's
Chinese BOM value remains a project-specific matching aid handled by the
document/index and BOM layers.

## Data Flow

The intended flow is:

1. Public LRC datasheet facts are encoded into a structured profile.
2. `suggest_profile_candidates()` loads ready profiles and indexes
   `part_number` plus safe public aliases.
3. `design-validator-ui` auto-matches BOM identities to profile candidates.
4. `validate_component_against_profile()` dispatches through
   `recommended.topology_family = "mosfet"`.
5. `validate_mosfet()` uses the profile pin numbers to find schematic pins and
   reports deterministic connectivity, Vgs, and Vds checks.
6. Project Markdown/HTML/JSON render profile evidence and document coverage
   without mutating verdicts in the report layer.

## Profile Contract

The profile should follow existing MOSFET profiles:

- `part_number`: `L2N7002KLT1G`
- `part_number_aliases`: only public order variants from the LRC datasheet,
  such as `L2N7002KLT3G`.
- `review_status`: `ready`
- `recommended.topology_family`: `mosfet`
- `recommended.polarity`: `n_channel`
- `pin_function`: `{"1": "Gate", "2": "Source", "3": "Drain"}`
- `abs_max.vds`: `60.0`
- `abs_max.vgs`: `20.0`
- `abs_max.id`: conservative steady-state 25 C rating from the datasheet
  maximum-ratings table, with pulsed current captured separately if useful.

Evidence tokens should use the established local profile style:
`datasheet:l2n7002klt1g.pdf#p1`.

## Boundaries

No validator changes are expected. Existing dispatch is already family-based:

```python
if family == "mosfet":
    from hardwise.validation.mosfet import validate_mosfet
```

D2c should not add an MPN-specific branch. If the existing MOSFET validator
cannot handle the selected group, stop and revise the plan instead of widening
the implementation.

Document coverage remains separate from profile validation. D2b's document row
proves that a public datasheet is available; D2c's reviewed profile is what
allows deterministic electrical checks.

## Compatibility

Adding one ready profile changes auto-match coverage for projects that contain
`L2N7002KLT1G` as an MPN or safe alias. That is intended. It should not change
matching for unrelated transistor groups, and it should not make same-family
rows match by family alone.

The mainboard smoke is expected to increase validated/profile-matched coverage
for the 106-refdes selected group. The exact PASS/WARN split should be measured
after implementation because many schematic nets may not have static voltage
hints; WARN is acceptable where the validator cannot infer Vgs/Vds.

## Rollback

The rollback is simple: remove `data/datasheet_profiles/l2n7002klt1g.json` and
the focused tests/docs added for D2c. No migrations or persistent user data are
involved.
