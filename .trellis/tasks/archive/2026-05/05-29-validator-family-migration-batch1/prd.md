# Migrate first validator families

## Goal

Absorb the first low-risk validator batch from `origin/try/trellis` into `codex/migrate-codex-mainline` while tightening the validator dispatch contract: migrated validators route by `topology_family`, use the common `(component, profile, design)` function signature, and reuse shared pin helpers for voltage and ground-net logic.

## User Value

- Preserve useful try/trellis device coverage without regressing codex's project-level coverage direction.
- Prove the migration pattern on low-coupling validators before absorbing analog, driver, or MOSFET checks.
- Reduce duplicated ground-net logic before it spreads into more validator modules.

## Confirmed Facts

- The current branch is `codex/migrate-codex-mainline` and tracks `origin/codex/migrate-codex-mainline`.
- `origin/try/trellis` contains diode and connector validators, profiles, fixtures, and tests.
- Current codex `component.py` still has legacy MPN fallback for existing families, but `i2c_mux` is pure family routing.
- Current `pins.py` already exposes `voltage_for_net`; it has a private `_is_ground_net` helper.
- Current `mcu.py` duplicates ground-net detection locally.
- Try/trellis diode and connector validators use class wrappers; migration should use the pure function entrypoint style from `i2c_mux.py`.

## Requirements

- Migrate only `diode` and `connector` family validators in this task.
- Add `data/datasheet_profiles/ss34.json` and `data/datasheet_profiles/connector_2x5.json`.
- Add Allegro fixtures and tests for both families.
- Add family-only dispatch branches for `diode` and `connector`; do not add `part_number.upper() == ...` fallback for new families.
- Expose a shared `is_ground_net()` helper in `pins.py` and use it from migrated connector logic and existing MCU logic.
- Keep existing codex product features and project-level coverage behavior intact.
- Do not migrate current_sense, op_amp, timer, optocoupler, or MOSFET in this task.
- Do not push after implementation unless explicitly authorized again.

## Acceptance Criteria

- [x] `validate_diode(component, profile, design)` and `validate_connector(component, profile, design)` exist as pure function entrypoints.
- [x] `component.py` dispatches `diode` and `connector` by `topology_family` only.
- [x] Connector ground checks call shared `is_ground_net()`; MCU no longer owns a duplicate ground helper.
- [x] New profiles, fixtures, and tests are present for SS34 diode and 2x5 connector.
- [x] Existing validation tests still pass.
- [x] `uv run pytest -q` and `uv run ruff check .` pass.
- [ ] Work is committed locally with a conventional commit.

## Result

- Added diode and connector validators with pure function entrypoints.
- Added SS34 and connector_2x5 profiles, Allegro fixtures, and tests.
- Exposed `is_ground_net()` in `pins.py`, reused it from connector and MCU, and aligned `voltage_for_net()` with the spec by returning `0.0` for recognized ground nets.
- Targeted tests: `34 passed`.
- Full suite: `367 passed, 7 deselected`.
- Ruff: clean.

## Out of Scope

- Full dispatcher cleanup for existing buck/gate_driver/mcu MPN fallbacks.
- Migrating MOSFET or fixing Vgs logic.
- Migrating op-amp/current-sense/timer/optocoupler validators.
- Updating project reports or UI beyond what tests require.
