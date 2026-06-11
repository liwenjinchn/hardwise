# Hardwise Workbench SPA Handoff

This handoff is for continuing the real React/Vite workbench from another
machine. It records the current product state, completed visual/offline work,
and which future feature ideas should or should not be added.

For the current documentation reading map, see `docs/docs_inventory.md`.

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

The public/offline backup uses the same SPA shell with baked snapshot data:

```bash
uv run hardwise design-validator-ui \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --ai-snapshot \
  --output /tmp/hardwise-copilot-workbench.html
```

Open the generated HTML directly. The file embeds workbench state, component
details, prep/export data, and audited Copilot responses; it does not require a
server or API key.

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
- `design-validator-ui --ai-snapshot` renders an offline single-file SPA
  snapshot instead of the older Python static workbench shell.

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

## Completed Visual / Offline Work

The focused visual pass is complete enough for the current demo. Review now
uses the engineering-sheet visual language from the reference: compact
component-first queue rows, status stamps, trust badges, detail sheet hierarchy,
and a chain-of-custody evidence rail. The queue overflow issue found during
browser review is fixed.

Acceptance evidence from the shipped pass:

- `npm --prefix frontend/workbench run build` passed.
- `uv run pytest -q` passed with 598 tests, 7 deselected, 1 warning.
- `uv run ruff check .` passed.
- Browser smoke covered 1440x900 and 760x900 without horizontal overflow.
- Clicking `Q12`, `U8`, and `U12` updated detail and evidence.
- Copilot still wrapped `U999` as `⟨?U999⟩`.
- Prep Packet preview opened for `Q12`.
- Offline `docs/hardware-demo.html` now contains `__HARDWISE_OFFLINE_SNAPSHOT__`
  and no `./assets` dependency.

Future visual work should be polish only: do not add another broad redesign
unless the demo target or product scope changes.

## Feature Backlog Review

Do not add features simply because they sound useful. Hardwise should stay
focused on review preparation and evidence organization, not automatic hardware
sign-off.

Recommended priority:

| Priority | Feature | Decision | Reason |
|---|---|---|---|
| Done | Visual/information-architecture alignment | Implemented | Review now uses the reference engineering-sheet language and the offline snapshot reuses the SPA shell. |
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
- Keep plain `design-validator-ui` and risk-hints paths working.
- Keep `design-validator-ui --ai-snapshot` on the SPA offline snapshot path.
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
