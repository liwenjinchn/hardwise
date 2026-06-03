# Mainboard profile gap analysis implementation plan

## D1 Checklist

1. Confirm the acceptance input.
   - Use the user-provided public Allegro folder:
     `/Users/liwenjin/Library/Containers/com.comisys.lanxin.hgo/Data/Library/Application Support/lanxin_macgoh/custom/files/lanxindownload/04_设计文件与EDA/allegro`.
   - Topology smoke already succeeds: 8180 components, 6918 nets, 24563
     properties.
2. Add narrow BOM intake compatibility for `RFMS5H2TABom(13).xlsx`.
   - Teach BOM parsing or a local normalization path to read `.xlsx`.
   - Map Chinese headers to `BomItem` fields.
   - Include `.xlsx` in project-directory BOM candidate discovery if parsing
     is added to `parse_bom`.
   - Add focused parser/auto-selection tests using a small synthetic workbook
     with the same Chinese headers.
3. Verify the public folder can produce a project index:
   - `inspect-bom-match <folder> RFMS5H2TABom(13).xlsx`
   - `design-validator-ui <folder> RFMS5H2TABom(13).xlsx --index-json ...`
4. Inspect the index payload and record baseline metrics:
   - component count;
   - BOM matched count;
   - validated/manual rows;
   - PASS/WARN/ERROR totals;
   - component group count.
5. Reuse existing coverage helpers:
   - profile-gap grouping from `ProjectValidationIndex`;
   - document candidate CSV generation;
   - next-family advisory Markdown.
6. If existing commands cannot produce the D1 Markdown summary cleanly, add a
   narrow report/orchestration command without changing validator truth.
7. Add focused tests only for new orchestration/reporting behavior, if any.
8. Run verification:
   - focused tests for touched modules;
   - `uv run pytest -q`;
   - `uv run ruff check .`.
9. Update `docs/learning_log.md` and `docs/interview_qa.md` only after D1
   ships with measured facts.

## Likely Files If Implementation Is Needed

- `src/hardwise/cli.py`
- `src/hardwise/bom/parser.py`
- `src/hardwise/project_inputs.py`
- `src/hardwise/report/project_validation_markdown.py`
- `src/hardwise/documents/candidates.py`
- `src/hardwise/validation/coverage_priority.py`
- `tests/bom/test_parser.py`
- `tests/test_cli_bom_match.py`
- `tests/test_cli_validator_ui.py`
- `tests/documents/test_candidates.py`
- `tests/validation/test_coverage_priority.py`

## Verification Evidence

Mainboard acceptance commands:

```bash
uv run hardwise inspect-allegro-netlist \
  "/Users/liwenjin/Library/Containers/com.comisys.lanxin.hgo/Data/Library/Application Support/lanxin_macgoh/custom/files/lanxindownload/04_设计文件与EDA/allegro"

uv run hardwise inspect-bom-match \
  "/Users/liwenjin/Library/Containers/com.comisys.lanxin.hgo/Data/Library/Application Support/lanxin_macgoh/custom/files/lanxindownload/04_设计文件与EDA/allegro" \
  "/Users/liwenjin/Library/Containers/com.comisys.lanxin.hgo/Data/Library/Application Support/lanxin_macgoh/custom/files/lanxindownload/04_设计文件与EDA/allegro/RFMS5H2TABom(13).xlsx"

uv run hardwise design-validator-ui \
  "/Users/liwenjin/Library/Containers/com.comisys.lanxin.hgo/Data/Library/Application Support/lanxin_macgoh/custom/files/lanxindownload/04_设计文件与EDA/allegro" \
  "/Users/liwenjin/Library/Containers/com.comisys.lanxin.hgo/Data/Library/Application Support/lanxin_macgoh/custom/files/lanxindownload/04_设计文件与EDA/allegro/RFMS5H2TABom(13).xlsx" \
  --output /tmp/hardwise-mainboard-d1-workbench.html \
  --index-output /tmp/hardwise-mainboard-d1-index.md \
  --index-json /tmp/hardwise-mainboard-d1-index.json

uv run hardwise build-document-index-candidates \
  /tmp/hardwise-mainboard-d1-index.json \
  --output /tmp/hardwise-mainboard-d1-document-candidates.csv

uv run hardwise recommend-next-family \
  /tmp/hardwise-mainboard-d1-index.json \
  --output /tmp/hardwise-mainboard-d1-next-family.md
```

Final code gate if implementation happens:

```bash
uv run pytest -q
uv run ruff check .
```

## Review Gate Before Start

Before `task.py start`, confirm the BOM identity policy:

- Recommended: treat `编号` as source item number, not MPN; use `名称` as
  conservative display/grouping text.
- Alternative: treat `编号` as part identity for grouping, faster but risks
  ranking/searching by an internal code rather than a public device identity.
