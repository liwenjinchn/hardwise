# D2b Implementation Plan

## Checklist

1. Update candidate generation
   - Add `value` to `DocumentCandidateRow`.
   - Add `Value` to candidate CSV output.
   - Map `mpn` vs `part_like_value` identities without promoting source item
     numbers.
   - Add optional family filtering to `build_document_candidate_report()`.

2. Update CLI
   - Add repeatable `--family` to `build-document-index-candidates`.
   - Preserve current no-filter behavior.
   - Include filter evidence in the command output if useful.

3. Add focused tests
   - Candidate CSV emits `Value` for `identity_kind=part_like_value`.
   - Candidate CSV emits `MPN` for `identity_kind=mpn`.
   - `--family transistor` filters a mixed project index.
   - Reviewed candidate CSV with `MPN` plus exact `Value` matches a BOM row
     whose public part number was not parsed from the BOM.
   - A reviewed index row can match the same identity in a second synthetic
     BOM/project without relying on refdes or source item number.

4. Add D2b reviewed index data
   - Create a focused local CSV under `data/document_indexes/` for the
     D2a-selected transistor family.
   - Include rows for `L2N7002KLT1G`, `LN2312LT1G`, and `PE537BA`.
   - Keep titles/descriptions as document coverage statements, not electrical
     conclusions.

5. Smoke the real mainboard path
   - Regenerate a family-scoped candidate CSV from the D1 index JSON.
   - Run workbench/index generation with the D2b document index.
   - Confirm the intended transistor groups have `document_status=matched` and
     selected document title/URL/source token.

6. Finish
   - Run focused tests.
   - Run `uv run ruff check .`.
   - Run broader pytest if time allows.
   - Update `docs/learning_log.md` and `docs/interview_qa.md` with measured
     D2b facts if implementation teaches a reusable lesson.
   - Commit only D2b-related files.

## Validation Commands

```bash
uv run pytest tests/documents/test_candidates.py tests/documents/test_matcher.py -q
uv run pytest -q
uv run ruff check .
git diff --check
```

Mainboard smoke commands will use the same public D1 project inputs/artifacts as
D2a and should write outputs under `/tmp/hardwise-mainboard-d2b-*`.

## Rollback Points

- If family filtering causes broad candidate output to change with no filter,
  revert the filter plumbing before proceeding.
- If matching D2a rows requires treating `编号` as MPN, stop and return to
  planning.
- If public document evidence for any transistor row cannot be reviewed
  cleanly, keep that row unmatched and record the gap instead of forcing a match.
