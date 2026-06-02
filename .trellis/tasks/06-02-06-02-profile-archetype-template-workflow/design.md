# Profile archetype template workflow design

## Architecture

The existing contracts are already close to the desired shape:

- `DatasheetProfile` is the reviewed datasheet-fact schema.
- `draft-datasheet-profile` writes `review_status="needs_review"` drafts from
  a project validation index and optional reviewed document index.
- `suggest_profile_candidates()` loads only `review_status="ready"` profiles,
  so generated drafts are ignored by automatic project validation.
- `validate_component_against_profile()` dispatches deep checks only by
  `profile.recommended["topology_family"]`, not by MPN.

The archetype workflow should extend the draft path, not the validator path.
The first implementation should add a small typed archetype registry and an
optional CLI flag:

```text
draft-datasheet-profile INDEX.json \
  --identity 74LV165PW \
  --document-index docs.csv \
  --archetype 74x165_piso_16pin \
  --output drafts/74lv165pw.json
```

The generated file remains a normal `DatasheetProfile` with
`review_status="needs_review"`. The archetype fills reusable family shape:
aliases, `recommended.topology_family`, pin-role placeholders, and evidence
placeholders that explicitly say reviewer confirmation is still required.

## Data Flow

1. `design-validator-ui --index-json` creates grouped project coverage.
2. `draft-datasheet-profile` selects one component group by identity.
3. If `--archetype` is supplied, the draft generator merges archetype facts into
   the `needs_review` draft.
4. `suggest-validation-targets` and `design-validator-ui` continue to ignore the
   draft because it is not `ready`.
5. A human reviews the public datasheet, local symbol pin mapping, polarity,
   limits, aliases, and evidence tokens before changing the profile to `ready`.

## First Archetype

Use `74x165_piso_16pin` first.

Reasons:

- It matches the real Allegro coverage story and the `74LV165` family validator.
- It demonstrates topology checks: load/clock fanout and Q7-to-DS cascade.
- It is more interview-useful than another voltage-only power profile.

Follow-up archetypes can cover `common_sot23_nmos` and
`i2c_level_shift_repeater_like`, but they should not block the first slice.

## Safety Contracts

- Generated profiles must always set `review_status="needs_review"`.
- Generated profiles must not appear as `matched` profile candidates until a
  reviewer promotes them to `ready`.
- Archetypes may propose pin roles and topology metadata, but evidence tokens
  must remain placeholders until public datasheet evidence is checked.
- No validator dispatch changes are needed for existing families. If a new
  family is ever needed, it must still dispatch by `topology_family`.
- Do not use private datasheets, internal BOM systems, supplier live data, PLM,
  price, lifecycle, PCB layout, or boardview data.

## Trade-offs

Start with an in-code typed registry instead of external YAML. It is smaller,
easier to test, and keeps the first slice deterministic. External archetype
files can be added later if users need to maintain their own templates.

The archetype should generate useful placeholders, not ready profiles. That
keeps the story honest: Hardwise scales profile creation work, but does not
pretend a template is equivalent to a reviewed datasheet.

## Rollback

The change should be isolated to profile draft generation, CLI option parsing,
tests, and docs. If it misbehaves, remove the archetype module and CLI option;
ready profile validation and family validators should continue unchanged.
