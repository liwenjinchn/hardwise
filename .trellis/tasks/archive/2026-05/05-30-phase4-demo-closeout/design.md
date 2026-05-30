# Phase 4 Demo Closeout Design

## Architecture Boundary

Phase 4 is a closeout/integration task, not a new validation-family slice. It should compose already-shipped capabilities:

1. Agent bridge: `Runner` + `run_component_validation(refdes)` exposes deterministic component validation to the tool-use loop.
2. Datasheet evidence: reviewed profile facts carry `datasheet:<file>#pN` tokens; real PDF ingest/search corroborates page-level provenance but does not dynamically author DS001 facts during `review`.
3. Static workbench: `design-validator-ui` renders project-level validation coverage and details from public fixture inputs.
4. Narrative docs: README, demo docs, interview answers, learning log, and PLAN audit trail describe the same proof.

No new product surface should be introduced unless the existing commands cannot express the demo chain.

The key framing correction is that Phase 4 is not one physical board flowing through every command. It is one trust backbone shown through two public input tracks:

- **KiCad hero track**: `pic_programmer` demonstrates registry verification, DS001/L78 evidence, refdes guard behavior, and the agent bridge if `Runner` can be configured with `U3 -> l78.json` without broad CLI changes.
- **Allegro workbench track**: `mixed_controller_power_stage` demonstrates the static multi-component validator UI and family coverage on the IR/PST+BOM path.

Trying to describe these as a single linear board sequence would be an overclaim because the current command surfaces consume different design formats.

## Data Flow

Recommended demo flow:

```text
KiCad hero track: pic_programmer
  -> parse registry / run review
  -> U3 = L7805 through schematic registry
  -> DS001 emits datasheet:l78.pdf#p4 from reviewed profile
  -> optional Runner wiring calls run_component_validation("U3")
  -> guarded explanation / report

Allegro workbench track: mixed_controller_power_stage
  -> parse/build IR Design + BOM identity
  -> local profile matching / explicit targets
  -> validate_component_against_profile()
  -> design-validator-ui
  -> static HTML workbench + markdown/json index sidecars

public L78 PDF / reviewed profile
  -> datasheet:l78.pdf#p4 token in profile/report
  -> optional ingest/query corroboration with [l78.pdf p4 part=L7805]
```

The story should keep the three identities separate:

- Refdes is the schematic join key (`U3`, `Q1`, `U12`).
- Profile identity is the component/datasheet model (`L7805`, `IRF540N`, `2N3904`).
- Evidence token is provenance (`datasheet:l78.pdf#p4`, `sch:...#U3`, `bom:...`).

## Contracts

- Agent validation output remains a structured tool response: `validated`, `no_profile`, `not_found`, or `not_configured`.
- Validator outputs remain `ValidationReport` / `PinValidation` / `ComponentValidation`; docs consume the shape, not ad hoc text.
- Demo docs must not imply the model independently judges hardware. It calls tools and explains deterministic results.
- Default verification cannot require `ANTHROPIC_API_KEY`; tests should rely on existing fake-client coverage or deterministic CLI commands.

## Compatibility

This task should preserve existing CLI behavior. If generated reports change, they should be intentional doc/demo artifacts rather than default command behavior changes. Existing README links and report paths should remain valid or be updated together.

Human-facing HTML docs must be triaged because several are historical pages:

| File | Phase 4 handling |
|---|---|
| `docs/demo.md`, `docs/demo.html` | Rewrite around the Phase 4 two-track trust-backbone story. |
| `docs/index.html` or `docs/product-intro.html` | Refresh one as the current entry page; avoid duplicating two separate current narratives. |
| `docs/interview_qa.md`, `docs/jd_alignment.md` | Update if stale against Phase 4 submission story. |
| `docs/hardware-demo.html`, `docs/midpoint_review.html`, `docs/interview_narrative.*` | Either mark as historical milestone / previous narrative or leave intentionally unchanged with rationale in implementation notes. |
| `docs/PLAN.html` | Regenerate only if the repository has an established generator and it is low-risk; otherwise keep `docs/PLAN.md` as source of truth. |

## Tradeoffs

- A real screencast is persuasive but hard to verify in git and can age quickly. A scripted demo with generated HTML/Markdown artifacts is easier to reproduce and review.
- Live API output proves the full agent loop but introduces environment risk. Existing fake-client tests prove dispatch; optional live command notes can supplement without gating completion.
- Public synthetic fixtures are acceptable for validation topology because the project rule forbids internal data and prioritizes reproducibility.
- Showing Phase 3 BJT in the main demo would make the arc neater, but only if a current fixture already supports it. Otherwise it is better kept as a tested Phase 3 milestone than forced into Phase 4.

## Rollback

Most Phase 4 changes should be docs and generated-demo command wiring. If a code change becomes necessary, keep it behind existing CLI contracts and rollback by reverting only that small integration change plus its tests.
