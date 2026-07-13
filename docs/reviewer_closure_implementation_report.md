# Reviewer-Closure Implementation Report

## Outcome

The reviewer-closure roadmap is complete for the public mixed-controller
Allegro fixture. Hardwise now separates deterministic electrical truth,
evidence reproducibility, and human review progress instead of compressing them
into one status. The live workbench supports project import, grouped triage,
backend-owned decisions, deterministic re-run, Copilot guardrails, and compact
handoff export.

This release stays inside the pre-layout schematic-review node. It adds no
layout automation, SI/PI/DFM solver, PLM workflow, live Cadence plugin, private
hardware data, or new validator family.

## Pilot evidence

The initial browser pilot imported the public
`mixed_controller_power_stage.net` plus BOM and document index, then exercised
Review, component detail, Copilot, Findings, and Export.

| Measure | Before / raw truth | Reviewer-closure result |
|---|---:|---:|
| Registry components | 25 | 25 |
| Deterministically validated components | 22 | 22 |
| PASS / WARN / ERROR components | 5 / 13 / 4 | unchanged |
| Raw audit tasks | 45 | 45, losslessly exported |
| Reviewer workload groups | 45 rows | 20 groups |
| Repeated 100 nF capacitor rows | 18 raw tasks | 1 group, 9 affected refdes, 9 derived tasks linked |
| Missing local datasheet sources | only per-token labels | 11 unique sources, 16 affected L1 tasks, sign-off readiness blocked |

## Implemented slices

1. **Sign-off evidence readiness** — classifies missing local sources across L1
   tasks and exposes a package-readiness gate in state, UI, prep packets, JSON,
   CSV, and annotations. It never rewrites PASS/WARN/ERROR.
2. **Dual-axis status** — queue filters and component badges use deterministic
   component status; document/profile readiness remains a separate evidence
   badge. Headers explicitly label component and raw-task units.
3. **Noise consolidation** — repeated BOM/check tasks become groups while raw
   tasks remain unchanged. Capacitor margin warnings, BJT rating follow-ons,
   and diode uncertainty link to their root task.
4. **Reviewer lifecycle** — accept, waive, resolve, and reopen require a reason
   for non-open states. Decisions are keyed by stable finding key, survive
   browser reload, reconcile after a real context rebuild, and enter exports.
5. **Handoff and launch ergonomics** — JSON preview is a compact summary while
   download retains the full ledger; Import distinguishes current assets from
   files selected for the next run; macOS and Windows launchers recover from an
   occupied default port and accept `HARDWISE_PORT`.

## External product check

Current vendor evidence reinforces the narrow position:

- Cadence Allegro X AI emphasizes placement, power-plane generation, and
  critical-net routing automation.
- Siemens owns native full-flow verification, SI/PI, and DFM surfaces.
- Flux already markets existing-EDA BOM/netlist upload, datasheet context, and
  AI design review.
- Quilter and JITX operate in autonomous layout or code-defined generation
  paradigms rather than an independent exported-review audit boundary.

Hardwise therefore competes on a Cadence/Allegro export-boundary trust layer:
input identity, deterministic findings, evidence readiness, stable reviewer
decisions, Refdes Guard, and an EDA-seat-independent review package.

Primary references:

- Cadence Allegro X AI product overview:
  https://resources.pcb.cadence.com/allegro-pcb-editor-videos/allegro-x-ai-product-overview
- Siemens PCB products: https://eda.sw.siemens.com/en-US/pcb/products/
- Flux Enterprise: https://www.flux.ai/p/enterprise
- Flux AI design reviews:
  https://www.flux.ai/docs/tutorials/copilot-use-cases/ai-design-reviews
- Quilter product: https://www.quilter.ai/product
- JITX detailed design checks: https://www.jitx.com/product/detailed-design-checks

## Verification evidence

Executed from the repository root unless noted:

```text
uv run pytest -q
756 passed, 7 deselected in 13.53s

uv run ruff check .
All checks passed!

cd frontend/workbench && npm run typecheck
generated-contract check + tsc passed

cd frontend/workbench && npm run test:unit
5 files, 70 tests passed

cd frontend/workbench && npm run build
1593 modules transformed; production static bundle generated

cd frontend/workbench && npm run test:e2e:only
8 browser tests passed
```

The browser E2E suite covers component navigation, unknown-refdes wrapping,
prep packets, decision persistence across reload and deterministic re-run,
compact JSON preview, multipart import, and 1440 px / 760 px overflow checks.

A separate in-app browser run also confirmed:

- `U1` displays electrical PASS independently from evidence review state.
- 45 raw tasks appear as 20 review groups.
- A nine-capacitor group can be waived with a reason.
- The waiver survives reload and deterministic re-run.
- Export shows 27 open plus 18 waived raw tasks for that group action.
- Sign-off readiness is blocked by 11 missing local sources affecting 16 L1
  tasks while electrical component totals remain 5 / 13 / 4.
- The JSON preview contains only the handoff summary; the download retains the
  full evidence ledger.

## Commits

- `c7becf0` — `feat(workbench): close reviewer decision loop`
- `d3402fa` — `fix(launcher): recover from occupied workbench ports`

## Remaining boundaries and risks

- Reviewer decisions persist for the lifetime of the local server and across
  browser reload/re-run. A future cross-machine/shared-review workflow would
  need an explicit decision-file or database contract; it is not implied here.
- The public fixture intentionally lacks 11 local datasheet sources. The new
  gate makes that limitation blocking and visible; this release does not copy
  or redistribute vendor PDFs.
- Windows launcher behavior is protected by static contract tests but was not
  executed on a Windows host in this macOS run.
- Grouping is deterministic and lossless, but future rule families must declare
  their root/derived relationship explicitly to avoid new peer-level noise.
