# C closeout after topology/document/D1

## Goal

Close the completed topology tools, document provider, and D1 mainboard
profile-gap work into a clean C-stage handoff: Trellis task state should match
the committed code, measured deliverables should be easy to audit, and the next
D2 slices should be explicit without starting new validation work.

## Requirements

1. Record that the combined implementation landed in commit
   `9e0df0d feat(workbench): expose document and topology context`.
2. Mark the three completed child deliverables as complete in their task
   artifacts:
   - `06-03-workbench-ai-topology-tools`
   - `06-03-document-discovery-provider`
   - `06-03-mainboard-profile-gap-analysis`
3. Replace the placeholder parent PRD for
   `06-03-allegro-ai-topology-document-discovery` with a concise completed
   integration summary and acceptance checklist.
4. Archive the completed child tasks, parent task, and this closeout task so
   `task.py list` no longer shows stale in-progress work.
5. Add a durable note describing the D2 split:
   - D2a: select a top `try_existing_validator_profile` family from the D1
     next-family advisory.
   - D2b: backfill public document-index rows for that selected family.
   - D2c: implement one reviewed profile/validator slice only after public
     evidence supports it.
   - D2d: rerun the mainboard smoke to prove manual coverage moved without
     changing unrelated validation truth.
6. Preserve scope boundaries: no new validator, no new ready profile, no live
   supplier/web lookup, no PLM/layout claims, and no new PASS/WARN/ERROR rows.

## Acceptance Criteria

- [x] Completed child tasks and the parent task have non-placeholder PRD
      acceptance state.
- [x] Stale task statuses are cleared by archiving completed tasks with
      `--no-commit`, leaving one explicit closeout commit for review.
- [x] D2 split is recorded in project planning notes without implying that D2
      has started.
- [x] The C closeout records the process lesson that a combined implementation
      commit can still require a separate task-state closeout.
- [x] `git diff --check` passes.
- [x] `python3 ./.trellis/scripts/task.py list` shows no active tasks after
      archive.

## Notes

- This is metadata/documentation cleanup over already verified work. It should
  not modify business logic or test fixtures.
