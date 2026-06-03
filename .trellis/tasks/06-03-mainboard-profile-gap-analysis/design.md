# Mainboard profile gap analysis design

## Boundary

D1 is an orchestration/reporting slice over existing coverage artifacts. It
does not alter validator dispatch, profile matching, profile schemas, or
PASS/WARN/ERROR semantics.

The first acceptance input is the user-provided public Allegro folder:

```text
/Users/liwenjin/Library/Containers/com.comisys.lanxin.hgo/Data/Library/Application Support/lanxin_macgoh/custom/files/lanxindownload/04_设计文件与EDA/allegro
```

Its PST topology parses successfully today, but its BOM does not. Therefore D1
has a narrow input-compatibility prerequisite before the coverage analysis can
run: support the folder's Chinese-header Excel BOM shape or produce an
equivalent normalized BOM artifact in a reproducible way.

## Existing Contracts To Reuse

- `ProjectValidationIndex` in `src/hardwise/validation/project_index.py` is the
  source of truth for project coverage rows and component groups.
- `profile_gap_groups(index)` groups manual/no-profile rows by identity for
  scannable review.
- `build_document_candidate_report(index_path)` and
  `render_document_candidate_csv(report)` already create document-index
  candidate rows from grouped coverage data.
- `build_family_coverage_report(index_path)` and
  `render_family_coverage_markdown(report)` already create next-family
  advisory Markdown.
- Reporting guidelines require no-profile/manual rows to remain coverage
  artifacts and forbid converting them into electrical judgements.

## Research Confirmation

Grok Search plus official-source cross-check supports the current D1 design:

- Cadence's public OrCAD X BOM guidance describes BOM output as component
  information for manufacturing/procurement and names standard columns such as
  line item, quantity, reference designator, and description. This supports
  mapping the Chinese `位号` column to refdes and `数量` to quantity, while
  keeping BOM identity separate from schematic topology.
  Source: https://resources.pcb.cadence.com/blog/2024-how-to-create-a-bom-file-with-orcad-x
- Cadence's Allegro Constraint Manager user guide describes the PST package
  files as front-to-back logic/netlist artifacts: `pstxnet.dat` carries nets
  and refdes/pin associations, `pstxprt.dat` carries physical packages/parts
  and refdes/device type, and `pstchip.dat` carries symbol/package information.
  This supports keeping PST parsing topology-only and joining BOM identity by
  refdes afterward.
  Source: https://resources.pcb.cadence.com/constraint-manager-user-guide/04-phases-in-the-design-flow
- openpyxl's official documentation supports `load_workbook(...,
  read_only=True, data_only=True)` for efficient read-only `.xlsx` value
  extraction. Read-only workbooks should be closed explicitly, and `data_only`
  reads cached formula results rather than formulas. This supports a narrow
  parser extension for the Chinese-header workbook instead of a broader
  spreadsheet framework.
  Sources:
  - https://openpyxl.readthedocs.io/en/stable/optimized.html
  - https://openpyxl.readthedocs.io/en/3.1/tutorial.html

## Input Contract

### Topology

Use the existing Capture/Allegro PST parser over the project folder. Confirmed
smoke:

```text
components: 8180
nets: 6918
properties: 24563
```

The topology remains schematic-only. It is not `.brd`, boardview, placement,
routing, or PCB geometry evidence.

### BOM

The public folder has `RFMS5H2TABom(13).xlsx` with one sheet and headers:

```text
序号 | 名称 | 编号 | 层级 | 标识 | 数量 | 特定替代件 | 位号 | 单位 | 使用规则 | 使用规则描述 | 状态
```

D1 should add a narrow adapter or normalization path with this mapping:

| Chinese column | D1 use |
|---|---|
| `序号` | source row / item order |
| `名称` | conservative display value / description |
| `编号` | item number or source identity, not automatically an MPN |
| `数量` | quantity; accept whole-number numeric spreadsheet values |
| `位号` | reference designator list |
| `状态` | optional source status metadata for display only |

Rows without `位号` are not component BOM rows for Hardwise matching. They
should not be forced into `BomItem.refdes_list`.

## Output Shape

The Markdown profile-gap analysis should include:

1. Input and scope boundary.
2. Board coverage metrics: components, BOM matched, validated/manual rows,
   PASS/WARN/ERROR totals.
3. Trust-tier explanation: L1 deterministic rows vs L3 manual/profile gaps.
4. Top profile-gap groups with identity, family, document status, profile
   status, refdes count, and refdes sample.
5. Action buckets:
   - add public document-index row;
   - draft or review profile;
   - try existing validator/profile family;
   - leave manual because identity/source evidence is ambiguous.
6. Links or paths to generated CSV/next-family advisory artifacts when present.

CSV output should reuse the existing document-candidate columns rather than
inventing a second document-index draft format.

## Trade-Offs

Report-only reuse is lowest risk if existing commands already produce all
needed artifacts. The new evidence shows they do not yet: topology reuse works,
but BOM intake does not handle `.xlsx` / Chinese headers. The smallest
implementation path is likely a narrow `parse_bom()` extension for this schema
plus `.xlsx` auto-discovery, followed by reuse of existing index/candidate
commands.

An external one-off conversion script would be faster, but weaker: D1 would
depend on an undocumented pre-processing step. A parser extension is slightly
larger but makes `design-validator-ui <folder> <xlsx>` and future workbench
flows reproducible.

## Stop Conditions

- Stop if the only available mainboard data is company-internal or not
  public-safe.
- Stop if the BOM mapping cannot preserve refdes and quantity without guessing.
- Stop if the requested output would require turning manual/no-profile groups
  into PASS/WARN/ERROR without a ready profile and deterministic validator.
- Stop if D1 needs new profile facts or new validators; that is a follow-up
  implementation task, not profile-gap analysis.
