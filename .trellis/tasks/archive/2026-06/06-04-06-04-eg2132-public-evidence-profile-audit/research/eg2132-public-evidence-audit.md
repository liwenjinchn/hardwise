# Research: EG2132 public official datasheet evidence audit

- Query: Audit EG2132 public official datasheet evidence for profile/validator assumptions: official source URLs, pinout, VCC limits, HIN/LIN logic thresholds, VB-VS/bootstrap topology, and bootstrap diode reverse-voltage requirement.
- Scope: mixed
- Date: 2026-06-04

## Findings

### Files found

- `data/datasheet_profiles/eg2132.json` - Ready EG2132 structured profile with pinout, VCC range, logic input threshold, bootstrap topology, and a `bootstrap_diode_min_reverse_voltage` field.
- `src/hardwise/validation/gate_driver.py` - Half-bridge gate-driver validator consuming EG2132 profile facts for VCC, logic inputs, gate loads, switch node, and bootstrap diode/capacitor checks.
- `src/hardwise/validation/gate_driver_helpers.py` - Helper logic that classifies bootstrap diode voltage hints from diode identity strings.
- `tests/validation/test_component.py` - EG2132 fixture tests asserting current 24 V bootstrap diode policy behavior and VCC/logic topology behavior.
- `tests/fixtures/allegro/eg2132_gate_driver.net` - Local fixture netlist with EG2132, high/low MOSFETs, bootstrap diode, and bootstrap capacitor.
- `.trellis/spec/backend/validation-guidelines.md` - Validator/profile contracts for source-backed ready profiles and topology PASS evidence.
- `.trellis/spec/backend/quality-guidelines.md` - Datasheet evidence test guidance for deterministic page/token provenance.

### Official public sources

- Official product page: `https://egmicro.com/products/detail?name=EG2132`
  - Accessible during audit. Page title identifies `EG2132 - 中压300V1A半桥驱动芯片`.
  - Product page exposes the official document metadata: `EG2132 中压300V1A半桥驱动芯片数据手册.pdf`, doc type `数据手册`, date `2025-01-21`.
  - Product page parameters list suspended supply `300`, low-end supply `8-20`, input logic `HIN,LIN`, output current `1.0/1.5`, package `SOP8`.
  - Product page description says the high-side working voltage reaches 300 V, low-side Vcc range is `9V - 20V`, and HIN/LIN include 200K pull-down resistors.
- Official PDF URL:
  - `https://www.egmicro.com/static/doc/%E5%8A%9F%E7%8E%87%E9%A9%B1%E5%8A%A8%E8%8A%AF%E7%89%87/%E5%8D%95%E7%9B%B8%E5%8D%8A%E6%A1%A5/EG2132%20%E4%B8%AD%E5%8E%8B300V1A%E5%8D%8A%E6%A1%A5%E9%A9%B1%E5%8A%A8%E8%8A%AF%E7%89%87%E6%95%B0%E6%8D%AE%E6%89%8B%E5%86%8C.pdf`
  - `curl -I -L` returned HTTP 200, `content-type: application/pdf`, `content-length: 367902`, `last-modified: Fri, 17 Jan 2025 07:49:30 GMT`, and content-disposition filename `EG2132 300V1A.pdf`.
  - PDF text identifies `EG2132 芯片数据手册 V1.1`; revision table says V1.0 initial draft on 2017-10-10 and V1.1 modified undervoltage points on 2021-12-20.

### Pinout evidence

- Official PDF, extracted PDF page 5, printed datasheet page `2/9`, section 4.1/4.2:
  - Pin diagram shows top pins `8 VB`, `7 HO`, `6 VS`, `5 LO`; bottom pins `1 Vcc`, `2 HIN`, `3 LIN`, `4 GND`.
  - Pin table states:
    - `1 VCC` - chip supply input, voltage range 9V-20V.
    - `2 HIN` - high-level active logic input controlling high-side MOSFET.
    - `3 LIN` - high-level active logic input controlling low-side MOSFET.
    - `4 GND` - chip ground.
    - `5 LO` - low-side MOSFET control output.
    - `6 VS` - high-side floating ground.
    - `7 HO` - high-side MOSFET control output.
    - `8 VB` - high-side floating supply.
- Internal profile matches this public pin ordering at `data/datasheet_profiles/eg2132.json:18`.
- Internal pin entries cite `datasheet:eg2132.pdf#p2` for all pins at `data/datasheet_profiles/eg2132.json:43`, `:59`, `:75`, `:89`, `:102`, `:116`, `:130`, and `:146`.

### VCC recommended and absolute maximum evidence

- Recommended operating VCC:
  - Official PDF, extracted PDF page 4, printed page `1/9`, description: `低端 Vcc 的电源电压范围宽 9V～20V`.
  - Official PDF, extracted PDF page 5, printed page `2/9`, pin description: `电压范围 9V-20V`.
  - Official PDF, extracted PDF page 10, printed page `7/9`, section 8.1: `推荐电源 VCC 工作电压典型值为 9V-20V`.
  - Official product page parameter table lists `低端电源(V)` as `8-20`, but the official PDF repeatedly states 9V-20V for operating/application text. Treat product-page `8-20` as a marketing/param-table discrepancy unless the code deliberately follows the product page instead of the PDF.
- Absolute maximum VCC:
  - Official PDF, extracted PDF page 7, printed page `4/9`, section 7.1 `极限参数`: `VCC 电源 -0.3 25 V`.
  - Current profile uses `abs_max.vcc = 20.0` at `data/datasheet_profiles/eg2132.json:4`, which does not match the PDF absolute maximum table. It appears to be using the operating/recommended maximum, not the absolute maximum.
- Current validator:
  - `_validate_vcc()` reads `recommended.vcc` evidence and enforces `vcc_min`/`vcc_max` from the profile at `src/hardwise/validation/gate_driver.py:45`, `:55`, `:56`, and `:74`.
  - The current profile sets `recommended.vcc_min = 8.0` and `recommended.vcc_max = 20.0` at `data/datasheet_profiles/eg2132.json:11`. PDF-backed operating minimum is stronger as 9.0 V; product page says 8 V.

### HIN/LIN logic high threshold evidence

- Official PDF, extracted PDF page 8, printed page `5/9`, section 7.2 `典型参数`:
  - `Vin(H)` for all input control signals has minimum `2.8 V`.
  - `Vin(L)` for all input control signals is `-0.3 / 0 / 1.5 V` min/typ/max.
- Official PDF, extracted PDF page 10, printed page `7/9`, section 8.2:
  - `逻辑信号输入端高电平阀值为 2.8V 以上，低电平阀值为 1.5V 以下`.
- Product page feature text says compatible with 5V and 3.3V input voltages, but does not state a numeric 2.5 V threshold.
- Current profile sets `logic_high_min = 2.5` at `data/datasheet_profiles/eg2132.json:13`, and per-pin HIN/LIN limits at `data/datasheet_profiles/eg2132.json:53` and `:69`. Official PDF evidence supports `2.8 V`, not `2.5 V`.
- Current validator does not numerically validate HIN/LIN voltage; it only checks net naming/connectivity at `src/hardwise/validation/gate_driver.py:91`.

### VB-VS rating and bootstrap topology evidence

- High-side/bootstrap voltage:
  - Official PDF, extracted PDF page 4, printed page `1/9`, feature: `高端悬浮自举电源设计，耐压可达 300V`.
  - Official PDF, extracted PDF page 7, printed page `4/9`, absolute maximum table:
    - `VB 自举高端 VB 电源 -0.3 300 V`.
    - `VS 高端悬浮地端 VB-25 VB+0.3 V`.
    - `HO 高端输出 VS-0.3 VB+0.3 V`.
  - This is a high-side absolute rating, not the same as `VB-VS = 20 V`.
- Bootstrap topology:
  - Official PDF, extracted PDF page 6, printed page `3/9`, typical application circuit shows `+15V -> D3 -> VB`, `C2` between `VB/HO path` and `VS`, and `+300V` half-bridge context.
  - Official PDF, extracted PDF page 11, printed page `8/9`, section 8.3 states EG2132 uses a bootstrap floating supply structure and can use `外接一个自举二极管` plus `一个自举电容`.
  - Same section states the bootstrap capacitor is charged to `Vc=VCC` and becomes the supply for internal driver `VB` and `VS`.
- Current profile:
  - `abs_max.vb_vs = 20.0` at `data/datasheet_profiles/eg2132.json:6` is plausible as a local abstraction of the typical bootstrap capacitor/supply limit, but the official absolute table does not directly state a `VB-VS 20 V` row. The closest direct table entries are `VS = VB-25 to VB+0.3`, `HO = VS-0.3 to VB+0.3`, and `VCC max 25 V`.
  - Pin 8 `VB` has `vb_vs_abs_max = 20.0` at `data/datasheet_profiles/eg2132.json:140`; this is not directly supported by the PDF absolute maximum wording found during audit.

### Bootstrap diode reverse-voltage evidence

- The official PDF directly states the topology needs an external bootstrap diode and bootstrap capacitor:
  - PDF page 11 / printed page `8/9`: `外接一个自举二极管` and `一个自举电容`.
  - Figure 8-3 labels `外接自举二极管`, `VB`, `VS`, `VCC`, and the +300 V bridge context.
- No official PDF text found during this audit directly states a bootstrap diode reverse-voltage minimum such as 24 V, 25 V, 300 V, or any explicit diode VRRM requirement.
- Current profile sets `bootstrap_diode_min_reverse_voltage = 24.0` at `data/datasheet_profiles/eg2132.json:15` and labels its evidence as `datasheet:eg2132.pdf#p6` at `data/datasheet_profiles/eg2132.json:157`.
- Current validator consumes that field as a board-level diode rating policy at `src/hardwise/validation/gate_driver.py:260`, compares it to `diode_reverse_voltage_hint()` at `src/hardwise/validation/gate_driver.py:261`, and errors below the profile minimum at `src/hardwise/validation/gate_driver.py:262`.
- Current helper maps `MBRA210` to 10 V and `SS34`/similar parts to 40 V at `src/hardwise/validation/gate_driver_helpers.py:86`.
- Current tests assert that the fixture diode `MBRA210LT3G` fails because it is "below required 24 V" at `tests/validation/test_component.py:489`.
- Conclusion: The 24 V bootstrap diode reverse-voltage minimum is not directly EG2132-datasheet-stated in the official public PDF found. It should be treated as a board-level validator policy unless another public source is added. If kept, its evidence token should not claim `datasheet:eg2132.pdf#p6` as a direct datasheet source for the numeric 24 V value.

### Related specs and patterns

- `.trellis/spec/backend/validation-guidelines.md` requires ready profiles to be promoted only when public pinout/polarity/limit evidence matches the local symbol.
- `.trellis/spec/backend/validation-guidelines.md` requires validators to use profile pin numbers and structured profile data rather than part-number-specific dispatch branches.
- `.trellis/spec/backend/quality-guidelines.md` requires datasheet provenance to remain deterministic through page/evidence tokens.
- `src/hardwise/ir/profile.py:28` defines `DatasheetProfile` with separate `abs_max`, `recommended`, `pin_function`, `pins`, and `evidence` fields, so a board policy should be separable from direct datasheet facts.

## Caveats / Not Found

- Page references above distinguish extracted PDF page numbers from the printed datasheet footer pages. The current profile tokens such as `datasheet:eg2132.pdf#p2` appear to refer to printed datasheet pages, while `pdftotext` extraction counts cover/revision/TOC pages first.
- The official product page and official PDF disagree on low-end supply minimum: product page parameter table says `8-20`; PDF description, pin table, and application section say `9V-20V`. The research preference is the official PDF for profile evidence, but this discrepancy should be flagged if changing profile contracts.
- The official PDF absolute maximum table supports `VCC max 25 V`, not current profile `abs_max.vcc = 20 V`.
- The official PDF supports HIN/LIN logic high threshold `2.8 V`, not current profile `2.5 V`.
- No public official source found in this audit directly states `bootstrap_diode_min_reverse_voltage = 24 V`; this appears to be a validator policy derived from expected board supply margin rather than a datasheet-stated EG2132 limit.
