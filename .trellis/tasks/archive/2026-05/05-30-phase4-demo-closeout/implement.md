# Implementation Plan

## Checklist

- [x] Confirm the exact runnable demo commands from existing CLI and fixtures:
  - KiCad hero track: `pic_programmer` review/agent evidence with `U3` / L78 / `datasheet:l78.pdf#p4`,
  - agent bridge evidence via `tests/agent/test_validation_bridge.py` or a small deterministic transcript,
  - Allegro complementary track: `design-validator-ui` HTML workbench generation from `mixed_controller_power_stage`.
- [x] Record that Phase 4 deliverable is reproducible artifacts, not a video/screencast.
- [x] Inventory human-facing docs before editing:
  - rewrite `docs/demo.md` / `docs/demo.html`,
  - refresh one entry page (`docs/index.html` or `docs/product-intro.html`),
  - update `docs/interview_qa.md` and `docs/jd_alignment.md` if stale,
  - explicitly label or intentionally leave historical pages (`docs/hardware-demo.html`, `docs/midpoint_review.html`, `docs/interview_narrative.*`) with rationale.
- [x] Update README links/copy so they point to the current Phase 4 story rather than stale V1.3 pages.
- [x] Update `docs/interview_qa.md` with a concise Phase 4 final-story answer.
- [x] Add a `docs/learning_log.md` entry for what Phase 4 proved or any closeout correction.
- [x] Add a `docs/PLAN.md` discharged Phase 4 audit-trail entry after verification.
- [x] Run focused commands for the demo artifacts.
- [x] Run `uv run pytest -q`.
- [x] Run `uv run ruff check .`.

## Live Result

- `uv run pytest tests/agent/test_validation_bridge.py -q` -> 6 passed.
- `uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003,DS001 --report-style component --output /tmp/hardwise-phase4-review.md` -> 29 findings, 121 components reviewed; U3 / DS001 cites `datasheet:l78.pdf#p4`.
- `uv run hardwise design-validator-ui tests/fixtures/allegro/mixed_controller_power_stage.net tests/fixtures/allegro/mixed_controller_power_stage_bom.csv --output /tmp/hardwise-phase4-workbench.html --index-output /tmp/hardwise-phase4-index.md --index-json /tmp/hardwise-phase4-index.json` -> 25 components, 4 validated, BOM matched 25, PASS/WARN/ERROR=1/0/3, manual=21.
- Browser QA on `http://127.0.0.1:8765/docs/demo.html` verified the Phase 4 hero, KiCad track, and Allegro track are present; mobile-width horizontal overflow was fixed.
- `uv run pytest -q` -> 386 passed, 7 deselected.
- `uv run ruff check .` -> clean.

## Spec Update Judgment

No `.trellis/spec/` update was needed. Phase 4 changed submission/demo narrative and fixed one stale agent-tool docstring; it did not introduce a new command/API contract, database schema, validator convention, or reusable coding pattern. The reusable lesson belongs in `docs/learning_log.md`, where it was captured as the two-track demo framing.

## Candidate Verification Commands

```bash
uv run pytest tests/agent/test_validation_bridge.py -q
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003,DS001 --report-style component --output /tmp/hardwise-phase4-review.md
uv run hardwise design-validator-ui tests/fixtures/allegro/mixed_controller_power_stage.net tests/fixtures/allegro/mixed_controller_power_stage_bom.csv --output /tmp/hardwise-phase4-workbench.html --index-output /tmp/hardwise-phase4-index.md --index-json /tmp/hardwise-phase4-index.json
uv run pytest -q
uv run ruff check .
```

Optional, not a default gate:

```bash
uv run hardwise query-datasheet "absolute maximum input voltage" --part-ref L7805 --persist-dir /tmp/hardwise-l78-chroma
uv run hardwise ask ...
```

## Risky Files

- `README.md`: keep it permanent and current, not a changelog.
- `docs/PLAN.md`: discharged entries should be audit trail only; do not rewrite durable decisions unless the work changes them.
- `docs/demo.md` / `docs/demo.html`: avoid stale metrics and avoid claiming private or live supplier data.
- `docs/*.html`: avoid blanket rewrites; triage current vs historical pages explicitly.
- `docs/interview_qa.md`: keep answers concise and evidence-backed.

## Stop-and-Ask Conditions

- Existing CLI cannot produce the required demo chain without new command surface.
- Any promising demo input would require company-internal hardware data.
- Verification reveals Phase 1/2/3 evidence is incomplete or contradictory.
- Showing BJT/MOSFET in the demo would require new fixtures, new parser behavior, or nontrivial profile assignment work.
