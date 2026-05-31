# Design

## Boundaries

This is a coverage analytics layer over existing project validation indexes. It
does not produce electrical findings. It reads `ProjectValidationIndex` and
renders CSV/Markdown coverage artifacts only.

## Data Flow

```text
design-validator-ui --index-json
  -> ProjectValidationIndex
  -> coverage_priority.py
  -> candidate CSV priority fields
  -> recommend-next-family Markdown
```

`ProjectValidationIndex` remains the input contract. `coverage_priority.py`
owns priority constants, candidate scoring, family aggregation, models, and
Markdown rendering. CLI commands lazy-import the module inside command bodies.

## Priority Scoring

`score_candidate(suggested_family, refdes_count)` returns `(score, band)`.

Formula:

```text
raw = (1.0 + log2(refdes_count + 1)) * FAMILY_SAFETY_WEIGHT[family] * validator_likelihood(family)
priority_score = round(raw, 1)
```

Candidate CSV sorting:

```text
(profile_gap_first, -priority_score, -refdes_count, mpn)
```

where `profile_gap_first = 0` when `profile_status != "matched"` and `1`
otherwise.

## Recommendation Aggregation

Build `refdes -> suggested_family` and `refdes -> identity` projections from
`index.component_groups`, then iterate `index.rows`. Count only rows whose
`match_status != "matched"`. This avoids over-counting groups whose aggregated
profile status is `mixed`.

Excluded families: `capacitor`, `resistor`, `connector`, `test_point`,
`mechanical`.

`inductor`, `ferrite`, `diode`, `transistor`, `ic`, and `unknown` remain active
coverage families. LEDs are included under `diode`.

## Advisory Actions

The coarse `suggested_family` does not identify exact validator topology.
Actions are advisory only:

- `try_existing_validator_profile`: a mapped validator family might fit; human
  checks `candidate_validator_families` and identity samples.
- `triage_for_new_validator`: no mapped validator family exists; likely needs
  a new deterministic family or manual triage.

No output may imply automatic profile authoring, automatic validation, or an
electrical verdict.

## Import Shape

Do not re-export `coverage_priority` through `validation/__init__.py`. The repo
has a known validation/documents cross-import trap, so CLI commands import
directly from `hardwise.validation.coverage_priority` inside the command body.

## Compatibility

The candidate CSV adds `Priority` as the last column. Existing prefix header
checks and human workflows remain compatible.

