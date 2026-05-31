# Design

## Boundary

C4d is a diode-family sub-role extension, not a generic inductor or generic TVS
product-line validator. The existing component dispatcher must remain
`recommended.topology_family` driven.

## Data Model

Add `data/datasheet_profiles/smbj24ca.json`:

- `part_number="SMBJ24CA"`
- `review_status="ready"`
- `recommended.topology_family="diode"`
- `recommended.diode_role="bidirectional_tvs"`
- `recommended.working_standoff_voltage=24.0`
- Two non-polar TVS terminals using `switch_node` pin categories

## Validator Behavior

In `validation/diode.py`, route `diode_role="bidirectional_tvs"` inside the
existing diode validator. For this role:

- Check both profiled terminals are present and connected.
- Check exactly enough topology to prove a rail clamp: one terminal should be on
  a recognized ground net and the opposite terminal should be the
  protected rail.
- If the protected rail voltage is known, compare `abs(rail - reference)` with
  `recommended.working_standoff_voltage`; above standoff is ERROR.
- If the protected rail voltage is unknown, WARN instead of fabricating.

## Non-Goals

- No generic TVS application validator across all interfaces.
- No unidirectional TVS orientation logic.
- No surge/ESD standard, pulse-power, capacitance, thermal, connector,
  placement, routing, or PCB geometry checks.
- No L2/LLM judgment.
