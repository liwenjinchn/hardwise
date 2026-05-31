# Implementation Plan

## Checklist

1. Tighten `DatasheetProfile.review_status` to
   `Literal["ready", "needs_review"]`; add explicit `"review_status": "ready"`
   to bundled ready profiles.
2. Add `src/hardwise/validation/coverage_priority.py` with:
   - `FAMILY_SAFETY_WEIGHT`
   - `DETERMINISTIC_VALIDATOR_FAMILIES`
   - advisory family-to-validator map
   - `score_candidate`
   - `FamilyCoverageRecommendation`
   - `FamilyCoverageReport`
   - `CoveragePriorityError`
   - `build_family_coverage_report`
   - `render_family_coverage_markdown`
3. Add `tests/validation/test_coverage_priority.py`.
4. Wire scoring into `src/hardwise/documents/candidates.py`:
   - add `priority_score` and `priority_band`
   - append `Priority` CSV column
   - sort profile gaps before matched-profile backfill rows
5. Extend `tests/documents/test_candidates.py`.
6. Add `recommend-next-family` to `src/hardwise/cli.py` using lazy submodule
   import.
7. Add large public Allegro fixture:
   - `tests/fixtures/allegro/motor_sensor_controller.net`
   - `tests/fixtures/allegro/motor_sensor_controller_bom.csv`
8. Extend CLI tests in `tests/test_cli_validator_ui.py`.
9. Update `docs/interview_qa.md` with the shipped C3 coverage-analytics fact.
10. Run verification.

## Verification

Targeted:

```bash
uv run pytest -q tests/documents/test_candidates.py tests/validation/test_coverage_priority.py tests/validation/test_profile_candidates.py tests/ir/test_profile.py tests/test_cli_validator_ui.py
```

Full gate:

```bash
uv run pytest -q
uv run ruff check .
```

Demo smoke:

```bash
uv run hardwise design-validator-ui tests/fixtures/allegro/motor_sensor_controller.net \
  tests/fixtures/allegro/motor_sensor_controller_bom.csv \
  --document-index data/document_indexes/family_v1_3_docs.csv \
  --index-json /tmp/large-index.json -o /tmp/large.html
uv run hardwise recommend-next-family /tmp/large-index.json -o /tmp/next-family.md
```

## Stop Conditions

- `review_status` has a third real value.
- The feature would change validator dispatch or PASS-WARN-ERROR counts.
- Ranking would need datasheet facts, supplier data, or MPN-keyed control flow.
- A net-consistent large fixture exceeds the time box; downscope to a smaller
  public fixture and document the downscope.

