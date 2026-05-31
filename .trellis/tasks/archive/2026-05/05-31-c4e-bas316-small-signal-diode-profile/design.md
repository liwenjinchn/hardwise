# Design

## Boundary

C4e is a profile-only diode-family closure. It should not modify diode dispatch
or introduce dual-diode modeling.

## Data Model

Add `data/datasheet_profiles/bas316.json`:

- `part_number="BAS316"`
- `review_status="ready"`
- `recommended.topology_family="diode"`
- `pin_function`: pin 1 Cathode, pin 2 Anode
- `abs_max.reverse_voltage=100.0`

## Validator Behavior

The existing diode validator already checks cathode/anode connectivity and
reverse voltage when both net voltages are inferable. In the motor fixture, D21
connects CANH to GND, so connectivity is deterministic PASS and reverse voltage
is deterministic WARN because CANH has no voltage hint.

## Non-Goals

- No BAV99 dual-diode support.
- No CAN transceiver/interface suitability checks.
- No forward-current sizing, recovery-time suitability, capacitance, ESD/surge,
  PCB/layout, routing, or connector completeness checks.
- No L2/LLM judgment.
