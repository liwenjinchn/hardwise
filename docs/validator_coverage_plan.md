# Validator Coverage Plan

Hardwise's real Allegro demo should tell a two-layer review story:

1. broad deterministic coverage for the whole schematic, especially generic
   passives; and
2. deeper topology checks for repeated high-value devices.

This keeps the claim honest. Generic passive rules are light coverage, not
datasheet-backed deep validation. Profile-backed IC, transistor, and diode
rules remain the higher-confidence deep checks.

## Priority Order

| Priority | Action | Coverage value | Reason |
|---|---|---:|---|
| 0 | Generic passive validator | +3642 refdes | One validator family covers most of the board and fixes the "passives untouched" demo gap. |
| 1a | 74LV165PW shift-register validator | +10 refdes | Shows signal-chain topology checks, not just voltage-limit checks. |
| 1b | LN2312LT1G MOSFET profile | +56 refdes | Highest repeated non-passive count; should reuse the existing MOSFET validator once public source evidence is recorded. |
| 2 | PCA9617ADP I2C level-shift repeater | +8 refdes | Useful I2C ecosystem coverage, but this is a level-shift/buffer rule, not an I2C mux rule. |
| 3 | Diode profile pack | +13 refdes now, +6 deferred | Existing diode validator can cover common protection/Schottky groups with modest profile work; ambiguous LED polarity stays manual until source evidence is clear. |

## Generic Passive Scope

Capacitors:

- parse capacitance and rated voltage from BOM/component value;
- compare rated voltage with inferred net voltage when rail voltage is
  deterministic; and
- keep unknown-voltage nets as non-fabricated review text rather than guessed
  failures.

Resistors:

- parse resistance and optional power rating;
- estimate power only when both terminal voltages are deterministic;
- warn on zero-ohm bridges between distinct known rails; and
- treat package checks as schematic package-family checks until the BOM exposes
  a separate package field.

## Deep-Check Scope

74LV165PW:

- validate supply/ground pins;
- prove shared PL/load control;
- prove CP/clock fanout directly or through one series resistor;
- prove Q7-to-DS cascade continuity; and
- allow the terminal stage to leave the chain toward the controller.

LN2312LT1G:

- add a public-source-backed N-channel MOSFET profile;
- reuse the existing MOSFET VGS/VDS validator; and
- record the source limitation because the available PDF is public but not
  ideal vendor-hosted evidence.

PCA9617ADP:

- add an I2C level-shift repeater profile;
- validate VCCA/VCCB voltage ranges and GND/EN connectivity; and
- check SCLA/SDAA plus SCLB/SDAB bus-side pairing.

Diodes:

- add profiles only where existing diode semantics are a good fit;
- avoid inventing current/protection behavior that the validator does not yet
  prove; and
- prefer TVS/Schottky profiles over ambiguous LED polarity unless source and
  pin evidence are clear.

Implemented real-board diode pack:

- `1.5SMC15A`: 5 TVS refdes, PASS on 12 V rail-to-ground standoff using the
  existing cathode/anode reverse-voltage check;
- `SM340AF SMA-FL`: 5 Schottky rectifier refdes, PASS on 12 V rail-to-ground
  reverse-voltage checks;
- `SD103AWS-7-F`: 3 Schottky/signal diode refdes, connected but WARN because
  enable/control nets do not expose deterministic static voltages; and
- `RF-GTB191TS-BC`: deferred. The real board shows a plausible LED-resistor-
  NMOS indicator path, but public polarity drawings conflict with the local
  symbol naming, so Hardwise should not promote those 6 LEDs to deterministic
  PASS just to improve the count.

## Measured Real Allegro Result

Smoke command:

```bash
uv run hardwise design-validator-ui "<public Allegro folder>" \
  --output /tmp/hardwise-real-allegro-workbench.html \
  --index-output /tmp/hardwise-real-allegro-index.md \
  --index-json /tmp/hardwise-real-allegro-index.json \
  --ai-snapshot
```

Measured output:

| Metric | Count |
|---|---:|
| Components | 4010 |
| BOM matched | 4010 |
| Deterministically validated rows | 3738 |
| Manual/no-profile rows | 272 |
| PASS / WARN / ERROR | 3653 / 79 / 6 |

Top validated families:

| Profile / rule | Refdes count |
|---|---:|
| `GENERIC_CAPACITOR` | 2018 |
| `GENERIC_RESISTOR` | 1624 |
| `LN2312LT1G` | 56 |
| `74LV165` | 10 |
| `PCA9617A` | 8 |
| `1.5SMC15A` | 5 |
| `SM340AF SMA-FL` | 5 |
| `PCA9548A` | 5 |
| `MPQ8626` | 4 |
| `SD103AWS-7-F` | 3 |

Artifact paths used for the measured smoke:

- Workbench HTML: `/tmp/hardwise-real-allegro-workbench.html`
- Markdown index: `/tmp/hardwise-real-allegro-index.md`
- JSON index: `/tmp/hardwise-real-allegro-index.json`

## Demo Claim

The intended claim is:

> Hardwise aligns the full public Allegro BOM to the schematic, performs light
> deterministic checks across the passive majority, and runs deeper
> source-backed topology validators on selected repeated active devices.

It should not claim that every covered passive received datasheet-backed or
layout-aware validation.

## Scale Mechanism

The next scale mechanism is profile archetypes, not validator copy-paste.
`draft-datasheet-profile --archetype 74x165_piso_16pin` can generate a
`needs_review` skeleton for 74x165-style PISO shift registers with pin-role and
topology placeholders. That skeleton is intentionally ignored by automatic
validation until a reviewer confirms public datasheet evidence and promotes it
to `ready`.
