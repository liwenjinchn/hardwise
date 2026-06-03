# Mainboard profile gap analysis

## Goal

Define D1 for the mainboard profile-gap work: given the public-safe Allegro
mainboard folder from the user, produce an honest grouped profile/document
coverage analysis that tells the reviewer which BOM/device groups still need
public datasheets, reviewed profiles, or deterministic validators.

This is a coverage-planning deliverable, not a new validation family. Its value
is making the remaining manual rows actionable without weakening Hardwise's L1
deterministic / L3 manual trust boundary.

## Confirmed Facts

- This task is a child of
  `06-03-allegro-ai-topology-document-discovery` and shipped in commit
  `9e0df0d feat(workbench): expose document and topology context`.
- Existing code already builds `ProjectValidationIndex` objects with
  `rows`, `component_groups`, and grouped `profile_gap_groups`.
- Existing CLI/reporting paths already include:
  - `design-validator-ui ... --index-json ...` for generating a validation
    index JSON.
  - `build-document-index-candidates <validation-index.json>` for candidate
    datasheet/document-index rows.
  - `recommend-next-family <validation-index.json>` for advisory family
    ranking.
- Existing project rules require public inputs only. No company-internal
  hardware data, even sanitized, may be used.
- The user identified the public mainboard folder as
  `/Users/liwenjin/Library/Containers/com.comisys.lanxin.hgo/Data/Library/Application Support/lanxin_macgoh/custom/files/lanxindownload/04_设计文件与EDA/allegro`.
- The folder contains a Capture/Allegro PST topology set:
  `pstxprt.dat`, `pstxnet.dat`, and `pstchip.dat`.
- `uv run hardwise inspect-allegro-netlist <folder>` succeeds on that folder:
  8180 components, 6918 nets, and 24563 properties. This proves the topology
  side is ready for D1.
- The same folder contains `RFMS5H2TABom(13).xlsx`. The workbook has one sheet
  with Chinese BOM headers including `序号`, `名称`, `编号`, `数量`, and `位号`.
- BOM intake now accepts this file shape:
  - `parse_bom()` reads the `.xlsx` workbook and Chinese header schema.
  - `design-validator-ui <folder>` auto-discovers `.xlsx` BOM candidates in
    project folders.
  - `编号` is preserved as source item number, not public MPN.
- No-profile/manual rows must remain L3/manual coverage artifacts. They must
  not become PASS/WARN/ERROR without structured profile evidence and an
  existing deterministic validation path.
- Generic passive coverage is light deterministic coverage, not datasheet-backed
  deep review.

## Requirements

1. D1 must bind to the user-provided public Allegro folder as the first
   acceptance input.
2. D1 must add or otherwise provide a reproducible BOM intake path for
   `RFMS5H2TABom(13).xlsx` before profile-gap analysis can run.
   - `位号` maps to the reference-designator list.
   - `数量` maps to quantity and may appear as whole-number spreadsheet values.
   - `名称`, `编号`, and `标识` must be mapped conservatively into BOM identity
     fields without fabricating MPNs from description text.
   - Unsupported/blank rows, such as a top-level assembly row with no `位号`,
     must be skipped or represented as structured non-component data rather
     than forced into component matching.
3. After BOM intake, the public folder plus BOM must be convertible into a
   `ProjectValidationIndex` JSON with `design-validator-ui --index-json`.
4. The analysis must summarize board-level coverage:
   - total components;
   - BOM matched count;
   - deterministic validated rows;
   - manual/no-profile rows;
   - PASS/WARN/ERROR totals when validation rows exist.
5. The analysis must group uncovered/manual work by BOM/device identity, not by
   every refdes, so a large mainboard remains scannable.
6. The analysis must separate at least four action buckets:
   - public document missing;
   - document matched but profile missing;
   - ready profile/validator candidate exists or likely exists;
   - manual/ambiguous/unusable identity.
7. The analysis must preserve existing document/profile status language from
   the project index where available: `matched`, `no_result`, `ambiguous`,
   `manual_needed`, `generic_passive`, `no_profile`, or equivalent existing
   statuses.
8. The output must include a ranked next-action view using existing C3/C4 style
   priority logic where possible:
   - profile gaps before document backfill;
   - active/high-signal families before low-value mechanical/test-point groups;
   - identity samples and refdes samples for reviewer triage.
9. D1 must produce reviewer-consumable artifacts:
   - a Markdown profile-gap analysis summary;
   - a CSV document-index candidate list when document gaps exist;
   - optionally a next-family Markdown advisory if the input has enough
     grouped coverage data.
10. The analysis must state its trust boundary directly: uncovered groups are
   planning rows, not electrical verdicts.

## Acceptance Criteria

- [x] `prd.md` defines D1 scope, non-goals, and acceptance criteria.
- [x] Planning records that D1 is not report-only reuse yet: it first needs
  `.xlsx` / Chinese-header BOM intake compatibility for the user-provided
  public folder.
- [x] The public folder topology smoke remains reproducible:
  `inspect-allegro-netlist <folder>` reports 8180 components and 6918 nets.
- [x] `inspect-bom-match <folder> RFMS5H2TABom(13).xlsx` can parse the BOM and
  report a high-confidence refdes join instead of a BOM header error.
- [x] `design-validator-ui <folder> RFMS5H2TABom(13).xlsx --index-json ...`
  can produce a `ProjectValidationIndex` JSON for D1 analysis.
- [x] Running D1 against the public mainboard input can produce:
  - a profile-gap Markdown summary;
  - document candidate CSV rows for groups needing public datasheets;
  - no new PASS/WARN/ERROR for previously manual/no-profile rows.
- [x] The output groups large projects by identity/family and includes refdes
  samples instead of dumping thousands of individual manual rows.
- [x] The output distinguishes generic passive coverage from source-backed
  profile validation.
- [x] The analysis uses only public repo fixtures, public document/profile
  artifacts, or user-provided public-safe inputs.
- [x] `uv run pytest -q` and `uv run ruff check .` remain the final code-change
  gate if D1 moves from planning into implementation.

## Completion Evidence

Real public-safe mainboard smoke:

```text
Topology: 8180 components / 6918 nets / 24563 properties
BOM match: 7248 matched, 932 design-only, 9 duplicate BOM refdes, 0 BOM-only
Workbench/index: 8180 components, validated=6573,
  PASS/WARN/ERROR=3867/2706/0, manual=1607
Grouped coverage: 195 component groups
Document candidates: 75
Next-family advisory: 6 families, try_existing=3, triage_new=3
```

Generated artifacts:

```text
/tmp/hardwise-mainboard-d1-auto-workbench.html
/tmp/hardwise-mainboard-d1-auto-index.md
/tmp/hardwise-mainboard-d1-auto-index.json
/tmp/hardwise-mainboard-d1-document-candidates.csv
/tmp/hardwise-mainboard-d1-next-family.md
```

Final gates before commit:

```text
uv run pytest -q      # 482 passed, 7 deselected
uv run ruff check .   # passed
git diff --check      # passed
```

## Non-Goals

- No new family validator.
- No new ready datasheet profile.
- No automatic datasheet download.
- No PDF text extraction or LLM fact extraction.
- No broad spreadsheet import framework beyond the narrow public BOM schema
  needed for D1.
- No L2 grounded-LLM verdicts.
- No supplier, PLM, lifecycle, price, availability, PCB/layout, boardview,
  placement, routing, simulation, or internal hardware scope.
- No claim that all deterministic coverage is datasheet-backed deep review.

## Open Question

Should D1 treat the Chinese BOM `编号` as the primary part identity for grouping,
or should it keep `编号` as an internal item number and derive grouping from
`名称` plus `位号` only?

Recommended answer: keep `编号` as `item_number` / source identity, not MPN.
Use `名称` conservatively for display/grouping until a public document-index row
or profile supplies a real MPN. The trade-off is that early document candidate
search queries may be noisier, but Hardwise avoids fabricating device identity
from a procurement/internal code.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
