# Real Allegro validator coverage expansion

## Goal

Expand Hardwise's real Allegro workbench coverage from a few profile-backed
ICs into a board-level review story:

- broad, generic passive checks for the 3642 capacitor/resistor refdes on the
  public Allegro sample;
- deeper deterministic topology checks for high-value repeated devices; and
- source-backed local profiles for the selected public datasheets.

The demo narrative should be "full-board light coverage plus focused deep
checks", not "100 deep-checked parts and 3900 untouched parts".

## Confirmed Facts

- Real public Allegro intake is healthy: 4010 design refdes, 4010 BOM matches,
  132 BOM groups, 3422 nets, and no BOM/design mismatches.
- Existing validated rows are profile-backed only:
  - PCA9548APW: 5 refdes
  - MPQ8626GD / MPQ8626GD-Z: 4 refdes
- The largest uncovered families are:
  - capacitor: 2018 refdes
  - resistor: 1624 refdes
  - transistor: 56 refdes
  - IC: 53+ uncovered refdes depending on profile state
  - diode: 21 refdes
- The sample BOM has `Item / Quantity / Reference / Part`; it does not expose a
  separate BOM package field. Schematic/package fields are available in the
  parsed design.
- Capacitor BOM values include rated voltage. In the current sample, 1346
  capacitors have enough static net-voltage context for direct voltage
  comparison and 672 do not.
- Resistors can support value parsing, zero-ohm bridge checks, and limited
  power estimates when both terminal voltages are known. In the current sample,
  58 resistors have two known static terminal voltages.
- Public datasheet availability:
  - 74LV165PW: official Nexperia 74LV165 PDF is available.
  - PCA9617ADP: official NXP PCA9617A PDF is available.
  - LN2312LT1G: public LRC/Leshan PDF is available via distributor/mirror
    sources; treat the source as public but less ideal than a vendor-hosted URL.

## Requirements

1. Add a generic passive validation path for capacitors and resistors without
   requiring one datasheet profile per passive value.
2. Add 74LV165PW profile support plus a shift-register topology validator that
   proves serial-chain continuity and common control nets on the real Allegro
   design.
3. Add an LN2312LT1G MOSFET profile that reuses the existing MOSFET validator
   and records public source evidence.
4. Add PCA9617ADP profile support plus level-translating I2C repeater checks.
   Do not describe this as an I2C mux rule.
5. Add a diode profile pack for the high-frequency real-board diode groups when
   existing diode validator semantics can cover them safely.
6. Update project documentation so the priority order and demo narrative are
   preserved.
7. Keep all work inside the schematic-review node: no PCB layout, boardview,
   PLM, supplier, price, lifecycle, or company-internal data.
8. Preserve the no-hallucinated-refdes invariant: all surfaced refdes must come
   from parsed design/BOM data.

## Acceptance Criteria

- [x] `docs/validator_coverage_plan.md` documents the priority order:
      generic passives, 74LV165PW, LN2312LT1G, PCA9617ADP, diode pack.
- [x] Running the real public Allegro workbench index shows generic validation
      rows for the 2018 capacitors and 1624 resistors, with gap groups no
      longer treating them as untouched no-profile rows.
- [x] Capacitor checks parse capacitance/rated voltage and compare rated
      voltage to inferred net voltage when deterministic rail voltage is known.
- [x] Resistor checks parse resistance/package, estimate power only when
      terminal voltages are known, and warn on zero-ohm bridges between distinct
      known rail voltages.
- [x] 74LV165PW rows validate VCC/GND pins, PL/CP/CE connectivity, common load
      fanout, clock fanout through direct or one-resistor paths, and Q7-to-DS
      serial-chain continuity on the real design.
- [x] LN2312LT1G rows match a local ready profile and run through the existing
      MOSFET validator.
- [x] PCA9617ADP rows match a local ready profile and run through a level-shift
      repeater validator that checks VCCA/VCCB ranges, EN connectivity, and
      SCLA/SDAA plus SCLB/SDAB bus-side pairing.
- [x] Diode groups selected from the real project match ready profiles and run
      existing diode checks without introducing speculative diode semantics.
- [x] `uv run pytest -q` and `uv run ruff check .` pass before completion is
      claimed.
- [x] A real Allegro smoke command regenerates the workbench/index and the
      summary proves the intended coverage increase.

## Notes

- Requested priority order:

| Priority | Action | Judgment |
|---|---|---|
| 0 | Generic passive validator | Required narrative base for the 3642 passive refdes. |
| 1a | 74LV165PW shift-register validator | Highest demo value because it proves signal-chain topology. |
| 1b | LN2312LT1G MOSFET profile | High ROI; reuse existing MOSFET rules after source capture. |
| 2 | PCA9617ADP | I2C level-shift/buffer rule, not an I2C mux rule. |
| 3 | Diode pack | Low-cost coverage because the diode validator already exists. |
