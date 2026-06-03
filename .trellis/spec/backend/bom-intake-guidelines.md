# BOM Intake Guidelines

> Contracts for schematic-exported BOM parsing and project-folder BOM selection.

---

## Scenario: Schematic BOM Intake

### 1. Scope / Trigger

Applies when changing:

- `src/hardwise/bom/parser.py`
- `src/hardwise/bom/types.py`
- `src/hardwise/project_inputs.py`
- CLI commands that accept a BOM path or auto-select a BOM from an Allegro/PST
  project directory

Trigger: adding a BOM file format, changing field mapping, changing
project-directory BOM discovery, or changing refdes/BOM identity matching.

### 2. Signatures

Parser entry point:

```python
def parse_bom(path: Path) -> Bom: ...
```

Project-folder resolver:

```python
def resolve_bom_input(
    *,
    netlist_path: Path,
    bom_path: Path | None,
    design: Design,
) -> ResolvedBomInput: ...
```

### 3. Contracts

- BOM parsing must emit the existing `Bom` / `BomItem` / `BomRow` shapes.
  Downstream matching, project indexes, and reports should not need to know
  whether the source was `.BOM`, `.csv`, `.tsv`, or `.xlsx`.
- Reference designators are the join key from BOM to schematic topology. They
  come from explicit reference/designator columns such as `Reference`, `Refdes`,
  or Chinese `位号`; do not infer refdes from descriptions, item names, or
  source item numbers.
- Quantity fields may arrive as spreadsheet whole-number strings like `2.0`;
  accept whole-number decimal display values, but reject non-integer quantities.
- For Chinese Excel BOMs with headers like `序号`, `名称`, `编号`, `数量`, and
  `位号`:
  - `位号` maps to `BomItem.refdes_list` through `split_refdes()`.
  - `数量` maps to `BomItem.quantity`.
  - `名称` maps to conservative display identity (`value` / `description`).
  - `编号` maps to `BomItem.item_number`; it is not automatically a public MPN.
- Rows without parseable refdes should not join to `Design.components`.
- Project-folder BOM discovery may include `.xlsx`, but only because
  `parse_bom()` owns the format contract and can return structured parse
  errors for unsupported workbooks.

### 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| Missing BOM header | Raise `BomParseError` with the expected header shape |
| Invalid quantity such as `two` | Raise `BomParseError` with file and row |
| Whole-number spreadsheet quantity such as `2.0` | Parse as integer `2` |
| `.xlsx` workbook lacks `位号` / `数量` | Raise `BomParseError` |
| `.xlsx` row has blank `位号` | Skip as non-component row |
| Project directory has multiple BOM candidates | Parse each candidate and auto-select the best refdes match |
| Project directory has no parseable BOM | Raise `BomParseError` listing candidate failures |

### 5. Good / Base / Bad Cases

- Good: `RFMS5H2TABom(13).xlsx` with Chinese headers parses into `BomItem`
  rows, keeps `编号` as `item_number`, and lets `design-validator-ui <folder>`
  auto-select it.
- Base: English CSV rows with `Reference,Quantity,Value,Manufacturer,MPN`
  continue to populate `part_number` when the source explicitly supplies MPN.
- Bad: Treating a Chinese `编号` procurement/source code as `part_number` and
  generating datasheet search/profile matches from it as if it were public MPN.
- Bad: Adding a one-off external conversion step that the CLI cannot reproduce.

### 6. Tests Required

- Parser tests for each new BOM format and header mapping.
- Regression tests that unsupported/invalid quantities still fail.
- Project-input or CLI tests when a new suffix is added to auto-discovery.
- Tests should assert identity boundaries: source item number fields must not
  silently become `part_number` unless the input column is explicitly MPN-like.

### 7. Wrong vs Correct

#### Wrong

```python
BomItem(part_number=row["编号"], refdes_list=split_refdes(row["名称"]))
```

#### Correct

```python
BomItem(
    item_number=row["编号"],
    value=row["名称"],
    description=row["名称"],
    refdes_list=split_refdes(row["位号"]),
)
```

The first version fabricates a public part identity and guesses refdes from
description text. The second preserves the source BOM identity while keeping
refdes matching explicit.
