# Profile archetype template workflow

## Goal

Add a reusable profile archetype/template workflow so repeated component
families can generate `needs_review` datasheet profiles without hand-writing
every MPN from scratch.

The outcome should reinforce the current architecture:

> validator family generalizes the rule; source-backed profile carries the
> part-specific facts.

## Requirements

1. Define the profile-archetype concept in code and/or documentation:
   - an archetype supplies stable family shape such as pin roles, topology
     family, and common recommended keys;
   - a generated profile remains `review_status="needs_review"` until a human
     checks public datasheet pinout, polarity, limits, aliases, and evidence.
2. Support at least one high-value archetype from the current real-board
   coverage story. Good candidates:
   - `74x165_piso_16pin` for PISO shift registers;
   - `common_sot23_nmos` for SOT-23 N-channel MOSFETs; or
   - `i2c_level_shift_repeater_like` for PCA9617/PCA9517-like devices.
3. Make the workflow useful for batch candidate generation from BOM/component
   group data, but do not auto-promote generated output to ready validation.
4. Keep deterministic dispatch by `recommended.topology_family`; do not add
   part-number branches to `validation/component.py`.
5. Generated profile facts must be source-auditable before validation:
   unknown pinout, polarity, voltage limits, or package mapping must remain
   reviewer-to-confirm.
6. Do not fetch private/company-internal datasheets or use supplier/PLM data.
   Public datasheets and local public document indexes only.

## Acceptance Criteria

- [ ] A profile archetype/template format is documented and, if implemented,
      covered by tests.
- [ ] At least one archetype can generate a `needs_review` profile skeleton
      with aliases, pin-role placeholders, topology family, and evidence
      placeholders.
- [ ] Generated `needs_review` profiles are ignored by automatic validation
      until promoted to `ready`.
- [ ] The workflow makes clear which fields require public datasheet evidence:
      pin number/name/function, package/pinout, voltage/current limits, polarity
      for diodes/LEDs, and recommended topology metadata.
- [ ] Existing real profiles such as `74lv165`, `ln2312lt1g`, and `pca9617a`
      continue to validate through family validators, not MPN-specific code.
- [ ] `uv run pytest -q` and `uv run ruff check .` pass before completion is
      claimed.

## Notes

- This is the answer to "other same-type devices怎么办": scale profile creation,
  not validator copy-paste.
- Keep the first implementation small. A skeleton generator plus strong safety
  gates is better than a broad but unsafe auto-profile system.
