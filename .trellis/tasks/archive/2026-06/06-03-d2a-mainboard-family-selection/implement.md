# D2a implementation checklist

1. Read D1 advisory and candidate artifacts.
2. Aggregate D1 project-index groups for `ic`, `transistor`, and `diode`.
3. Inspect local ready profiles and deterministic validators for those buckets.
4. If useful, inspect representative refdes topology only as selection evidence.
5. Write `.trellis/tasks/06-03-d2a-mainboard-family-selection/family-selection.md`.
6. Verify:
   - `python3 ./.trellis/scripts/task.py list`
   - `git diff --check`
   - `git status --short --branch`
7. Archive D2a with `--no-commit` and commit only D2a files plus any D2a
   learning/planning notes.

## Stop-And-Ask Conditions

- The selection would require using non-public hardware data.
- The selected path would need D2b document-index work to be completed first
  before D2a can make any recommendation.
- The recommendation would require new validator semantics rather than reusing
  an existing family validator.
- Another parallel task has modified the same D2a files.
