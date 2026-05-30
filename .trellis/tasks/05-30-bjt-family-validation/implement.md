# Implementation Plan

## Checklist

- [x] Verify one public NPN BJT datasheet source (prefer 2N3904) and exact page tokens for pinout, `Vebo`, and `Vceo` facts.
- [x] Add `data/datasheet_profiles/<bjt>.json` with `recommended.topology_family = "bjt"` and schema v2 pin rows.
- [x] Add Allegro fixture(s) under `tests/fixtures/allegro/`:
  - nominal low-side / emitter-ground case,
  - non-ground-emitter case that proves `Vbe = base - emitter`,
  - reverse B-E breakdown case where emitter is above base by more than `Vebo`.
- [x] Use `Net.voltage_hint` in all numeric `Vbe` / `Vce` tests, including PASS cases; do not rely on realistic `0.7 V` net names.
- [x] Add `src/hardwise/validation/bjt.py`, reusing MOSFET helper shape for pin lookup and WARN-on-unknown, and diode helper shape for one-direction reverse-voltage ERROR.
- [x] Add BJT dispatch branch in `src/hardwise/validation/component.py` using only `recommended.topology_family`.
- [x] Add `tests/validation/test_bjt.py` covering nominal PASS, reference-node PASS, floating WARN, reverse `Vebo` ERROR, `Vceo` ERROR/PASS as appropriate, and family-only dispatch.
- [x] Update `.trellis/spec/backend/validation-guidelines.md` to spell out that BJT `Vebo` / `Vceo` live in top-level `profile.abs_max`, while per-pin `limits` are for generic pin validators.
- [x] Update `docs/interview_qa.md`, `docs/learning_log.md`, and `docs/PLAN.md`.
- [x] Run `uv run pytest tests/validation/test_bjt.py -q`.
- [x] Run `uv run pytest -q` and `uv run ruff check .`.

## Live Result

- onsemi `2n3904-d.pdf` page 1 contains pinout (1 Emitter / 2 Base / 3 Collector) and max ratings (`VCEO=40 V`, `VEBO=6 V`).
- `uv run pytest tests/validation/test_bjt.py -q` -> 6 passed.
- `uv run pytest -q` -> 386 passed, 7 deselected.
- `uv run ruff check .` -> clean.

## Verification Commands

```bash
uv run pytest tests/validation/test_bjt.py -q
uv run pytest -q
uv run ruff check .
```

## Risky Files

- `src/hardwise/validation/component.py`: keep dispatch by `topology_family`; no part-number fallback.
- `data/datasheet_profiles/*.json`: do not add unverified datasheet evidence tokens.
- `src/hardwise/validation/bjt.py`: avoid adding generic three-terminal abstractions unless duplication becomes painful after tests are green.

## Stop-and-Ask Conditions

- The selected BJT datasheet lacks a clear reverse emitter-base (`Vebo`) or collector-emitter (`Vceo`) absolute max.
- Implementing a meaningful BJT check requires simulation, beta/current gain estimation, or resistor sizing beyond the planned minimal sanity checks.
- Supporting PNP would require separate polarity semantics; defer rather than silently widening the family.
- The only available profile facts would be synthetic or unattributed.
