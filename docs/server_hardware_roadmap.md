# Server Hardware Review Roadmap

Hardwise is not trying to become another automatic PCB layout system. The
durable product goal is narrower: a trust layer for server-hardware engineers
before Layout handoff, built around exported enterprise EDA evidence and public
datasheet/profile facts.

## External Landscape

Current AI hardware tools cluster around four product shapes:

| Reference | Public positioning | What Hardwise should not copy | Useful lesson |
|---|---|---|---|
| Cadence Allegro X AI | AI-assisted feasibility, placement, routing, power plane generation, and layout optimization inside the Cadence ecosystem. Sources: [Cadence press release](https://www.cadence.com/en_US/home/company/newsroom/press-releases/pr/2023/cadence-introduces-allegro-x-ai-accelerating-pcb-design-with.html), [Allegro X AI overview](https://resources.pcb.cadence.com/product-overviews/allegro-x-ai-product-overview). | Do not compete on placement/routing automation or native enterprise EDA breadth. | The natural user environment is still Cadence/Allegro; Hardwise should consume its exports cleanly. |
| Flux | Browser-native ECAD with AI assistance for hardware design, component context, schematic generation, BOM help, and datasheet-aware project assistance. Sources: [Flux AI-assisted design](https://docs.flux.ai/tutorials/ai-for-hardware-design), [Flux copilot use cases](https://docs.flux.ai/tutorials/copilot-use-cases). | Do not become a browser ECAD editor or schematic generator. | AI help is acceptable when scoped as a junior engineer that must be reviewed. |
| Quilter | Physics-driven PCB placement/routing automation that works with existing Altium, Cadence, Siemens, and KiCad workflows. Source: [Quilter product page](https://www.quilter.ai/). | Do not promise schematic-to-fabrication automation or layout ownership. | The market values transparent constraint coverage and explicit "done vs needs review" status. |
| JITX | Software-defined electronics: requirements, constraints, stackups, and rules as code, with HFSS in the loop for high-speed optimization. Source: [JITX product page](https://www.jitx.com/). | Do not turn Hardwise into a code-defined hardware compiler or SI optimization loop. | Server/high-speed teams care about requirements, stackup, SI targets, and evidence loops; these can inform review checks without making Hardwise a simulator. |

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

The moat is not "the model can review hardware." The moat is that the model is
boxed inside a verifiable evidence path:

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

## Current Baseline

Already shipped locally:

- Allegro/Telesis and PST intake, plus BOM matching.
- Workbench UI for project import, validation queues, evidence panel, and
  Copilot traces.
- Deterministic validators and seeded-defect smoke coverage.
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
| L2 evidence-backed | Copilot or report text cites a source token but does not create a deterministic verdict. | Public datasheet chunks, document index rows, reviewed profile evidence. |
| L3 manual gap | The system has a real object but lacks enough source evidence or ready validator coverage. | Registry object + missing/not-configured reason. |

Roadmap work should move high-value L3 rows into L1/L2 one evidence family at a
time. It should not relabel weak evidence as a hard verdict.

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

### 5. Integration Boundary

Goal: stay useful to enterprise EDA users without becoming a plugin project too
early.

- Keep local/offline exported-file workflow as MVP default.
- Improve Windows launch and project import ergonomics.
- Treat live Cadence/Allegro plugin integration as post-MVP until the exported
  path is stable and validated.

Done when: a user can run the workbench against exported files on a normal
machine, keep API keys local, and reproduce the report without opening Cadence.

## Non-Goals

- Auto-placement, auto-routing, or schematic-to-fabrication automation.
- Code-defined hardware generation.
- SI/PI/thermal/DFM signoff.
- PLM lifecycle, pricing, inventory, or supplier-risk workflow.
- Native Cadence plugin as the default proof path.
- Using company-internal hardware data, even sanitized.

## Next Concrete Slice

The next highest-leverage slice is Capture pin-table and server-review coverage:

1. Normalize Capture pin-table import as a named evidence source.
2. Add a review-package manifest for schematic PDF, ERC/DRC, checklist, and
   notes artifacts so the workbench can say which required evidence is present
   or missing.
3. Map pin-table facts into L1 review tasks for NC/reserved/mode pins.
4. Add one server-style fixture family where pin evidence changes the review
   queue.
5. Update workbench/export text so the reviewer can see exactly which row came
   from netlist, BOM, pin table, profile, or datasheet evidence.

This keeps Hardwise pointed at the gap competitors leave open: auditable
pre-layout review trust, not layout automation.

## Next Implementation Order

Pin-table evidence summary is now shipped: workbench JSON, import summaries,
project prep packets, static snapshots, and CLI output show loaded/missing state,
accepted findings, rejected unknown refdes, and affected refdes without allowing
rejected rows into the L1 queue. The next development round should move to
review-package manifest polish, then a combined evidence package completeness
dashboard.

Recommended sequence:

| Priority | Slice | Done when |
|---|---|---|
| Done | Pin-table evidence project summary/export | Import summaries, prep packets, static snapshots, and workbench JSON show loaded/missing state, accepted findings, rejected unknown refdes, and affected refdes without allowing rejected rows into the L1 queue. |
| P1 | Review-package manifest polish | Manifest status remains shallow and provenance-only; missing required artifacts create manual-gap/package-status warnings, not electrical findings. |
| P2 | Evidence package completeness dashboard | Workbench shows netlist/PST, BOM, pin table, document index/profile, and review-package coverage together with trust-tier wording. |

Keep these as explicit non-goals for the next round:

- Do not add more KiCad parser surface unless a public regression fixture needs
  it.
- Do not start layout automation, SI/PI simulation, thermal, DFM, PLM, or formal
  signoff flows.
- Do not parse schematic PDFs or ERC/DRC reports into electrical conclusions in
  manifest v1.
