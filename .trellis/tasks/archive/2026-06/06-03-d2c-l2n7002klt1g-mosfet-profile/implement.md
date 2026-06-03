# D2c Implementation Plan

## Checklist

1. Add `data/datasheet_profiles/l2n7002klt1g.json`.
   - Keep it source-backed and `review_status = "ready"`.
   - Use public MPN/order aliases only.
   - Do not include Chinese BOM value text as an alias.
2. Add focused tests.
   - `tests/validation/test_mosfet.py`: profile pinout and abs-max facts.
   - `tests/validation/test_mosfet.py`: low-side synthetic validation reuses
     existing MOSFET rules for `L2N7002KLT1G`.
   - `tests/validation/test_profile_candidates.py`: BOM MPN
     `L2N7002KLT1G` matches `data/datasheet_profiles/l2n7002klt1g.json`.
3. Run focused tests and ruff on touched files.
4. Run real mainboard smoke:

```bash
uv run hardwise design-validator-ui \
  "/Users/liwenjin/Library/Containers/com.comisys.lanxin.hgo/Data/Library/Application Support/lanxin_macgoh/custom/files/lanxindownload/04_设计文件与EDA/allegro" \
  --document-index data/document_indexes/mainboard_d2_transistor_docs.csv \
  --output /tmp/hardwise-mainboard-d2c-workbench.html \
  --index-output /tmp/hardwise-mainboard-d2c-index.md \
  --index-json /tmp/hardwise-mainboard-d2c-index.json
```

5. Inspect `/tmp/hardwise-mainboard-d2c-index.json`.
   - `L2N7002KLT1G` group should be `profile_status = "matched"` with
     `profile_path = "data/datasheet_profiles/l2n7002klt1g.json"`.
   - `LN2312LT1G` and `PE537BA` should not be newly promoted by D2c.
   - `document_source` for the selected group should remain
     `doc:mainboard_d2_transistor_docs.csv#line2`.
6. Run full gate:

```bash
uv run pytest -q
uv run ruff check .
git diff --check
```

7. Update durable notes.
   - `docs/learning_log.md`: measured mainboard D2c movement and any surprise.
   - `docs/interview_qa.md`: add a measured D2c fact if the smoke succeeds.
   - `.trellis/spec/backend/validation-guidelines.md`: update only if D2c
     exposes a reusable profile/validator rule not already documented.
8. Commit with a focused conventional commit after the quality gate passes.

## Stop And Ask

- The public LRC PDF facts conflict with the expected pin mapping.
- Mainboard sampling shows selected refdes use non-package pin IDs.
- The only way to match the group is to add Chinese BOM value text to the
  profile aliases.
- Existing MOSFET validator semantics need to change.

## Focused Verification Commands

```bash
uv run pytest tests/validation/test_mosfet.py tests/validation/test_profile_candidates.py -q
uv run ruff check data/datasheet_profiles tests/validation/test_mosfet.py tests/validation/test_profile_candidates.py
```

## Execution Notes

Implemented:

- Added `data/datasheet_profiles/l2n7002klt1g.json`.
- Added focused MOSFET profile/validation tests for public pinout, Vds/Vgs
  limits, and family-based dispatch.
- Added profile-candidate coverage for direct public MPN matching.
- Added a reviewed-document-MPN bridge for `design-validator-ui`: when a BOM
  item has no direct ready profile match, a matched document-index row may
  supply its reviewed public MPN for profile lookup, but only if the local
  schematic symbol exposes the profile pin numbers.
- Added synthetic workbench smoke coverage proving `L2N7002KLT1G` promotes via
  the D2b document row while `LN2312LT1G` (`D/G/S` local pins) and `PE537BA`
  remain outside D2c.

Verification:

```text
uv run pytest tests/test_cli_validator_ui.py::test_design_validator_ui_uses_document_mpn_for_l2n7002klt1g_profile \
  tests/validation/test_profile_candidates.py tests/validation/test_mosfet.py -q
22 passed

uv run pytest -q
491 passed, 7 deselected
uv run ruff check .
All checks passed!
git diff --check
clean
```

Target mainboard smoke:

```text
uv run hardwise design-validator-ui \
  "/Users/liwenjin/Library/Containers/com.comisys.lanxin.hgo/Data/Library/Application Support/lanxin_macgoh/custom/files/lanxindownload/allegro" \
  --document-index data/document_indexes/mainboard_d2_transistor_docs.csv \
  --output /tmp/hardwise-mainboard-d2c-workbench.html \
  --index-output /tmp/hardwise-mainboard-d2c-index.md \
  --index-json /tmp/hardwise-mainboard-d2c-index.json

document-index: matched=3, no_result=189, ambiguous=0, manual_needed=0
8180 components, validated=6679, BOM matched=7248
PASS/WARN/ERROR=3868/2811/0, manual=1501
```

Measured movement vs D2b baseline:

- Validated rows moved `6573 -> 6679` (+106).
- Manual rows moved `1607 -> 1501` (-106).
- `L2N7002KLT1G` group: 106 refdes, `profile_status=matched`,
  `validation_status=WARN`, `document_source=doc:mainboard_d2_transistor_docs.csv#line2`,
  `profile_path=data/datasheet_profiles/l2n7002klt1g.json`.
- `LN2312LT1G` group: 26 refdes, `profile_status=no_result`,
  `document_source=doc:mainboard_d2_transistor_docs.csv#line3`.
- `PE537BA` group: 11 refdes, `profile_status=no_result`,
  `document_source=doc:mainboard_d2_transistor_docs.csv#line4`.
