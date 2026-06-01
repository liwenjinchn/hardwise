# Electrical Domain Review Findings

## Summary

The project has the right overall shape for a pre-layout schematic reviewer:
electrical judgments are mostly isolated under `src/hardwise/validation/`,
profiles are structured and source-tokened, reports repeatedly state the
schematic-only boundary, and tests cover many "do not guess" paths.

The main professional risks are not in the project framing; they are in a few
family validators that can produce false PASS results because they recognize
component prefixes or part-number families without checking enough of the
electrical path.

## Findings

### High: buck topology can pass a misplaced freewheel diode or incomplete output path

- Code: `src/hardwise/validation/dcdc.py:35`, `src/hardwise/validation/dcdc.py:111`
- Type: correctness bug / missing electrical model

`validate_buck_topology()` looks for an inductor and the first D-prefixed
component on the switch output net. `_validate_buck_diode()` then checks only
whether that diode identity looks Schottky-like. It does not check the diode's
other terminal is on the expected freewheel return path, nor that the inductor's
other terminal reaches the intended output/load/feedback rail.

A one-off check moved `D5.2` from `GND` to `+24V`, changed `D5` to `SS34`, and
changed `L1` to `100uH`; the report still returned PASS for both buck checks.

Recommended remediation: make the buck template validate the other terminal of
the diode and inductor. Unknown topology should WARN, not PASS.

### High: BAS-series diodes are classified as Schottky-style freewheel candidates

- Code: `src/hardwise/validation/topology.py:80`, `src/hardwise/validation/dcdc.py:133`
- Type: correctness bug / test gap

`is_likely_schottky_diode()` returns `True` for any `BAS*` identity. The repo
also has a ready `BAS316` profile as a small-signal switching diode. That means
a BAS316-like part can pass the buck freewheel Schottky-family gate even though
it is not a power freewheel diode.

Recommended remediation: remove `BAS` from the Schottky-positive prefix set for
buck freewheel use. Treat it as unknown unless a profile explicitly says it is
valid for that role, and add a regression that `BAS316` does not pass as an
XL1509 freewheel diode.

### Medium: MOSFET Vds only checks positive drain-to-source overstress

- Code: `src/hardwise/validation/mosfet.py:158`
- Type: correctness bug / unsupported polarity model

`_validate_vds()` computes `vds = drain_voltage - source_voltage` and errors
only when `vds > vds_limit`. A high-side or P-channel style case with source at
`+150V`, drain at `GND`, and a 100 V rating can report PASS because `vds` is
`-150V`.

Recommended remediation: either encode supported MOSFET polarity/channel type
and reject unsupported cases, or compare the relevant magnitude/direction from
profile data. Add a negative-Vds regression.

### Medium: gate-driver output checks overclaim "gate load" from Q-prefix reachability

- Code: `src/hardwise/validation/gate_driver.py:153`,
  `src/hardwise/validation/gate_driver.py:187`,
  `src/hardwise/validation/gate_driver_helpers.py:25`
- Type: overclaiming risk / false PASS risk

`reachable_gate_loads()` accepts any Q-prefixed component directly or through
one resistor. The validator wording then says the output reaches a "gate-load"
component, but the algorithm does not know whether the reached Q pin is
actually the gate. The VS switch-node check similarly counts Q-prefixed devices
without verifying switch-node pins.

Recommended remediation: soften the wording to "Q-prefixed device reachable"
or require MOSFET profile/pin mapping before calling it a gate load or switch
node.

### Medium: `needs_review` profiles can still produce deterministic PASS

- Code: `src/hardwise/validation/component.py:11`,
  `src/hardwise/cli.py:847`, `src/hardwise/cli.py:1009`,
  `src/hardwise/agent/tools.py:321`
- Type: trust/provenance bug

`profile_candidates.py` correctly skips `review_status="needs_review"` drafts,
but direct CLI targets and agent targets load any `DatasheetProfile` and run
the validator. A one-off check with an L78 profile copied to
`review_status="needs_review"` still returned overall PASS.

Recommended remediation: direct validation should either refuse
`needs_review`, downgrade it to manual/WARN, or include review status in the
tool result so the agent/report cannot present it as fully L1 deterministic.

## Positive Checks

- Generic validation uses pin numbers, not names, which avoids common package
  pinout mistakes.
- MOSFET Vgs is correctly gate-to-source, and BJT reverse B-E handling is
  directionally correct for the current NPN scope.
- Report/UI wording is mostly careful about schematic-only evidence and does
  not claim PCB placement, routing, SI/PI, thermal, lifecycle, pricing, or PLM
  coverage.

## Verification

```text
uv run pytest tests/validation -q
87 passed

uv run pytest tests/report/test_component_validation_markdown.py tests/report/test_validator_ui.py -q
6 passed

uv run ruff check src/hardwise/validation src/hardwise/report
All checks passed
```

