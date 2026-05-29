# Family-Level Datasheet Validation Workbench

## Goal

Move Hardwise from exact local profile matching toward a scalable device-family validation workflow. A new project should not fall back to zero validation just because its exact MPN is new. Hardwise should group BOM identities, find public datasheets, extract structured facts, classify device families, and run reusable family-level schematic checks with evidence.

The product target is close to the reference validator screenshot: a component-group list with document status, a validation summary, and detailed reports for components whose device family and datasheet facts are trusted enough to validate.

## Current Baseline

- `design-validator-ui <allegro-folder>` can now auto-detect PST input and select the best BOM candidate.
- The provided public Allegro project imports successfully:
  - `4010 components`;
  - `BOM matched=4010`;
  - `validated=0`;
  - `manual=4010`.
- HTML, Markdown, and JSON artifacts are generated even when profile coverage is zero.
- The remaining gap is not project import. The remaining gap is reusable datasheet/document coverage and family-level validation.

## Product Shape

The workbench should show components by BOM/device group, not only individual refdes rows:

- grouped refdes sample/count;
- normalized component identity;
- inferred device family;
- document status: `matched`, `no_result`, `ambiguous`, or `manual_needed`;
- validation status: `PASS`, `WARN`, `ERROR`, or `not_validated`;
- report detail for validated groups;
- explicit scope boundary when a group has a document but no trusted family validator.

## Architecture Direction

Data flow:

```text
BOM + schematic topology
  -> identity normalization
  -> component grouping
  -> public datasheet resolution
  -> datasheet fact extraction
  -> device family classification
  -> family-specific validation framework
  -> evidence-backed HTML/Markdown/JSON workbench
```

## Core Concepts

### Identity Normalization

Normalize BOM/device identity before matching or searching:

- prefer explicit MPN/manufacturer when available;
- detect library placeholders such as `GW_CAPACITOR`, `GW_RESISTOR`, `TestPoint`, and connector footprint-like names;
- for passives, keep value/package/rating as a group identity instead of pretending it is a datasheet MPN;
- preserve raw BOM fields and source lines for auditability;
- never fabricate an MPN from a refdes or footprint.

### Component Groups

Group by normalized identity and family:

- ICs and active devices: usually group by normalized MPN;
- passives: group by value/package/rating when a true MPN is absent;
- connectors/test points/mechanical: group as structural components and do not run electrical judgement by default;
- duplicates should share one document resolution and one extracted profile draft.

### Datasheet Resolution

Resolve public datasheets using normalized identity:

- search by MPN plus manufacturer when known;
- cache downloaded documents locally by stable hash or canonical identity;
- store match status and confidence;
- keep `ambiguous` results visible for human selection;
- never use private/company-internal documents unless the project explicitly treats them as public reproducible fixtures.

### Datasheet Fact Extraction

Extract reusable typed facts rather than one-off prose:

- pinout: pin number, name, function, category, alternate names;
- absolute maximum and recommended operating ranges;
- typical application topology;
- required/typical external components;
- package and pin-count evidence;
- table/page/source tokens for each extracted fact.

Extraction may be LLM-assisted, but validation must consume structured facts. Low-confidence extraction becomes `needs_review`, not PASS/FAIL evidence.

### Device Family Classification

Classify each group into a reusable family such as:

- buck regulator / switching regulator;
- LDO / linear regulator;
- half-bridge or gate driver;
- MCU / digital controller;
- op amp / comparator;
- diode / LED / Zener / TVS;
- BJT / MOSFET;
- memory / flash / EEPROM;
- clock / oscillator / buffer;
- connector / test point / mechanical;
- passive capacitor / resistor / inductor / ferrite.

The classifier must output `unknown` or `needs_review` when identity or datasheet evidence is weak.

### Family Validation Frameworks

Each family owns reusable checks. The exact datasheet only fills parameters.

Examples:

- Buck regulator:
  - VIN range versus schematic rail;
  - feedback topology and nominal output;
  - inductor presence/value range;
  - freewheel diode or synchronous topology expectations;
  - input/output capacitor presence and ratings when available;
  - enable pin legal range and polarity;
  - thermal/layout notes remain manual unless schematic-side evidence is enough.
- LDO:
  - VIN/VOUT/dropout;
  - required input/output capacitors and ESR notes;
  - EN/NC pin handling;
  - power dissipation estimate when rails/current are known.
- Gate driver:
  - VCC range;
  - HIN/LIN input drive;
  - HO/LO gate-load reachability;
  - bootstrap diode/capacitor topology and ratings;
  - VS/VB floating supply constraints.
- MCU:
  - VDD/VDDA/VBAT rails;
  - NRST/BOOT straps;
  - SWD/JTAG pin consistency;
  - crystal/clock pins if populated;
  - decoupling presence;
  - full alternate-function validation is out of first scope.
- Diode/LED/Zener/TVS:
  - polarity;
  - nominal role inferred from nets;
  - voltage/current/rating sanity when datasheet facts are available.
- Passives/connectors:
  - group and document coverage first;
  - run only simple schematic-side checks unless family-specific evidence exists.

## MVP Scope

The first implementation slice should not try to validate every component. It should establish the scalable pipeline:

1. Build a component-group index from BOM + design rows.
2. Normalize identities and mark placeholders separately from real MPNs.
3. Add document-resolution status fields to the project index and JSON sidecar.
4. Render a document coverage workbench similar to the reference screenshot.
5. Add one LLM-assisted or deterministic datasheet extraction draft path behind an explicit command.
6. Add one or two family validators that consume extracted structured facts.
7. Keep all unsupported groups visible as `not_validated` or `needs_review`.

## Non-Goals

- No PCB layout, `.brd`, boardview, placement, routing, current-loop geometry, SI/PI, or thermal layout checks.
- No PLM, lifecycle, pricing, stock, supplier risk, or live supplier availability.
- No fabricated datasheets, fabricated MPNs, or model-only electrical judgement.
- No attempt to validate every passive or connector deeply in the first slice.
- No company-internal data.

## Acceptance Criteria

- [ ] A real Allegro/PST folder can produce a grouped component/document coverage workbench.
- [ ] The workbench distinguishes real MPNs from library placeholders.
- [ ] At least one document group can be marked `matched` with a cached public datasheet.
- [ ] Ambiguous and no-result document matches are visible and do not block artifact generation.
- [ ] Extracted datasheet facts include source tokens and confidence/status.
- [ ] At least one family validator consumes extracted structured facts rather than a hand-written exact-MPN profile.
- [ ] PASS/WARN/ERROR appears only when both schematic evidence and datasheet facts are trusted.
- [ ] JSON sidecar exposes grouped component rows, document status, family classification, and validation status for later statistics.
- [ ] The provided public Allegro project remains importable and produces a useful artifact even before any group validates.

## Suggested Implementation Slices

### Slice 1: Grouped Coverage Index

Add grouped component identity rows on top of the existing per-refdes project index.

Ship gate:

- real project reports top groups such as capacitors, resistors, PCA9617ADP, MP5991, and other IC groups;
- placeholders are not treated as true MPNs;
- HTML/Markdown/JSON include group counts and refdes samples.

### Slice 2: Document Resolution Layer

Add a document index/resolver for public datasheet matches.

Ship gate:

- each group has `document_status`;
- matched documents point to cached/public sources;
- ambiguous/no-result/manual-needed states are explicit.

### Slice 3: Datasheet Fact Extraction Draft

Extract pinout and operating facts into a structured draft profile.

Ship gate:

- extraction output is JSON with evidence tokens;
- low-confidence fields are marked `needs_review`;
- no validation uses unsupported free-form prose.

### Slice 4: Family Classifier

Classify groups into device families from BOM identity and datasheet text.

Ship gate:

- classifier returns family, confidence, and reason;
- unknown families remain visible but not validated.

### Slice 5: First Generic Family Validator

Implement one family validator that consumes extracted facts.

Recommended first family:

- buck/switching regulator if the goal is screenshot-like power findings;
- gate driver if the goal is high-value motor/power-stage findings;
- MCU startup/debug if the goal is pin-strap and SWD correctness.

Ship gate:

- at least one real/public group produces evidence-backed PASS/WARN/ERROR without a hand-written exact-MPN profile.

## Cross-Machine Sync Notes

Track and sync task/design artifacts through Git:

- commit `.trellis/tasks/<task>/prd.md`, `implement.jsonl`, `check.jsonl`, and `task.json` when the task should travel between computers;
- commit project docs such as `docs/rolling_log.md` when the roadmap should be visible without Trellis;
- do not commit `.trellis/.runtime/`, `.trellis/.developer`, `.trellis/.current-task`, or machine-specific hook approval state;
- install Trellis/Codex hooks separately on each machine, then use Git pull/push for task and repo content.

