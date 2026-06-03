# C closeout implementation plan

## Checklist

1. Confirm repository state.
   - `git status --short --branch`
   - `python3 ./.trellis/scripts/task.py list`
2. Patch task artifacts.
   - Add the completed parent PRD summary.
   - Mark document-provider and D1 acceptance criteria complete.
   - Record commit `9e0df0d` on completed child task metadata where useful.
3. Record D2 planning split in `docs/rolling_log.md`.
4. Add a learning-log note for task-state closeout after combined commits.
5. Start this closeout task, then archive completed tasks with `--no-commit`:
   - `06-03-document-discovery-provider`
   - `06-03-mainboard-profile-gap-analysis`
   - `06-03-workbench-ai-topology-tools`
   - `06-03-allegro-ai-topology-document-discovery`
   - `06-03-c-closeout-after-topology-document-d1`
6. Verify:
   - `python3 ./.trellis/scripts/task.py list`
   - `git diff --check`
7. Commit the closeout as one local Conventional Commit.

## Stop-And-Ask Conditions

- Any archive command tries to auto-commit despite `--no-commit`.
- A required task directory is missing or already archived.
- The closeout would require source-code changes or a new validator/profile.
- D2 planning needs a product decision beyond the four-way split already
  agreed in conversation.
