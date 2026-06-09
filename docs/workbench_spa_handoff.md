# Hardwise Workbench SPA Handoff

This handoff is for continuing the real React/Vite workbench from another
machine. It records the current product state, the visual target, the next
implementation sequence, and which feature ideas should or should not be added.

For the separate documentation consolidation pass, read
`docs/documentation_cleanup_handoff.md` before asking an agent to load broad
project context.

## Current State

The main branch currently contains the real SPA workbench, not only the static
prototype. The important user-facing path is:

```bash
uv run hardwise serve-workbench \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --fake-ai \
  --port 4314
```

Open `http://localhost:4314/`.

Expected fixture numbers:

| Metric | Expected |
|---|---:|
| Components | 25 |
| Validated | 22 |
| PASS / WARN / ERROR | 5 / 13 / 4 |
| Manual | 3 |

Current shipped behavior:

- Review is component-first: the left queue uses one row per refdes from
  `/api/workbench/state.queue`.
- Findings remains finding-first: it lists all review tasks from
  `/api/workbench/state.review_tasks`.
- Component detail fetches `/api/workbench/components/{refdes}`.
- The evidence column shows the selected component's grouped review tasks and
  chain-of-custody.
- Copilot still goes through `/api/workbench/chat`; unknown refdes must surface
  as `⟨?U999⟩`.
- Per-component prep packets exist at
  `/api/workbench/components/{refdes}/prep-packet?format=json|markdown`.
- Project-level prep packets exist at
  `/api/workbench/prep-packet?format=json|markdown`; the SPA Export page can
  preview and download the markdown package.

## Visual Reference

The visual target is the local high-fidelity prototype:

```text
/Users/liwenjin/designs/designs/hardwise/
```

Key files in that folder:

| File | Why it matters |
|---|---|
| `Hardwise.html` | Runnable reference prototype entry. |
| `theme.css` | Source of the blueprint/paper tokens, density, stamps, rails, and panel rhythm. |
| `views-review.jsx` | Reference Review workspace structure. |
| `ui.jsx` | Reference chips, trust badges, evidence rows, and shared primitives. |
| `data.jsx` | Mock data shape used by the prototype; useful for comparing intended hierarchy, not backend truth. |

For another computer, copy this folder as well as the repository. The exact path
does not have to match, but keeping the same path avoids rewriting handoff notes.
If only one thing can be copied, copy `Hardwise.html`, `theme.css`,
`views-review.jsx`, and a 1440x900 screenshot of the Review view.

Suggested transfer command:

```bash
rsync -a /Users/liwenjin/designs/designs/hardwise/ \
  <other-machine>:/Users/liwenjin/designs/designs/hardwise/
```

If the reference folder is unavailable, do not continue visual alignment from
memory. First recreate a reference screenshot and a current screenshot, then
compare them side by side.

## Visual Gap Audit

The current SPA is structurally correct but not visually finished. Treat it as a
functional alignment pass, not a final design pass.

Main gaps to close:

1. The screen still feels like a styled admin dashboard. The reference feels
   like a precise engineering review sheet.
2. Real backend data is shown too literally. The UI needs stronger summary,
   truncation, and hierarchy before showing raw evidence text.
3. The left queue is component-first, but rows are still too text-heavy. It
   should read as refdes, one main conclusion, status stamp, trust badge, and
   issue count.
4. The detail panel has the right content, but the component sheet needs tighter
   baseline alignment, smaller internal headings, and better separation between
   identity, verdict, pins, checks, and prep packet.
5. The evidence rail works functionally, but it does not yet feel like the
   reference chain-of-custody. Strengthen the vertical rail, node rhythm, guard
   note, and recommended action sequence.
6. Badges and buttons are too generic. Status badges should feel like small
   engineering stamps; icon buttons should be quieter and more square.
7. Typography needs another pass for Chinese/English/mono rhythm. Keep Chinese
   first, but make `F-001`, `L1`, evidence tokens, and refdes visually crisp.

## Visual Alignment Plan

Do this as a single focused visual pass before adding more product features.

1. Capture comparison evidence.
   - Reference Review, 1440x900.
   - Current SPA Review, 1440x900.
   - Current SPA Review, 760x900.
   - Optional: reference Import/Copilot/Findings if those pages will be touched.

2. Build a small token map before editing:

   | Reference concept | SPA target |
   |---|---|
   | Paper canvas / drafting grid | `frontend/workbench/src/styles.css :root` and `body::before` |
   | Status stamp | `.status-badge` plus queue/detail/evidence variants |
   | Trust badge | `.trust-badge` |
   | Queue row | `.queue-row`, `.queue-copy`, `.queue-side` |
   | Detail sheet | `.detail-panel`, `.detail-head`, `.identity-grid`, `.pin-table` |
   | Evidence rail | `.finding-chain`, `.evidence-list`, `.evi-node`, `.task-brief` |
   | Topbar/nav | `.topbar`, `.flow-nav`, `.project-pill`, `.mini-stats` |

3. Tighten the Review first.
   - Do not redesign every page at once.
   - Make the first screen look finished at 1440x900.
   - Keep the three-column ratio near `340px / 1fr / 360px`.
   - Preserve component-first behavior and component/detail/evidence sync.

4. Then carry the same primitives to Import, Parse, Copilot, Findings, and
   Export.
   - Reuse the stamp, chip, table, rail, and icon-button language.
   - Keep those pages simpler than Review; Review is the hero screen.

5. Verify with both visual and functional gates.
   - `npm --prefix frontend/workbench run build`
   - `uv run pytest tests/workbench/test_context.py -q`
   - `uv run pytest -q`
   - `uv run ruff check .`
   - Browser smoke at 1440x900 and 760x900.

Acceptance for the next visual pass:

- Review reads as an engineering review workspace, not a generic dashboard.
- Left queue shows one compact component row per refdes; Q12 appears once.
- Three columns are complete and non-overlapping at 1440x900.
- Narrow width has no horizontal overflow and evidence tokens remain readable.
- Clicking `Q12`, `U8`, and `U12` updates detail and evidence.
- Copilot still wraps `U999` as `⟨?U999⟩`.
- Prep packet buttons still work.

## Feature Backlog Review

Do not add features simply because they sound useful. Hardwise should stay
focused on review preparation and evidence organization, not automatic hardware
sign-off.

Recommended priority:

| Priority | Feature | Decision | Reason |
|---|---|---|---|
| P0 | Visual/information-architecture alignment | Do next | The product already has enough function to demo, but the screen does not yet look as convincing as the reference. |
| Done | Project-level Review Prep Packet | Implemented | Complements the shipped component-level prep packet with board overview, key groups, review focus areas, open questions, risk hints, and evidence tokens. Keep it working during visual alignment. |
| Done | Datasheet evidence locator | Implemented | `locate_component_evidence` finds bounded reviewed-profile evidence for EN pins, abs max, recommended application, decoupling, reset, boot, debug, bootstrap, power, and pin function. It is not broad datasheet chat or PDF search. |
| Done | Manual Gap -> L1 promotion scaffold | Implemented | Project packet now includes `profile_promotion_candidates`, and `/api/workbench/profile-gaps/{group_id}/promotion-packet` emits a human checklist plus `needs_review` draft command. `/api/workbench/profile-gaps/{group_id}/datasheet-candidates` can call the existing Datasheets.com adapter to prefill reviewable `ReviewStatus=candidate` document-index rows. It never writes `ready`, downloads approved PDFs, or changes deterministic verdicts. |
| Done | Module/power-tree summaries | Implemented | Project packet now includes `draft_summaries` for modules, key groups, candidate power/interface/clock-reset nets, and open questions, with uncertainty text that keeps them as review-prep draft context, not final electrical truth. |
| Defer | PLM, supplier, lifecycle, pricing, PCB/layout review, auto score, bug attribution | Do not add now | These widen the product beyond the schematic-review-prep node and weaken the trust story. |

## Implementation Boundaries

Keep these invariants while continuing:

- Do not change deterministic PASS/WARN/ERROR logic for visual work.
- Do not mix external risk hints into deterministic verdicts.
- Do not expose API keys or model credentials to the browser.
- Keep Refdes Guard visible and tested.
- Keep old static `design-validator-ui` and risk-hints paths working.
- Do not commit local screenshots unless they are intentionally added as docs
  assets.

## Useful Commands

```bash
git status --short --branch
uv run pytest tests/workbench/test_context.py -q
uv run pytest tests/report/test_validator_project_risk_hints.py tests/test_cli_validator_ui.py -q
uv run pytest -q
uv run ruff check .
npm --prefix frontend/workbench install
npm --prefix frontend/workbench run build
```

Serve the real SPA:

```bash
uv run hardwise serve-workbench \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --fake-ai \
  --port 4314
```

Open `http://localhost:4314/`, not `127.0.0.1`, if the in-app browser blocks
the loopback IP.
