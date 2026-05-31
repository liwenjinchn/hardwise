# C4c analog IC basic pin profiles

## Goal

Close the next C3/C4 ranked IC coverage gap by adding reviewed public basic
pin profiles for the analog IC group in the public-safe synthetic Allegro
fixture: `LMV358`, `LM393`, `INA180A1`, and `TLV9062`.

## Requirements

- Use only public datasheet facts and the public-safe synthetic Allegro fixture.
  Do not introduce private hardware data.
- Add `review_status="ready"` profiles for the four IC identities, with
  package pinout and supply/ground pins sourced from public Texas Instruments
  datasheets.
- Keep this as basic deterministic pin-level validation. U20-U23 may validate
  connectivity, supply rails, and ground pins; they must not validate amplifier
  behavior, comparator thresholds, current-shunt sizing, gain accuracy, output
  swing, bandwidth, stability, or PCB/layout details.
- Do not add a generic IC validator, op-amp validator, comparator validator, or
  current-sense validator in this slice.
- If pin categories need extension, keep it generic and limited to connected
  output-style pins; do not change `recommended.topology_family` dispatch
  semantics.
- Preserve C4/C4b LED and BJT behavior and existing deterministic findings.
- Keep the fixture narrative as public-safe synthetic Allegro, not a real public
  project board.

## Acceptance Criteria

- [x] U20-U23 match local ready profiles and produce deterministic validation
      rows.
- [x] `recommend-next-family` no longer ranks the IC group containing
      `LMV358`, `LM393`, `INA180A1`, and `TLV9062`.
- [x] Focused tests prove each public pinout profile and a nominal connected
      fixture path through generic pin validation.
- [x] CLI/ranking tests reflect the changed validated/manual counts without
      changing non-IC validation truth.
- [x] `docs/interview_qa.md`, `docs/learning_log.md`, and Trellis task records
      capture the C4c result and boundaries.
- [x] `uv run pytest -q`, `uv run ruff check .`, and a C4c smoke pass.

## Notes

- Public source URLs checked for profile facts:
  - https://www.ti.com/lit/ds/symlink/lmv358.pdf
  - https://www.ti.com/lit/ds/symlink/lm393.pdf
  - https://www.ti.com/lit/ds/symlink/ina180.pdf
  - https://www.ti.com/lit/ds/symlink/tlv9062.pdf
