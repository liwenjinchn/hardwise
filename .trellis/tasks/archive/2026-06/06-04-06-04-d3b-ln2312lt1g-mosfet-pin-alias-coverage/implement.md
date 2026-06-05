# D3b LN2312LT1G MOSFET pin-alias coverage implementation

## Execution

1. Selected `LN2312LT1G` because D3a/D2d already identified it as a real
   mainboard transistor gap with a ready profile and an existing MOSFET
   validator; the blocker was local schematic pin IDs `D/G/S`.
2. Added explicit `PinProfile.schematic_pin_aliases` and a shared
   `validation/pin_resolver.py` helper so candidate matching, pin-level
   validation, MOSFET checks, and UI pin consistency use the same resolution
   rule.
3. Updated `data/datasheet_profiles/ln2312lt1g.json` with aliases
   `Gate -> G`, `Source -> S`, `Drain -> D`; datasheet package pin numbers
   and source tokens remain unchanged.
4. Added a focused Allegro fixture:
   `tests/fixtures/allegro/ln2312lt1g_symbol_alias.*`.
5. Added tests for profile facts, alias-based validation, candidate matching,
   UI smoke, and profile-contract store round-trip.

## Surprise / Fix

The stricter value-text candidate test exposed that normalized substring
matching could read `MOS LN2312LT1G` as alias `S-LN2312LT1G` across a token
boundary. The matcher now requires non-alphanumeric boundaries while still
allowing punctuation inside part numbers such as `SD103AWS-7-F`.

## Verification

```bash
uv sync --extra dev
uv run pytest tests/validation/test_mosfet.py tests/validation/test_profile_candidates.py tests/store/test_profile_contracts.py tests/test_cli_validator_ui.py::test_report_validator_ui_batch_writes_ln2312lt1g_alias_manifest -q
```

Result:

```text
33 passed
```

Additional verification:

```bash
uv run hardwise report-validator-ui-batch tests/fixtures/allegro/ln2312lt1g_symbol_alias.net tests/fixtures/allegro/ln2312lt1g_symbol_alias_bom.csv --targets-manifest tests/fixtures/allegro/ln2312lt1g_symbol_alias_targets.yaml --output /tmp/hardwise-ln2312lt1g-alias.html
uv run pytest tests/test_cli_validator_ui.py::test_design_validator_ui_matches_mpq8626_power_family_with_public_docs tests/test_cli_validator_ui.py::test_design_validator_ui_uses_document_mpn_for_l2n7002klt1g_profile tests/test_cli_validator_ui.py::test_report_validator_ui_batch_writes_ln2312lt1g_alias_manifest -q
uv run pytest -q
uv run ruff check .
```

Result:

```text
validator-ui-batch: /tmp/hardwise-ln2312lt1g-alias.html (1 components, validated=Q9, PASS/WARN/ERROR=1/0/0)
3 passed
520 passed, 7 deselected
All checks passed!
```

## Scope Check

- No D3a MPQ8626 profile, document cache, Datasheets.com, HTML/PDF ingest, or
  evidence-to-contract files were changed.
- No new validation family or large dependency was introduced.
