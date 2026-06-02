# Design

## Boundaries

This task expands deterministic schematic-side validation only. It does not add
PCB/layout inspection, supplier lookup, PLM/lifecycle state, pricing, live web
fetch during validation, or company-internal data.

All new validators must consume the existing `Design`, `Component`,
`DatasheetProfile`, and `ValidationReport` contracts. Refdes surfaced in reports
must come from the parsed design and remain protected by the existing Refdes
Guard path.

## Architecture

### Generic passive validation

Add a profile-free validation path for BOM groups whose normalized family is
`capacitor` or `resistor`.

This path should live in validation code, not report rendering. It returns the
same `ValidationReport` shape as profile-backed validation so project index,
HTML workbench, JSON export, Copilot traces, and markdown summaries can share
one truth model.

Suggested report identity:

- capacitor: `profile_part_number = "GENERIC_CAPACITOR"`
- resistor: `profile_part_number = "GENERIC_RESISTOR"`

Rows may keep `profile_path = None`, with `match_status = "generic_passive"` and
a localized reason explaining that generic rules do not need a per-MPN profile.

Capacitor checks:

- parse capacitance from BOM/component value;
- parse rated voltage from BOM/component value;
- check package exists and looks capacitor-family compatible;
- compare rated voltage to the maximum deterministic terminal voltage when any
  terminal net voltage can be inferred; and
- skip the voltage-margin judgment without guessing when net voltage is unknown.

Resistor checks:

- parse resistance from BOM/component value;
- parse explicit power rating when present;
- check package exists and looks resistor-family compatible;
- estimate `P = V^2 / R` only when both terminal voltages are known and
  resistance is non-zero; and
- warn, not error, for zero-ohm bridges between distinct known rails because
  these may be stuffing options.

### 74LV165PW shift-register topology

Add a ready profile for `74LV165PW` aliases and a new
`topology_family: shift_register_piso` validator. The validator should be
generic enough for 8-bit parallel-in/serial-out shift registers, but scoped by
profile facts instead of part-number string checks.

Checks:

- VCC and GND pin checks reuse pin-level validation.
- PL/load pin is connected and shared across peer devices when expected.
- CP/clock pin reaches a common upstream clock either directly or through a
  single series resistor.
- CE/clock-enable pin is tied to a defined net, ideally ground or a pull path.
- Q7 output cascades to another device's DS input directly or through one
  resistor when a next stage is present.
- The terminal Q7 stage is allowed when it leaves the register chain instead of
  feeding another DS input.

### LN2312LT1G MOSFET profile

Add a ready `ln2312lt1g.json` profile with aliases for `LN2312LT1G` and
`S-LN2312LT1G`. Use the existing `topology_family: mosfet` validator.

The profile must record the public LRC/Leshan facts available from the PDF:
20 V N-channel MOSFET, VGS abs max +/-8 V, SOT-23, and pin roles. Because the
available source is distributor/mirror hosted, keep evidence tokens explicit and
do not overclaim vendor-hosted provenance.

### PCA9617ADP I2C level-shift repeater

Add a ready `pca9617a.json` profile and a new
`topology_family: i2c_level_shift_repeater` validator.

Checks:

- VCCA is within 0.8 V to 5.5 V.
- VCCB is within 2.2 V to 5.5 V.
- GND is ground-like.
- EN is connected to a deterministic enable/control net.
- Port A has both SCLA and SDAA connected.
- Port B has both SCLB and SDAB connected.
- Port A and B bus-side net names should look like I2C/SMBus/PMBus clocks and
  data when names are informative; anonymous net names should produce
  non-fatal review text, not invented errors.

### Diode pack

Add only profiles that fit existing diode validator assumptions. Avoid new
speculative current/protection semantics unless the profile can support them
with public source tokens and tests.

Initial candidates from the real Allegro sample:

- `1.5SMC15A` TVS, 5 refdes
- `SM340AF SMA-FL` Schottky, 5 refdes
- `SD103AWS-7-F` Schottky/small-signal diode, 3 refdes
- LED groups may be included only if pin evidence and polarity semantics are
  reliable enough for the existing LED path.

## Compatibility

The existing `ValidationReport` schema remains unchanged. Report and UI changes
should be additive labels/reasons. Profile candidates should continue exact
normalized matching by `part_number` and aliases.

Generic passives intentionally do not create JSON profiles per BOM value. That
keeps the profile library for datasheet-backed devices and avoids thousands of
low-value profile files.

## Rollback

Each validator family is independently removable:

- generic passives are one project-index dispatch branch plus validator module;
- shift-register and I2C repeater validators are profile-dispatched topology
  families; and
- diode/MOSFET additions are data-profile changes unless tests expose profile
  mismatch risk.
