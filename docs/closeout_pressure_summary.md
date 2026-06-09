# Hardwise Closeout Pressure-Test Summary

This is the small committed summary for the closeout pressure-test rerun. The
large generated HTML/JSON artifacts stayed under `/tmp` and are not part of the
repo.

## Scope

- Switch and mainboard fixture exports are pressure tests, not the primary public
  demo.
- Inputs are public/synthetic Allegro/PST + BOM fixture exports already used by
  the closeout branch.
- This committed page keeps only aggregate counts, not raw board artifacts.
- No company-internal hardware data is used or recorded here.
- No local absolute input paths are recorded here.
- The measured changes come from Workstream A generic inductor/ferrite coverage
  and Workstream B PE537BA MOSFET profile coverage.

## Results

| Board | Components | BOM matched | Validated before | Validated after | Manual before | Manual after | PASS after | WARN after | ERROR after |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Switch fixture | 4010 | 4010 | 3738 | 3794 | 272 | 216 | 3663 | 125 | 6 |
| Mainboard fixture | 8180 | 7248 | 6752 | 6847 | 1428 | 1333 | 3921 | 2926 | 0 |

## Coverage Movement

| Board | Slice | Rows moved out of manual | Resulting profile/status |
|---|---|---:|---|
| Switch fixture | Generic inductor | 18 | `GENERIC_INDUCTOR`, light deterministic coverage |
| Switch fixture | Generic ferrite | 38 | `GENERIC_FERRITE`, light deterministic coverage |
| Mainboard fixture | Generic inductor | 41 | `GENERIC_INDUCTOR`, light deterministic coverage |
| Mainboard fixture | Generic ferrite | 43 | `GENERIC_FERRITE`, light deterministic coverage |
| Mainboard fixture | PE537BA P-MOS | 11 | `PE537BA`, MOSFET validator, WARN because static drain/load voltage is not inferred |

## Remaining Gaps

| Board | Top remaining family gaps | Why deferred |
|---|---|---|
| Switch fixture | `ic` 35 refdes / 14 groups; `unknown` 41 / 6; `diode` 8 / 2 | IC/diode rows need reviewed public profiles or family-specific rules; unknown rows need identity cleanup before validator work. |
| Mainboard fixture | `unknown` 1118 refdes / 957 groups; `ic` 121 / 28; `diode` 54 / 8 | Unknown is mostly intake/classification work; IC/diode groups are candidates for future public-document review and scoped family validators. |

## Interpretation

The closeout branch improved coverage without changing the product claim:
Hardwise remains a trusted pre-Layout schematic-review workbench. Generic
inductor/ferrite rows are conservative L1 facts from BOM/package/connectivity,
not topology or EMI sufficiency checks. PE537BA proves the existing MOSFET
validator can handle a P-channel profile while preserving the source-referenced
Vgs rule and leaving unknown drain/load voltage as WARN.
