# Electrical Validator Fix Design

## Scope

This task fixes deterministic validator behavior and wording only. It does not
add new validator families, parse PCB data, or expand Hardwise beyond
pre-layout schematic review.

## Changes

### Buck topology

`validate_buck_topology()` should continue to use the switch output pin as the
starting point, but PASS must require path evidence:

- inductor has one terminal on the switch net and another terminal on a net
  that is consistent with the profiled output/feedback rail when that rail can
  be inferred;
- external freewheel diode has one terminal on the switch net and another
  terminal on a recognized return/clamp rail, normally ground for the current
  nonsynchronous XL1509-style profile;
- unknown or unprovable topology returns WARN instead of PASS.

### Diode family classification

`is_likely_schottky_diode()` is currently too broad for power freewheel use.
Remove `BAS` from the positive Schottky-family prefixes. Leave unknown identities
as WARN so the reviewer can decide from datasheet evidence.

### MOSFET Vds

The generic MOSFET validator does not encode channel type or permitted reverse
stress. Under that scope, large absolute drain-source voltage must not PASS.
Use magnitude against the existing `abs_max.vds` limit, with wording that the
check is a static drain-source stress check rather than a complete operating
mode analysis.

### Gate driver wording

The current EG2132-style topology check can prove Q-prefixed reachability, not
the exact MOSFET gate pin. Keep the conservative reachability behavior, but
change summaries/check wording to avoid claiming "gate load" or "switch node"
unless future structured MOSFET pin profiles prove it.

### Needs-review profiles

Direct validation should surface `review_status="needs_review"` as a validator
result that prevents an all-PASS L1-looking output. The lowest-risk route is to
add a component-level WARN in `validate_component_against_profile()` before
family-specific checks. Candidate generation already excludes draft profiles;
this keeps direct CLI and agent paths honest without breaking report schemas.

## Compatibility

- `ValidationReport` shape remains unchanged.
- Existing report renderers already display component-level WARN rows.
- Existing ready profiles should keep their nominal behavior except where they
  relied on false-positive topology inference.

