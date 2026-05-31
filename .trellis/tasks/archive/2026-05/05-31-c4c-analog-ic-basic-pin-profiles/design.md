# Design

## Boundary

C4c is a profile-coverage closure, not a new IC validation family. The existing
`profile_candidates` flow should match BOM identities to local ready profiles,
and `validate_component_against_profile()` should run generic pin-level checks.

## Data Model

Add four `data/datasheet_profiles/*.json` files:

- `lmv358.json`
- `lm393.json`
- `ina180a1.json`
- `tlv9062.json`

Each profile records package pin numbers, pin functions, supply limits where
useful, and evidence tokens pointing to the public TI datasheet filename.

## Pin Categories

Existing generic pin validation handles `analog_input` but not output-style
analog/comparator pins. Add only connected-pin handling for:

- `analog_output`
- `open_collector_output`

These categories should behave like `analog_input` in this slice: they pass when
the profiled pin is present and connected, and do not infer behavior.

## Non-Goals

- No `topology_family="op_amp"` / `"comparator"` / `"current_sense"` dispatch.
- No gain, offset, threshold, output swing, bandwidth, stability, shunt sizing,
  load-current, thermal, simulation, PCB, or layout checks.
- No L2/LLM judgment.

## Compatibility

The added profiles should only affect BOM identities that exactly match the new
profile `part_number` or aliases. Existing LED, BJT, buck, gate-driver, MCU,
connector, MOSFET, and diode validation rows must remain stable.
