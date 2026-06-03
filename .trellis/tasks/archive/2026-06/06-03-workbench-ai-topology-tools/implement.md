# Workbench AI topology tools - Implementation Plan

## Checklist

- [x] Inspect existing workbench chat, Runner dispatch, and project-index tests.
- [x] Add Pydantic input/output models for topology tools in `agent/tools.py`.
- [x] Implement deterministic helpers for:
  - [x] component context lookup
  - [x] net context lookup
  - [x] net search
  - [x] project topology summary without module naming/grouping
- [x] Extend `TOOL_DEFINITIONS` with the new tools.
- [x] Extend `Runner` with optional `project_index` and dispatch branches.
- [x] Pass `context.index` from `WorkbenchChatService` into `Runner`.
- [x] Update `WORKBENCH_SYSTEM_PROMPT` for topology and project overview
      questions.
- [x] Extend fake workbench model routing and answer summarization for topology
      payloads.
- [x] Update snapshot suggestions if needed without removing existing evidence
      smoke coverage.
- [x] Add unit tests for each tool.
- [x] Add Runner/workbench fake chat tests for at least one topology question.
- [x] Run focused tests.
- [x] Run full quality gate.

## Result

Implemented four Allegro/PST topology tools for the existing right-bottom
Workbench AI panel:

- `get_component_context`
- `get_net_context`
- `search_nets`
- `summarize_project_topology`

The tools expose parsed `Design` component/pin/net facts and optional
`ProjectValidationIndex` coverage state. They deliberately do not infer visual
schematic module boundaries, KiCad wires/labels, layout, PLM, lifecycle, price,
or datasheet web-search facts.

Fake/snapshot workbench mode now routes topology-looking questions through the
real Runner and real tool dispatch. Tested examples include `U8 接了哪些关键网络?`,
`RESET 相关网络有哪些?`, and `这张板大概有哪些已验证风险和待补 profile?`.

## Completed Verification

```bash
uv run pytest tests/agent/test_tools.py tests/workbench/test_chat.py \
  tests/agent/test_validation_bridge.py \
  tests/test_cli_validator_ui.py::test_design_validator_ui_ai_snapshot_embeds_copilot_panel -q
uv run ruff check .
uv run pytest -q
```

Result:

```text
30 passed in focused tests
All checks passed!
474 passed, 7 deselected
```

## Likely Files

- `src/hardwise/agent/tools.py`
- `src/hardwise/agent/runner.py`
- `src/hardwise/agent/prompts.py`
- `src/hardwise/workbench/chat.py`
- `tests/agent/test_tools.py`
- `tests/workbench/test_chat.py`
- possibly `tests/agent/test_validation_bridge.py` if tool-count assertions need
  updating

## Verification

Focused:

```bash
uv run pytest tests/agent/test_tools.py tests/workbench/test_chat.py -q
uv run pytest tests/agent/test_validation_bridge.py -q
uv run pytest tests/test_cli_validator_ui.py::test_design_validator_ui_ai_snapshot_embeds_copilot_panel -q
```

Full gate:

```bash
uv run pytest -q
uv run ruff check .
```

Manual smoke after implementation:

```bash
uv run hardwise serve-workbench \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --fake-ai --dry-run
```

If a live server is started for browser QA, use the in-app browser against the
reported localhost URL and ask one component-context question plus one net
search question.

## Stop-And-Ask Conditions

- A topology question requires visual schematic page/layout interpretation
  rather than netlist topology.
- The implementation would need to read non-public board files.
- The new tool surface starts overlapping with datasheet web search or PLM
  document discovery.
- The model needs module names that cannot be derived from deterministic
  netlist/BOM/profile facts.
- Implementation starts adding module-group labels instead of conservative net
  buckets.

## Notes For Parallel Work

This child task is independent from:

- `06-03-document-discovery-provider`
- `06-03-mainboard-profile-gap-analysis`

It should not depend on document discovery or new family validators.
