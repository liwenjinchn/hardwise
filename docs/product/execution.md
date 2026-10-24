# Product diagnosis execution

Baseline: `9dbf6ff181080034b1660962d5cc43519e1008ad`, verified against origin/main on 2026-10-24.
Branch: `feat/review-trust-baseline`.

## Goal / Context / Constraints / Done when

- Goal: implement the reviewed Cadence-first schematic-review product baseline.
- Context: the accepted PRD prioritizes trustworthy limited checks, durable review records, then independent repeated use.
- Constraints: public/synthetic inputs only; preserve existing supported inputs; no push without authorization. No claims of production readiness from software tests.
- Done when: PRD A01–A14 and the M0–M3 gates have authoritative evidence, including actual Windows/Cadence export and independent peer use. External gates remain pending until observed.

## Status contract decision

Target contracts are in [PRD](prd-v1.md); phases in [Roadmap](roadmap-v1.md).
The existing wire status combines result and attention (`PASS/WARN/ERROR`). It will migrate to independent result, severity, evidence and reviewer-decision fields, across CLI, API, generated TypeScript, UI, export and evaluation. `UNKNOWN` must not silently map to PASS. Existing WARN records must not be guessed to mean FAIL or UNKNOWN during migration; require replay from original inputs or mark as legacy/needs review.

First patch prevents skipped passive checks from producing PASS within the existing interface: temporarily WARN with an explicit missing-data reason. This is an intermediate compatibility measure, not completion of the UNKNOWN contract. Terminal voltage inference remains heuristic until explicit confirmed rail/reference-domain facts are wired into the primary import flow.

## Work ledger

| Task | Status | Evidence / next work |
|---|---|---|
| T01 Baseline and counterexamples | In progress | Differential capacitor and missing-data regressions first; XL1509/output/lifecycle cases still to add |
| T02 Cross-surface result contract | In progress | UNKNOWN/NOT_APPLICABLE now round-trip across model, tools, SPA and exports; independent result/severity/evidence/reviewer axes and legacy provenance migration still pending |
| T03 Profile conditions and reviewed subset | Planned | XL1509 examples in original audit; independent field review pending |
| T04 Confirmed rail/reference facts and BOM conflicts | Planned | Do not promote network names or voltage_hint to reviewed facts |
| T05 Passive rule correctness | In progress | Two-terminal delta and missing-data handling; ranges/domains still pending |
| T06 Constrained formal output | Planned | Agent/tool and refdes counterexamples pending |
| T07 Persistence and dependency fingerprints | Planned | Restart/relevant-change gates pending |
| T08 Import and evidence UX | Planned | Actual target-EDA export and Windows walkthrough pending |
| T09 Independent evaluation | Planned | Frozen independently reviewed cases pending |
| T10 Two-round peer pilot | Planned | Human participants and public design selection pending |
| T11 AI profile drafts | Optional, not started | Only after reviewed schema and gold set |

## Verification record

Each implementation commit records exact commands and outputs below. Passing regressions do not close the remaining product gates.

### First implementation package — 2026-10-24

- Added 12 audit-driven passive terminal-stress cases; baseline: 11 failed / 1 passed.
- After the patch: full `PYTHONPATH=src uv run pytest -q`: **773 passed, 7 deselected**, 23.89 s. `uv run ruff check .`: passed. `git diff --check`: passed.
- Frontend: Vitest **70 passed**; contract/type/build passed; Playwright **8 passed** with the real backend and fake AI. No live model or Windows/Cadence installation was tested.
- CLI public fixture: 25 components / 22 evaluated / 3 profile gaps; component totals changed from 5/13/4 to **2/16/4**. R1/R2 lack terminal voltages; R76 lacks a power rating. The increase in WARN is explicit missing-data reporting, not three newly discovered physical defects.
- CLI HTML, Markdown and JSON were generated and the rendered HTML counts inspected. Existing XL1509 limitations remain; the generated report is a development artifact, not a product acceptance report.
- Local editable-package discovery was inconsistent after uv synchronization (ModuleNotFoundError during collection). Explicit PYTHONPATH to this checkout's src was used for the verified run and E2E server. Packaging root cause is not established; target-machine install remains an open gate.
- Next: implement independent UNKNOWN and empty-check semantics across all output surfaces; then replace heuristic rail authority with confirmed voltage/reference-domain facts. This package does not close M0 or M1.


### Second implementation package — 2026-10-24

- Resumed the interrupted status migration in the existing checkout; retained legacy WARN meaning. Added UNKNOWN and NOT_APPLICABLE throughout validation counts, agent tool schemas, API summaries, generated TypeScript, SPA, static HTML, Markdown/JSON and trust-dashboard aggregation.
- Empty check sets return UNKNOWN. PASS plus UNKNOWN returns UNKNOWN; ERROR and WARN retain attention priority. Only inapplicable checks return NOT_APPLICABLE. Neither UNKNOWN nor NOT_APPLICABLE creates a cleared task or increases PASS totals.
- Missing passive ratings/terminal inputs now produce UNKNOWN instead of the first package's temporary WARN. Public fixture: 25 components, 22 with reports, 3 profile gaps; component statuses **PASS 2 / WARN 4 / ERROR 4 / UNKNOWN 12 / NOT_APPLICABLE 0**. These are component rollups, not complete per-rule coverage or expert-reviewed accuracy.
- Fixed an additional SPA queue fallback that labeled every zero-task row as passed; labels now follow actual deterministic status. Added regressions for empty sets, mixed outcomes, JSON round-trips, legacy WARN, unknown manual tasks, offline export and inapplicable zero-task rows.
- Full regression: `PYTHONPATH=src uv run pytest -q`: **786 passed, 7 deselected**, 25.03 s. `uv run ruff check .` and `git diff --check`: passed.
- Frontend: `npm run test:unit`: **72 passed**. Build, contract drift check and TypeScript check passed with this checkout's absolute src path in PYTHONPATH. E2E: **8 passed**, 18.0 s, real backend with fake AI. An initial run had 7 passes and one page-load timeout; an unchanged full rerun passed. Cause of the initial timeout is not established.
- Ran `hardwise design-validator-ui` on the public fixture, generated HTML/Markdown/JSON and inspected the rendered HTML: UNKNOWN 12 is visible alongside PASS 2, WARN 4, ERROR 4 and NOT_APPLICABLE 0.
- Compatibility: validation index sidecar now declares `hardwise.validation_index.v2`; new summary counters default to zero for old callers. This is an intermediate five-status wire contract, not the final independent result/severity/evidence/reviewer model. It does not re-certify historical PASS records or migrate saved reviewer provenance.
- Remaining gates: confirmed rail/reference-domain facts, voltage ranges, reviewed profile conditions, formal AI output boundaries, restart persistence/fingerprints, real Windows/Cadence export and independent peer evaluation. No live model or physical target environment was used; M0/M1 remain open.
