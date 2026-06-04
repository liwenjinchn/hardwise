# Dia-like static workbench UI implementation notes

## Implemented

- Changed the shared multi/project validator workbench shell from three columns
  to a two-column Dia-like layout:
  - `left-stack` combines the device/group list and validation summary;
  - the right detail area owns the selected report.
- Added static detail tabs per validated component:
  - `报告` contains pin summary, basic/model checks, connectivity table,
    pin-consistency, compliance checks, evidence, and final summary.
  - `原理图连接` contains netlist topology plus scope boundaries.
- Kept tab switching in `MULTI_UI_SCRIPT`; the script only toggles DOM classes
  and `aria-selected`, and does not compute validation verdicts.
- Updated grouped project rows so a group containing a validated refdes can
  navigate to that refdes detail panel. Groups without a validated refdes still
  use their group id and remain coverage/manual rows.
- Added renderer/CLI assertions for the new left-stack layout, tab payloads,
  and validated group row target.

## Files

- `src/hardwise/report/validator_multi_ui.py`
- `src/hardwise/report/validator_project_ui.py`
- `src/hardwise/report/validator_project_group_ui.py`
- `src/hardwise/report/validator_multi_ui_assets.py`
- `tests/report/test_validator_ui.py`
- `tests/test_cli_validator_ui.py`

## Verification

Focused:

```bash
uv run pytest tests/report/test_validator_ui.py tests/test_cli_validator_ui.py -q
uv run ruff check src/hardwise/report/validator_project_ui.py \
  src/hardwise/report/validator_project_group_ui.py \
  src/hardwise/report/validator_multi_ui.py \
  src/hardwise/report/validator_multi_ui_assets.py \
  tests/report/test_validator_ui.py tests/test_cli_validator_ui.py
```

Result:

```text
38 passed
All checks passed!
```

Browser QA:

```bash
uv run hardwise design-validator-ui \
  tests/fixtures/allegro/mixed_power_stage.net \
  tests/fixtures/allegro/mixed_power_stage_bom.csv \
  --output /tmp/hardwise-dia-like-workbench.html \
  --index-json /tmp/hardwise-dia-like-workbench-index.json
python3 -m http.server 8765 --directory /tmp
```

Observed in the local browser:

```text
title=Hardwise 原理图检验工具 - mixed_power_stage
default active panel=U12
default active tab=报告
left-stack=true
validated group row for U12=true
PASS/WARN/ERROR=4/6/2
click 原理图连接 -> topology panel visible
click U3 row -> active panel U3
```

Full gate:

```bash
uv run pytest -q
uv run ruff check .
git diff --check
```

Result:

```text
523 passed, 7 deselected
All checks passed!
git diff --check passed
```

## Boundaries

- No validation truth changed.
- No `data/datasheet_profiles/*` changed.
- No document-index or candidate-matching behavior changed.
- No AI/Copilot answer becomes part of the static validation truth.
