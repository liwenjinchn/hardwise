# Phase 4 end-to-end demo closeout

## Goal

Close DR-011 Phase 4 by producing a reproducible end-to-end demo narrative: agent validator bridge, datasheet-cited finding, HTML workbench, and submission-facing docs.

## Confirmed Facts

- `docs/PLAN.md` Phase 4 calls for an end-to-end demo and narrative: agent review -> validator call -> datasheet-cited finding -> HTML workbench, with `interview_qa.md` and resume material updated.
- DR-011 Phase 1 is already implemented: `run_component_validation(refdes)` exists as the fifth agent tool, `Runner` accepts an IR `design` plus explicit `validation_targets`, and `tests/agent/test_validation_bridge.py` proves the model loop dispatches into `validate_component_against_profile()`.
- DR-011 Phase 2 is already implemented: `data/datasheet_profiles/l78.json` carries reviewed `datasheet:l78.pdf#p4` tokens, `ingest-datasheet` can extract the public ST L78 PDF into chunks, and the docs now describe the two-line evidence model instead of overclaiming runtime RAG extraction.
- DR-011 Phase 3 is complete per the user and repository evidence: `validation/bjt.py`, `data/datasheet_profiles/2n3904.json`, fixture tests, learning log, interview Q&A, and the `PLAN.md` discharged item are present.
- Existing demo docs already include `docs/demo.md`, `docs/demo.html`, and README demo links, but they predate the final DR-011 Phase 1/2/3 closure and may not tell one continuous Phase 4 story.
- The repository currently has two input tracks, not one board that supports every surface:
  - KiCad agent/review track: `pic_programmer` is the public KiCad project used by `review` / `ask` style flows and has `U3 = L7805` evidence through DS001.
  - Allegro workbench track: `mixed_controller_power_stage` is the fixture used by `design-validator-ui` and shows multiple deterministic validation families in one static UI.
- No current public fixture is both a KiCad project and an Allegro netlist+BOM project, so Phase 4 must not claim that one physical board drives every demo artifact.
- `docs/demo.md` still speaks in the older V1.3 language around MPQ8626 / PCA9548A, 4010 components, and a `<public-allegro-folder>` placeholder. That layer needs deliberate triage, not light touch copy edits.
- The hard boundary remains pre-Layout schematic-side validation with public data only. No company-internal hardware data, PCB geometry, boardview, supplier/PLM/lifecycle/pricing, account backend, or simulation scope is allowed.

## Requirements

- Produce a reproducible Phase 4 artifact package, not a video/screencast file.
- Frame the demo as one trust backbone across two public input tracks:
  - hero track: `pic_programmer` KiCad agent/review loop for registry -> validator bridge -> real L78 datasheet token -> guarded explanation/report;
  - complementary track: `mixed_controller_power_stage` Allegro workbench for project-level multi-family validation UI.
- Demonstrate the agent bridge in the story: an agent/tool loop can call `run_component_validation(refdes)` and receive structured PASS/WARN/ERROR with evidence tokens. The preferred hero is `U3` on `pic_programmer` with `data/datasheet_profiles/l78.json` if the existing command wiring can support it without new product surface.
- Demonstrate datasheet-cited evidence honestly: at least one finding or validation result cites a reviewed `datasheet:<file>#pN` token, and the docs distinguish profile-token evidence from independent PDF/Chroma corroboration.
- Demonstrate the HTML workbench path: `design-validator-ui` writes a local static workbench plus index sidecars from the public Allegro fixture.
- Triage human-facing docs before editing so submission links do not tell contradictory historical stories.
- Update submission-facing narrative docs so README/demo/interview/JD material all describe the same narrow proof, or explicitly label older pages as historical milestones.
- Keep all acceptance evidence runnable locally with `uv run` and no live API requirement in default verification. Live MiMo/API evidence may be referenced only as optional/contextual.

## Acceptance Criteria

- [ ] The demo docs explicitly state that Phase 4 uses one trust backbone across two public input tracks, not one board pretending to cover both KiCad and Allegro command surfaces.
- [ ] The hero KiCad track shows the core chain: registry object -> deterministic validator or DS001 rule -> real `datasheet:l78.pdf#p4` evidence token -> guarded agent/report explanation.
- [ ] The complementary Allegro track shows `design-validator-ui` producing a static HTML workbench and sidecars from public fixtures.
- [ ] A docs inventory is captured in the implementation notes: `docs/demo.md` / `docs/demo.html` rewritten; one entry page (`docs/index.html` or `docs/product-intro.html`) refreshed; `docs/interview_qa.md` and `docs/jd_alignment.md` updated if stale; historical pages explicitly labeled or left out with rationale.
- [ ] `docs/interview_qa.md` gains a Phase 4 answer/update that explains the final end-to-end story without overstating autonomous hardware judgement.
- [ ] README and/or `docs/demo.md` are current with the final Phase 4 commands, outputs, and boundaries.
- [ ] `docs/PLAN.md` gets a discharged Phase 4 entry once implementation and verification pass.
- [ ] `docs/learning_log.md` records what Phase 4 proved or any closeout surprise discovered.
- [ ] Verification includes `uv run pytest -q` and `uv run ruff check .`; any optional slow/live commands are clearly labeled.

## Out of Scope

- New validator family work beyond already-completed BJT.
- New parsers, schematic net inference, PCB/boardview/placement/routing, simulation, supplier/PLM/lifecycle/pricing, GitHub Action packaging, hosted app state, or account/quota features.
- Free-form model hardware judgement. The model may explain structured tool/validator output; it must not invent refdes, profiles, or evidence.
- Using private or company-internal hardware data, even sanitized.

## Nice To Have

- If a current public fixture already exposes a BJT/MOSFET refdes without new parser or profile-matching work, the demo may mention the Phase 3 family through `run_component_validation`. Do not widen Phase 4 to hunt for new hardware examples; BJT is already proven by its own tests and audit trail.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
