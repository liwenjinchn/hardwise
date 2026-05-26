# Hardwise Switch-Board Demo

This demo uses a public Cadence Capture/Allegro PST schematic export plus its schematic BOM to show the deterministic validation loop on a workflow closer to day-to-day hardware review.

## Inputs

- **Allegro/PST directory**: Capture/Allegro schematic netlist topology (`pstxprt.dat`, `pstxnet.dat`, optional `pstchip.dat`).
- **Schematic BOM**: BOM exported from the schematic tool, joined to design components by refdes.
- **Profile catalog**: `data/datasheet_profiles/profile_catalog.json`, mapping BOM identities to locked datasheet profiles and deterministic validators.

All demo inputs must be public/reproducible. Do not use company-internal hardware data, even sanitized.

## Run the demo

```bash
uv run hardwise validate-allegro-project \
  "<public-switch-board>/allegro" \
  "<public-switch-board>/SWITCH BOARD 144-VA_20240712 1401.BOM" \
  --output reports/switch-board-validation-index.md \
  --index-json reports/switch-board-validation-index.json \
  --detail-dir reports/switch-board-validation-details
```

For this repository's local public sample path, replace `<public-switch-board>` with the directory that contains the exported `allegro/` PST folder and BOM file.

## Outputs to open

- `reports/switch-board-validation-index.md` — project-level validation index and validated-family summary.
- `reports/switch-board-validation-index.json` — JSON sidecar for UI/component workspace prototypes.
- `reports/switch-board-validation-details/U86.md` — per-component deterministic validation details for one `74LV165` shift register.

Optional explanation view:

```bash
uv run hardwise explain-component \
  reports/switch-board-validation-index.json \
  U86 \
  --output reports/switch-board-U86-explanation.md
```

This explains the stored checks and evidence for `U86` without creating new findings.

## Current smoke result

Current public switch-board smoke output:

```text
4010 components in design
4010 BOM matched
79 validated components
PASS=301, WARN=0, ERROR=0, manual_needed=112
```

Validated family summary:

| Profile | Template | Components | PASS | WARN | ERROR | manual_needed |
|---|---|---:|---:|---:|---:|---:|
| LN2312LT1G | nmos | 56 | 168 | 0 | 0 | 112 |
| 74LV165 | 74lv165 | 10 | 60 | 0 | 0 | 0 |
| PCA9617A | pca9617a | 8 | 48 | 0 | 0 | 0 |
| PCA9548A | pca9548a | 5 | 25 | 0 | 0 | 0 |

## Reliability boundary

Hardwise only explains facts that are already present in the parsed design, BOM join, locked datasheet profiles, and deterministic validator outputs.

It does **not** perform:

- PCB/layout, placement, routing, SI/PI, thermal, or boardview review.
- PLM, price, lifecycle, inventory, or supplier-risk review.
- Free-form datasheet interpretation at report time.
- Voltage inference without explicit evidence. Net-voltage checks use name-rule evidence only, such as `P3V3_STBY -> 3.3 V`.
- Free-generated refdes, pins, or datasheet facts.

## Recommended demo path

1. Open `reports/switch-board-validation-index.md` and start with **Validated Family Summary**.
2. Open `reports/switch-board-validation-details/U86.md` to show pin-level checks, messages, and evidence tokens.
3. Open `reports/switch-board-U86-explanation.md` to show the explanation layer: it summarizes stored checks but does not invent new conclusions.
4. Point out remaining `no_profile` groups as planned coverage expansion, not guessed validation.
