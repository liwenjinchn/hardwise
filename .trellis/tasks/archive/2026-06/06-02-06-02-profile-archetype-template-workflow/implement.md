# Profile archetype template workflow implementation

## Checklist

- [x] Load `trellis-before-dev` before editing product code.
- [x] Add a typed archetype registry, likely under `src/hardwise/ir/`.
- [x] Implement `74x165_piso_16pin` as the first archetype.
- [x] Extend `draft_profile_from_project_index()` with an optional archetype id.
- [x] Add `--archetype` to `draft-datasheet-profile`.
- [x] Ensure generated archetype drafts always keep
      `review_status="needs_review"`.
- [x] Add tests that prove:
      - the archetype draft contains topology family, pin placeholders, aliases,
        and evidence placeholders;
      - the generated draft is ignored by automatic profile candidate matching;
      - existing ready profiles still validate through family validators, not
        MPN-specific dispatch.
- [x] Update docs/interview wording only after the code behavior is verified.
- [x] Run `uv run pytest -q`.
- [x] Run `uv run ruff check .`.

## Verification Commands

```bash
uv run pytest tests/test_cli_validator_ui.py tests/validation/test_profile_candidates.py -q
uv run pytest -q
uv run ruff check .
```

## Stop-and-Ask Conditions

- The implementation would need to auto-promote generated profiles to `ready`.
- The implementation would require private/internal datasheets or supplier/PLM
  data.
- The implementation would add `profile.part_number` branches to
  `validation/component.py`.
- The first archetype cannot produce a valid `DatasheetProfile` without
  pretending unreviewed pinout/limit facts are source-backed.

## Commit Boundary

Keep this as one profile-archetype commit if possible. Do not bundle Windows CI
or interview-materials edits into the same commit unless a tiny doc line is
needed to explain the new command.
