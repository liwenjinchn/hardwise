# Design: validator family migration batch 1

## Scope Boundary

This task imports two low-coupling validators from `origin/try/trellis`:

- `diode` using the SS34 profile and fixtures.
- `connector` using the 2x5 connector profile and fixtures.

The design deliberately avoids the higher-risk validators whose checks depend on analog topology interpretation, class-based state, or known electrical caveats.

## Dispatch Contract

Existing codex families still contain MPN fallback branches. New migrated families should not add more fallback branches. Dispatch shape for this task:

```python
if family == "diode":
    from hardwise.validation.diode import validate_diode
    return validate_diode(component, profile, design)
if family == "connector":
    from hardwise.validation.connector import validate_connector
    return validate_connector(component, profile, design)
```

This establishes the intended future shape without broad cleanup of existing branches.

## Validator Signature

Migrated validators use the same public entrypoint style as `i2c_mux.py`:

```python
def validate_x(component: Component, profile: DatasheetProfile, design: Design) -> list[ComponentValidation]:
    ...
```

No class wrapper is needed for this first batch.

## Shared Helpers

`pins.py` owns pin-level heuristics. This task makes ground detection public as `is_ground_net(net_name)`. Existing private use becomes a wrapper or direct call, and `mcu.py` imports the shared helper instead of maintaining its own hard-coded set.

The connector validator uses `is_ground_net()` for ground classification and `voltage_for_net()` for VCC voltage checks.

## Data Flow

Profile JSON supplies `recommended.topology_family`. `validate_component_against_profile()` first runs pin-level validation for every profiled pin, then dispatches component-level topology checks by family.

Tests load Allegro netlist + BOM fixtures, build a `Design`, apply BOM matching, load the datasheet profile, and assert both pin-level and component-level results.

## Compatibility

- Existing tests may see no status change because migrated profiles add new families rather than changing existing profiles.
- `mcu.py` refactor must preserve existing BOOT0 and ground behavior, except it should gain support for the broader shared ground token handling.
- Profiles copied from try/trellis are public-demo synthetic profiles and remain acceptable for MVP fixtures.

## Rollback

- If migrated tests fail due to profile/fixture shape, revert the specific family module and profile first.
- If existing tests fail due to `is_ground_net()` exposure, revert the MCU helper refactor while keeping new connector use local.
- Do not remove the migration branch or rewrite prior commits.
