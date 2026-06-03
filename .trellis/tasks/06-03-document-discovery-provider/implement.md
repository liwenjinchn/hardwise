# Document discovery provider - Implementation Plan

## Checklist

1. Inspect current document coverage contracts.
   - `src/hardwise/documents/{types,index,matcher}.py`
   - `src/hardwise/validation/component_groups.py`
   - `src/hardwise/validation/project_index.py`
   - `src/hardwise/workbench/{context,chat}.py`
2. Add provider models and deterministic helpers.
   - Component document lookup by refdes.
   - Project document coverage summary by grouped BOM identity.
   - Bounded candidate rendering for ambiguous matches.
   - `not_configured` and `not_found` branches.
3. Add agent tool schemas.
   - `get_component_documents(refdes)`
   - `summarize_document_coverage(limit=...)`
4. Wire Runner dispatch.
   - Pass document coverage context into `Runner`.
   - Keep no-document-index runs fail-closed with structured
     `not_configured`.
5. Wire workbench context.
   - Pass `context.document_report` and `context.index` into the chat Runner.
   - Add `--document-index` to `serve-workbench`.
6. Update prompt and fake mode.
   - Prompt: document coverage questions use document tools.
   - Fake routing: component document questions and gap-summary questions call
     the new tools.
   - Fake summaries clearly separate document coverage from electrical facts.
7. Add tests.
   - Unit tests for configured component document lookup.
   - Unit tests for missing/ambiguous/manual and not-configured outputs.
   - Unit tests for unknown refdes closest matches.
   - Runner-backed fake workbench chat test using a small public-safe fixture
     document index.
   - CLI dry-run or focused command test for `serve-workbench --document-index`.
8. Run focused verification.
9. Run full quality gate.
10. Update `docs/learning_log.md` only if implementation uncovers a bug or
    framework/input quirk worth preserving.
11. Update `docs/interview_qa.md` only after measured implementation facts are
    available.

## Likely Files

- `src/hardwise/agent/tools.py`
- `src/hardwise/agent/runner.py`
- `src/hardwise/agent/prompts.py`
- `src/hardwise/workbench/chat.py`
- `src/hardwise/workbench/context.py`
- `src/hardwise/cli.py`
- `tests/documents/test_matcher.py` or a new focused provider test
- `tests/workbench/test_chat.py`
- `tests/test_cli_validator_ui.py` or CLI workbench dry-run tests

## Verification

Focused tests:

```bash
uv run pytest tests/documents tests/workbench/test_chat.py -q
uv run pytest tests/test_cli_validator_ui.py -q
```

Provider smoke with public-safe fixture:

```bash
uv run hardwise serve-workbench \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --document-index tests/fixtures/allegro/document_match/docs.csv \
  --fake-ai --dry-run
```

Full gate:

```bash
uv run pytest -q
uv run ruff check .
```

## Stop-And-Ask Conditions

- The provider would need live internet search or supplier/PLM lookup.
- The only available document source is non-public hardware data.
- A requested answer needs datasheet specification extraction rather than
  document coverage status.
- The implementation would convert document coverage into PASS/WARN/ERROR.
- The task starts depending on topology-tool implementation in a way that
  cannot be expressed as optional context.

## Review Gate Before Start

Recommended option B is ready for review:

- local document-index provider;
- no live discovery;
- fail-closed without `--document-index`;
- workbench AI tool integration;
- fake-mode coverage for offline demo and tests.

After review, start this child task with `task.py start` and implement only the
provider slice. Keep topology tools and mainboard gap analysis as independent
child tasks.
