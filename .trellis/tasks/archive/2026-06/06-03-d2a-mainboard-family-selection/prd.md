# D2a mainboard family selection

## Goal

Choose the next mainboard family slice for D2c from the D1 coverage advisory,
and hand D2b a narrow public-document backfill target. D2a is an analysis and
planning deliverable only: it must not add profiles, validators, document-index
rows, or new PASS/WARN/ERROR truth.

## Requirements

1. Use the D1 artifacts as inputs:
   - `/tmp/hardwise-mainboard-d1-next-family.md`
   - `/tmp/hardwise-mainboard-d1-document-candidates.csv`
   - `/tmp/hardwise-mainboard-d1-auto-index.json`
2. Compare only the D1 `try_existing_validator_profile` buckets:
   - `ic`
   - `transistor`
   - `diode`
3. Score each bucket by:
   - uncovered refdes count;
   - number of BOM/device groups;
   - identity clarity from the Chinese BOM value text;
   - existing deterministic validator/profile fit;
   - D2b public-document backfill size;
   - D2c implementation risk.
4. Inspect representative groups and refdes samples from the project index.
5. Produce a reviewer-facing Markdown report with:
   - family comparison table;
   - recommended D2c family;
   - D2b input rows/search queries for the chosen family;
   - risks and stop conditions.
6. Preserve scope boundaries:
   - no new validator/profile;
   - no document-index backfill;
   - no live supplier/PLM/lifecycle/pricing claims;
   - no PCB/layout/boardview conclusions;
   - no new electrical verdicts.

## Acceptance Criteria

- [x] `prd.md` and `implement.md` define D2a as family selection only.
- [x] The report compares `ic`, `transistor`, and `diode` using D1 measured
      facts rather than intuition alone.
- [x] The selected family has a clear D2b document-backfill input list.
- [x] The report explicitly explains why the large `unknown` bucket is deferred.
- [x] The report states what D2c may and may not implement.
- [x] D2b task files created by another parallel line are not modified or
      staged by this task.
- [x] `git diff --check` passes.

## Notes

- D2a can be completed with PRD + implementation checklist + report. It does
  not need a technical design because it does not change code contracts.
