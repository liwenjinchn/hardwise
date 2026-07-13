# Server Hardware Review Roadmap

Hardwise is not trying to become another automatic PCB layout system. The
durable product goal is narrower: a trust layer for server-hardware engineers
before Layout handoff, built around exported enterprise EDA evidence and public
datasheet/profile facts.

## External Landscape

The public landscape was rechecked on 2026-07-11 with Grok Search, then
cross-checked against current vendor documentation. The important correction is
that deterministic review rules alone are not a moat: Cadence and AI-native
tools already expose overlapping checks. Hardwise has to differentiate on the
export-first audit trail, cross-artifact completeness, and reproducible
calibration around Cadence/Allegro evidence.

Current AI hardware tools cluster around four product shapes:

| Reference | Public positioning | What Hardwise should not copy | Useful lesson |
|---|---|---|---|
| Cadence Allegro X | Native schematic integrity checks, ERC, EOS/MTBF analysis, and in-design analysis coexist with Allegro X AI placement/routing automation. Sources: [Allegro X platform datasheet](https://www.cadence.com/en_US/home/resources/datasheets/allegro-x-design-platform-ds.html), [Allegro X AI release](https://www.cadence.com/en_US/home/company/newsroom/press-releases/pr/2023/cadence-introduces-allegro-x-ai-accelerating-pcb-design-with.html). | Do not compete on native ERC/reliability breadth, placement/routing, or enterprise EDA integration. | Consume exported Cadence evidence cleanly and make the external audit boundary explicit. |
| Flux | Browser-native ECAD with an AI Design Review panel covering resistor power, pull state, capacitor voltage, availability, and layout checks; Flux says it blends deterministic algorithms with AI. Sources: [AI Design Review guide](https://www.flux.ai/docs/tutorials/copilot-use-cases/ai-design-reviews), [launch note](https://www.flux.ai/p/blog/introducing-the-ai-design-review-tab). | Do not claim that these check families are unique, or become a browser ECAD editor. | Trust must come from reproducible source tokens, stable registry joins, and explicit downgrade paths rather than model fluency. |
| Quilter | Automated PCB layout plus per-candidate Physics Rule Checks for user-defined constraints. Sources: [Quilter overview](https://docs.quilter.ai/), [PRC overview](https://docs.quilter.ai/physics-rule-checks-prcs/overview). | Do not promise schematic-to-fabrication automation, layout ownership, or physics validation. | Keep unlike coverage dimensions separate and show exactly what was or was not checked. |
| JITX | Local software-defined electronics: requirements and manufacturing rules become inspectable code, with generated designs, checks, and HFSS loops. Sources: [JITX product page](https://www.jitx.com/), [design constraints](https://docs.jitx.com/en/latest/essentials/physical_design/design-constraints.html). | Do not turn Hardwise into a code-defined hardware compiler or SI optimization loop. | Local, inspectable rules and measured feedback are stronger trust primitives than unconstrained AI prose. |

Across public design-review material, the repeated review axes are pin-by-pin
datasheet checks, PI, SI, EMI, DFM/DFA, thermal, BOM/document readiness, and
manufacturing handoff. Cadence/Capture review workflows also treat the schematic
PDF, ERC/DRC output, PST netlist, BOM, pin table, checklist, and review notes as
an evidence package before Layout handoff. Those are real concerns, but
Hardwise should only accept the subset that can be supported by pre-layout
schematic exports, BOM identity, Capture pin evidence, review-artifact metadata,
and public datasheet/profile tokens.

## Positioning

Hardwise should be described as:

> A Cadence/Allegro-first pre-layout review trust layer for server hardware:
> it turns exported netlist/PST + BOM + pin-table + public datasheet/profile
> evidence into registry-verified review queues and auditable Copilot answers.

The product wedge is not "the model can review hardware." It is that exported
project evidence is boxed inside a verifiable path that remains useful outside
the native authoring tool:

- Refdes and net references come from parsed EDA registries.
- BOM identity is joined to schematic topology by refdes.
- Pin-table facts can upgrade checklist items into deterministic L1 review
  tasks when they are exported from Capture.
- Review-artifact metadata, such as schematic PDF, ERC/DRC report, and checklist
  attachment names, can be tracked as package evidence without turning Hardwise
  into a signoff or PLM system.
- Datasheet/profile facts carry public source tokens.
- The UI separates deterministic findings, evidence-backed answers, and manual
  gaps instead of flattening everything into one model-written verdict.

This wedge remains a hypothesis, not a proven market moat. The strongest
countercase is Cadence's own schematic audit/reliability surface plus Flux-style
AI reviews. A public engineer calibration or pilot that finds no incremental
value in cross-artifact completeness should stop further rule expansion. A
native Cadence export-review module with the same deterministic evidence trail
would trigger the same re-evaluation.

## Current Baseline

Already shipped locally:

- Allegro/Telesis and PST intake, plus BOM matching.
- Workbench UI for project import, validation queues, evidence panel, and
  Copilot traces.
- Deterministic validators and seeded-defect smoke coverage.
- Six-lane evidence-package completeness shared by state/import/export, prep
  packets, the React workbench, and static snapshots; unlike units remain
  separate and the combined object has no electrical verdict.
- A versioned public/synthetic seeded-family matrix: 7 injected defects across
  capacitor, resistor, MOSFET, diode, I2C mux, and DCDC buck families, with
  recall 7/7 and zero unexplained new issues on the committed fixtures.
- Refdes Guard, Evidence Ledger, and L1/L2/L3 trust tiers.
- `design-validator-ui --ai-snapshot` offline demo and `serve-workbench
  --fake-ai` local server path.
- Datasheet/document candidate smoke path.
- KiCad review/ask path for public reproduction and regression.

This baseline means the next roadmap should compound the Cadence/Allegro review
path rather than add more KiCad parser surface.

## Trust Tiers

| Tier | Meaning | Acceptable sources |
|---|---|---|
| L1 deterministic | Hard finding, warning, pass, or checklist task produced by code from parsed EDA/BOM/pin/profile data. | Netlist/PST, BOM, Capture pin table, reviewed profile JSON, validator rule. |
| L2 evidence-backed | Copilot or report text cites retrieved or reviewed source evidence but does not create a deterministic verdict. | Public datasheet chunks with page tokens, reviewed profile evidence. |
| L3 manual gap | The system has a real object but lacks page-level source evidence or ready validator coverage. | Registry object, document-index candidate/coverage row, missing/not-configured reason. |

Roadmap work should move high-value L3 rows into L1/L2 one evidence family at a
time. It should not relabel weak evidence as a hard verdict.

## Roadmap Contract

Sections 1-5 are durable capability directions and product boundaries, not an
infinite active backlog. The finite release contract is the implementation-order
table at the end of this document. Conditional work such as a live Cadence
plugin, KiCad topology expansion, public/synthetic human calibration, or new
rule families does not count as unfinished until fresh public/user evidence
creates a new goal. Company-internal data remains prohibited. This prevents
"finish the roadmap" from silently expanding beyond the two-week
schematic-review MVP.

## Roadmap

### 1. Intake Hardening

Goal: make Cadence/Allegro export ingestion boring and trustworthy.

- Keep PST + BOM as the default product path.
- Add Capture pin-table import as a first-class evidence input, not a side
  artifact.
- Add a lightweight review-package manifest for schematic PDF, ERC/DRC reports,
  checklist exports, and review notes. Store names, hashes, source paths, and
  missing-artifact status; do not parse them into electrical conclusions yet.
- Preserve KiCad as public fixture/regression only.
- Add fixture diversity around server-style BOM groups: regulators, controllers,
  connectors, clocks, high-speed interfaces, power stages, and management ICs.

Done when: a fresh exported project produces a component group index, pin-table
coverage report, review-package evidence manifest, and explicit missing-evidence
rows without requiring code changes.

### 2. Server Review Rule Families

Goal: cover review work that a server hardware engineer actually checks before
Layout without needing PCB geometry.

Prioritize:

- Power tree and regulator pin/profile checks.
- NC / reserved / mode strap pin handling from Capture pin evidence.
- Clock/reset/enable pull state checks where schematic evidence is sufficient.
- Connector/interface pin-role consistency.
- Datasheet absolute-max and recommended-operating-range mismatch checks.
- BOM/profile/document coverage by group identity.

Defer:

- Full SI/PI simulation.
- Stackup optimization.
- Routing length/impedance/differential-pair verification.
- Thermal simulation.
- DFM/DFA signoff.

Done when: each family has a deterministic validator, fixture-backed tests,
evidence tokens, UI queue mapping, and a manual-gap path for unsupported cases.

MVP closure applies this gate to the shipped families represented by the
versioned six-family calibration matrix. Reserved/mode-strap expansion,
general clock/reset/enable policy, and any new server-specific family remain
evidence-triggered follow-ons; they are not assumed correct from net names or
scheduled without a public/synthetic fixture.

### 3. Evidence Workbench

Goal: turn "why did it say this?" into a first-class review interaction.

- Surface source tokens next to every task row.
- Let Copilot answer only by tool trace, with unknown refdes/net/profile paths
  visible.
- Show per-BOM-group profile/document state: reviewed profile, candidate
  document, not found, ambiguous, or manual.
- Make exportable review packets useful for a design review meeting, not just a
  demo page.

Done when: a reviewer can pick one Must Review row, inspect EDA facts,
datasheet/profile evidence, Copilot trace, and export the decision record.

### 4. Evaluation and Calibration

Goal: prove trust behavior before broadening claims.

- Expand seeded-defect tests by family.
- Track recall on synthetic defects separately from false-positive noise.
- Add manual calibration only with public/synthetic projects.
- Keep "no internal data" non-negotiable.

Done when: the README can state family-by-family smoke results without implying
expert-level accuracy on private designs.

Current MVP state meets this gate with 7/7 seeded recall and zero unexplained
new issues across six families. These are clean-fixture mutation deltas, not a
population false-positive rate or human gold-standard accuracy claim.

### 5. Integration Boundary

Goal: stay useful to enterprise EDA users without becoming a plugin project too
early.

- Keep local/offline exported-file workflow as MVP default.
- Improve Windows launch and project import ergonomics.
- Treat live Cadence/Allegro plugin integration as post-MVP until the exported
  path is stable and validated.

Done when: a user can run the workbench against exported files on a normal
machine, keep API keys local, and reproduce the report without opening Cadence.

The exported-file path is covered on macOS and Windows CI, with generated
Python/TypeScript contract checks and a local browser E2E suite. Live plugin
work remains post-MVP by design.

## Non-Goals

- Auto-placement, auto-routing, or schematic-to-fabrication automation.
- Code-defined hardware generation.
- SI/PI/thermal/DFM signoff.
- PLM lifecycle, pricing, inventory, or supplier-risk workflow.
- Native Cadence plugin as the default proof path.
- Using company-internal hardware data, even sanitized.

## Evidence-Readiness Release

The finite active roadmap is closed. The release combines two reviewer
questions that must remain separate:

1. **Is the input evidence package complete enough to review?** Six independent
   lanes cover netlist/PST registry, BOM identity, ready-profile plus
   deterministic-validation coverage, approved public documents, Capture pin
   evidence, and review-package artifacts. Every lane exposes source, metric
   units, next action, and trust boundary; there is no overall readiness score.
2. **Do the shipped deterministic families catch their intended mutations?** A
   versioned public/synthetic matrix reports per-family clean-baseline deltas.
   The release result is 7/7 seeded recall and zero unexplained new issues over
   six families, without presenting that result as expert accuracy.

Implementation order and closure evidence:

| Priority | Slice | Done when |
|---|---|---|
| Done | Pin-table evidence project summary/export | Import summaries, prep packets, static snapshots, and workbench JSON show loaded/missing state, accepted findings, rejected unknown refdes, and affected refdes without allowing rejected rows into the L1 queue. |
| Done | Review-package manifest polish | Manifest status remains shallow and provenance-only; missing required artifacts create manual-gap/package-status warnings, not electrical findings. |
| Done | P2 evidence-package completeness | State/import/export/prep/static/React surfaces share one six-lane contract; document upload is project-local, rejected rows cannot become green coverage, canonical tokens classify in the Evidence Ledger, and unlike units never mix. |
| Done | Family calibration matrix | Versioned matrix covers capacitor, resistor, MOSFET, diode, I2C mux, and DCDC buck; CLI/JSON expose per-family recall and unexplained deltas while preserving legacy headline fields. |

No active implementation item remains in this release. A new roadmap should be
opened only when public engineer calibration, a real exported-project pilot,
current Cadence capability changes, or a public regression fixture demonstrates
a concrete missing job. Keep these as explicit non-goals unless such evidence
changes the decision:

- Do not add more KiCad parser surface unless a public regression fixture needs
  it.
- Do not start layout automation, SI/PI simulation, thermal, DFM, PLM, or formal
  signoff flows.
- Do not parse schematic PDFs or ERC/DRC reports into electrical conclusions in
  manifest v1.

## Reviewer-Closure Release

A public mixed-controller project was re-imported through the live React
workbench and exercised as a hardware reviewer would use it: import, parse,
triage, component evidence, Copilot, findings, and export. The deterministic
core held, but the pilot exposed a product-level gap: Hardwise can identify and
explain review work, yet it does not fully close the reviewer decision loop.

This release is the finite roadmap opened by that pilot. It strengthens the
exported Cadence/Allegro trust boundary; it does not add a new EDA node or a new
validator family.

| Status | Order | Slice | Acceptance evidence |
|---|---:|---|---|
| Done | 1 | Sign-off evidence readiness | Every L1 task reports whether its cited local source is reproducible. Missing local datasheet sources block package sign-off readiness without changing PASS/WARN/ERROR. State, UI, prep packet, JSON/CSV export, and tests agree. |
| Done | 2 | Electrical/evidence dual axis | Queue and detail surfaces show deterministic electrical status separately from profile/document/package readiness. Filters and counts name their unit (`components` or `tasks`); a deterministic PASS never appears to become an electrical manual verdict because of a document task. |
| Done | 3 | Review-noise consolidation | Repeated tasks with the same BOM identity and check become one visible group with affected refdes. A root-cause deterministic ERROR suppresses or links weaker derived uncertainty for the same subject instead of presenting contradictory peers. Raw tasks remain exportable for audit. |
| Done | 4 | Reviewer decision lifecycle | Accept, waive, resolve, and reopen are backend-owned decisions keyed by stable finding key. Non-open decisions require a reason, survive browser reload, reconcile on a real deterministic re-run, and are included in JSON/CSV/annotation/prep exports without mutating the validator verdict. |
| Done | 5 | Handoff and launch ergonomics | JSON preview is a human-sized summary with full download retained; import controls distinguish current assets from files selected for the next run; launchers handle an occupied default port and support an explicit port override. Browser E2E covers the complete loop. |

Release closure requires all five rows to be implemented, `uv run pytest -q`
and `uv run ruff check .` to pass, frontend contracts/unit/build/E2E to pass,
and an independent browser run to demonstrate import, triage, decision,
re-run, Copilot guard, and export. The result report must include the commands,
measured task/component counts, remaining risks, and commit hashes.

## Public Evidence Pack Pilot

This bounded follow-on pins three official manufacturer PDFs for XL1509-12E1,
STM32G030C8T6, and EG2132. The PDF binaries stay in the gitignored local cache;
the reviewed manifest commits only source URLs, document revisions, safe local
aliases, and expected SHA256 values.

| Status | Slice | Acceptance evidence |
|---|---|---|
| Done | Three-source public manifest | Three official HTTPS PDF URLs, revisions, local aliases, and SHA256 values are reviewable in one small CSV. |
| Done | Fail-closed local reproduction | Real fetch reports 3 fetched / 0 skipped; changed bytes fail hash verification and unsafe local aliases cannot escape the datasheet cache boundary. |
| Done | Readiness regression | In an isolated checkout the mixed-controller gate moves from 16 affected L1 tasks / 11 missing tokens to 11 / 7. Electrical verdicts do not change. |
| Deferred | Power/reset/clock expansion | Whole-project readiness remains blocked, so the evidence-first gate does not authorize a new validator family yet. |

The measured source table, reproduction command, and remaining gap are in
`docs/public_evidence_pack_pilot.md`.
