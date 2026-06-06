# Hardwise MVP Definition

Hardwise MVP is a trusted pre-layout schematic review workbench.

It does not try to prove that an LLM can independently judge a complete
hardware design. It proves a narrower workflow: turn public EDA files,
schematic BOM identity, and public datasheet/profile evidence into a review
artifact where every surfaced object is registry-verified, every actionable
finding carries evidence, and every uncertain area stays in the reviewer's
hands.

## User Problem

Target user: hardware engineers preparing a schematic for Layout handoff.

Before Layout, reviewers need to quickly answer:

- Which components require attention before the review meeting?
- Which findings are deterministic issues, and which are only manual checks?
- Which datasheet page, netlist fact, rule, or BOM row supports each claim?
- Did the AI mention a real board object, or did it invent a refdes-shaped token?
- What feedback list can the team discuss and close item by item?

The costly work is not only electrical reasoning. It is the repeated switching
between schematic, BOM/netlist, datasheet, checklist, evidence notes, and review
feedback rows.

## Core Flow

1. Import a public schematic project or schematic netlist plus schematic BOM.
2. Build a trusted EDA registry for refdes, pins, nets, and BOM identity.
3. Match local public datasheet documents and reviewed structured profiles.
4. Run deterministic checklist rules and component-family validators.
5. Classify output into review actions:
   - `Must review`: deterministic ERROR/WARN or high-value checklist finding.
   - `Manual gap`: no ready profile, no retrieval evidence, or not enough context.
   - `Passed`: deterministic check completed without an issue.
6. Let Copilot explain only tool-backed facts: component context, validation
   result, topology, datasheet evidence, and unknown-refdes misses.
7. Export a workbench and feedback list that the engineer can use in the
   schematic review meeting.

## Page Structure

The MVP UI should open on the review workflow, not the internal architecture.

- Project summary: input files, component count, BOM match count, validated count,
  PASS/WARN/ERROR/manual counts.
- Review queue: issue-first list of `Must review`, `Manual gap`, and `Passed`
  rows, filterable by refdes/status/trust tier.
- Component detail: selected component identity, pins, nets, validation result,
  profile/document state, evidence tokens, and suggested review action.
- Copilot/evidence panel: answers questions by showing tool trace and trust tier;
  it explains deterministic results but does not replace them.
- Feedback list export: issue location/refdes, description, evidence, accept or
  reject field, reviewer feedback, and close status.

## MVP Scope

In scope:

- Public KiCad projects and public Allegro schematic netlist/PST plus schematic
  BOM fixtures.
- Registry-verified component, pin, net, and BOM identity.
- Local document index and public datasheet/profile evidence.
- Deterministic checklist rules for new-component candidates, capacitor voltage
  annotation, NC-pin handling, and reviewed datasheet facts.
- Deterministic component-family validation where a reviewed profile exists.
- L1/L2/L3 trust tiers:
  - L1 deterministic: Python rule or validator owns PASS/WARN/ERROR.
  - L2 grounded: this turn has page-level datasheet retrieval evidence.
  - L3 manual: no ready profile, no retrieval evidence, or insufficient context.
- Static HTML workbench, markdown/HTML report, and optional local Copilot panel.

## Non-Goals

- PCB layout review, `.brd`, boardview, placement, routing, or PCB geometry.
- SI/PI, EMC, thermal, SPICE, timing, or simulation closure.
- PLM, lifecycle, supplier risk, price, inventory, or production BOM governance.
- Company-internal hardware data, even sanitized.
- Full-board automatic correctness judgement.
- Automatic promotion of profile drafts into ready validators.
- Multi-agent decomposition, hosted account system, WebSocket streaming, or team
  collaboration features.

## Acceptance Criteria

The MVP is credible when:

- A public demo input opens a workbench with project summary, review queue,
  component detail, evidence, and manual-gap rows.
- Unknown refdes such as `U999` cannot be presented as a valid board object.
- Every report finding has a source token, or it is downgraded out of hard
  findings.
- At least one L1 deterministic issue is traceable from component to net/profile
  evidence.
- At least one L2 datasheet answer shows a `datasheet:<file>#p<N>` token.
- Manual/profile gaps are visible as reviewer work, not hidden as failures.
- Copilot answers expose tool trace and cannot overwrite L1 validator results.
- The exported report can be discussed item by item in a pre-Layout schematic
  review.
- `uv run pytest -q` and `uv run ruff check .` pass before claiming done.
