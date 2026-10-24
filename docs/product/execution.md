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
| T02 Cross-surface result contract | In progress | Independent result/severity/evidence fields now span rules, tools, projections, UI and exports; legacy records require replay. Full candidate-set coverage and dependency/version history remain open |
| T03 Profile conditions and reviewed subset | In progress | XL1509 source-audited and quarantined; relative pin/supply schema and confirmed-envelope evaluator added. Full conditional inductor lookup, independent approval and 5–10 profile subset pending |
| T04 Confirmed rail/reference facts and BOM conflicts | In progress | Explicit per-net DC envelopes accepted by CLI/import; passive and MOSFET/NPN terminal DC checks consume confirmed ranges/common reference/mode. Other profile families, graphical confirmation and BOM conflicts pending |
| T05 Passive rule correctness | In progress | Confirmed interval DC stress, missing-data and reference/mode checks implemented for generic capacitor/resistor rules; profile-family and broader operating-condition gates remain |
| T06 Constrained formal output | In progress | Chinese/long refdes guards, no-tool prose suppression and explicit unverified-chat boundary added; arbitrary parameter/unit/condition semantic verification remains open |
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


### Third implementation package — 2026-10-24

- Added a strict portable voltage-facts document: exact net/reference identities, DC operating mode, V units, finite optional min/typ/max, source, explicit confirmation and confirmer. Duplicate net/mode or foreign-net records fail atomically. Typical-only/unconfirmed records remain usable metadata but cannot establish a passing envelope.
- Generic capacitor/resistor stress now requires two confirmed terminal ranges in the selected mode and a shared reference. Computes conservative interval maximum delta; same-net common mode does not produce differential. Missing references/ranges and unconfirmed net-name/voltage_hint guesses return UNKNOWN. Zero-ohm links never establish passing power margin.
- Wired the input through `design-validator-ui` and `serve-workbench --voltage-facts`, the live Import upload, deterministic reruns, API/index JSON, fact-table Markdown and offline React state. Current source/reference/range/confirmation records are visible on the Import page; added Chinese stress explanations.
- Added a public/synthetic bipolar-DC example. A 16 V capacitor across confirmed +12/-12 V is ERROR at 24 V; without the document the comparison is UNKNOWN. This is an explicit synthetic premise, not a measured design.
- The seeded capacitor benchmark now carries an explicit synthetic 3.3 V input file in its matrix/workspace and keys clean baselines by that input. Retains **7/7** detections and **0** unexpected differential findings; this remains a regression metric, not overall false-positive accuracy.
- Verification: full `PYTHONPATH=src uv run pytest -q`: **814 passed, 7 deselected**, 22.40 s; Ruff and diff whitespace checks pass. Frontend **74** unit tests, contract/type/build pass; E2E **9 passed**, 16.8 s, including actual upload, 24 V error display, rerun and retained source records. Used absolute checkout PYTHONPATH for frontend's backend subprocesses, as previously documented.
- Ran static snapshot generation and `serve-workbench --voltage-facts --fake-ai --dry-run` on the synthetic example. Generated white React offline examples and inspected the rendered main sample. Corrected the earlier user-facing sample that had inadvertently used the legacy dark HTML renderer: CLI's `--ai-snapshot` uses the current light React UI; ordinary static rendering still uses the legacy template. No frontend redesign was performed.
- Boundaries: only generic passive stress consumes these confirmed facts so far. Other profile-family validators still use legacy inference; A01/A04/A05 as whole-product gates are NOT closed. Input facts do not independently certify parsed BOM ratings, datasheet fields or physical conditions. Graphical confirmation, new fact-token source locators, history/fingerprint invalidation and cross-restart persistence remain open. In particular rerun reconciliation still uses existing stable keys, not full fact fingerprints; no external release gate is claimed.
- Next: finish the independent result/severity/evidence contract and remove heuristic authority from profile-family checks; add review-history persistence and per-finding dependency invalidation rather than reusing old decisions after relevant changes. Windows/Cadence and peer-use gates still require external evidence.


### Fourth implementation package — 2026-10-24

- Implemented `hardwise.assessment.v1`: PASS/FAIL/UNKNOWN/NOT_APPLICABLE result, ERROR/WARNING/INFO severity, SOURCE_FACT/DERIVED/HYPOTHESIS evidence kind, rule version, review/migration flags, retained legacy status and required inapplicability reason. `status` is a derived compatibility alias for checks; new producers explicitly set current result/severity.
- Audited the WARN branches rather than using one bulk semantic mapping. Missing/unproven facts become UNKNOWN; actual recommendation/policy violations are FAIL+WARNING. Above-range buck-inductor classification requires a resolved path; an ambiguous path remains UNKNOWN. Unknown severity ERROR remains distinct from a demonstrated FAIL.
- Migrated pin/component/net producers, component rollups, tool results, detail/queue/task projections, white React check/evidence displays, generated contracts, Markdown, legacy static HTML and analytics. Human decisions remain separate; an API/export regression proves a waived UNKNOWN remains UNKNOWN with unchanged severity.
- Status-only historical records retain the original but become unassessed/needs review until replay. Trust dashboard no longer trusts stored historical PASS totals: recomputes from canonical check records and keeps historical counters separately. V3 sidecars declare the changed contract. Dashboard report availability is labeled separately from check coverage.
- Prevented unreviewed profiles from certifying their individual checks. Corrected missing inductor/ferrite current-rating parse records from PASS to UNKNOWN; this does not claim a current/saturation model exists.
- Published explicit emitted-record denominators, not a fabricated full-board candidate count. Public fixture component rollup: **1 PASS / 0 WARN / 4 ERROR / 17 UNKNOWN**, 3 profile gaps. Emitted checks: **155 = 116 PASS + 9 FAIL + 30 UNKNOWN + 0 NOT_APPLICABLE**. Legacy records needing replay in this fresh run: 0. The former 4 WARN components lacked proof; the former extra passive PASS lacked a current rating. No new physical defects are claimed from these count changes.
- Verification: full `PYTHONPATH=src uv run pytest -q`: **838 passed, 7 deselected**, 39.05 s; Ruff and diff whitespace checks pass. Frontend **77** unit tests, contract/type/build pass. E2E **10 passed**, 19.9 s, including independent result/severity display plus prior import, rerun, export and responsive checks. Public CLI snapshot/index generation and seeded benchmark were exercised: **7/7** expected cases, **0** unexpected differential issues. No paid/live model or target EDA was used.
- Reopened the generated light React sample in the in-app browser, selected R1 and verified result/severity fields in its accessibility tree; viewport screenshot retains the current white UI. Desktop/760 px workflows were separately verified by Playwright. The narrow Codex pane screenshot is not a claim of complete mobile UX acceptance.
- Remaining gates: T03 reviewed profile subset/conditions and XL1509 corrections; T04 removal of heuristic voltage authority from remaining families and input conflict handling; full candidate-set inventory; T06 formal AI boundaries; T07 persistence and dependency invalidation; actual Windows/Cadence and independent peer evidence. The complete product goal and M0–M3 remain open.


### Fifth implementation package — 2026-10-24

- Rechecked XLSEMI's Rev 2.6 PDF and locally hashed the existing audit copy: `d0226589787aa1ec629f0a1365aec4e017799ae79594891fa48f7733b4c1ebc2`, matching the public document index. Source pages 4/8 justify relative pin limits and conditional inductor selection; detailed review record is `xl1509-source-audit.md`.
- Removed XL1509 EN's incorrect fixed 45 V limit and the unconditional 68–150 uH range. Added typed target/supply/ground-pin relations with package, source URL, revision, hash and page. The 12 V variant's feedback upper bound is likewise represented relative to VIN. Exact identity/package, same selected mode, confirmed finite envelopes and matching ground reference are required; unsupported conditions remain UNKNOWN.
- Confirmed EN24 V/VIN12 V produces a candidate relation FAIL; EN0 V/VIN12 V passes the limited DC relation. Overlapping ranges remain UNKNOWN without correlation assumptions. Old scalar pin PASS is not allowed to certify a relation-controlled pin. None of this assesses transient or full-device functionality.
- Quarantined the actual XL1509 profile (`needs_review`), rather than self-approving the correction. Primary auto-matching excludes it from executable targets and shows an explicit Chinese quarantine reason plus its blocked candidate path. Direct profile reports keep observations/metadata but cannot certify electrical PASS/FAIL until approval. Reviewed test-only in-memory copies exercise evaluator integration; they never write READY to the actual profile.
- Inductor rules now honor an explicit operating-condition requirement: 33 uH is no longer rejected by a global 68 uH bound. Without confirmed maximum input/load/output conditions the value comparison stays UNKNOWN. Full conditional table execution is NOT complete; topology-error predicates remain separately regression-tested. Retained raw missing-inductor/diode counterexamples instead of deleting those tests.
- Fresh public sample: **21 report-bearing components, 4 manual/profile gaps; 1 PASS / 0 WARN / 3 ERROR / 17 UNKNOWN**. Emitted checks **145 = 108 PASS + 7 FAIL + 30 UNKNOWN**. The drop in reported errors follows quarantine of an untrusted profile, not a claim that the physical circuit was fixed. Some legacy expansion suggestions can still list this gap; they are not authority to reapprove it.
- Verification: full `PYTHONPATH=src uv run pytest -q`: **859 passed, 7 deselected**, 22.39 s; `uv run ruff check .` and `git diff --check` pass. Frontend **77** tests and contract/type/build pass. E2E **10 passed**, 18.3 s. Added **21** source-condition/quarantine cases. Public CLI regenerated white React HTML plus Markdown/JSON; live-import model regression and browser screenshot show U12's explicit quarantine message.
- Browser preview's prior local HTTP process had stopped; verified connection refusal, restarted the local-only output server, then obtained a fresh preview tab after the old error-page tab could not navigate. Fresh page/screenshot confirmed white UI and quarantine reason. No network/security settings changed.
- Still open: independent engineering approval, 5–10 reviewed profiles, complete operating-condition entry/lookup, remaining family voltage authority, formal AI boundaries, durable review state/fingerprint invalidation and Windows/Cadence/peer gates. This package makes T03 progress but does not close A05/A06 as production acceptance.


### Sixth implementation package — 2026-10-24

- Addressed the identity portion of A08 without changing the accepted product direction or the white React frontend. Baseline counterexamples reproduced **8 failed / 19 passed**: Chinese-adjacent identifiers, long numbers, DDR terminology and direct pin exemptions.
- Refdes scanning now uses ASCII identifier boundaries and unrestricted ASCII digits. Existing complete net/part identifiers are not partially rewritten. Real registry identities remain intact; missing objects receive the existing unverified marker, idempotently.
- Ordinary DDR2–DDR5 technical words remain readable; explicit object contexts and tool-trace `refdes` fields still require registry membership. Common component-prefix tokens cannot hide behind direct `pin` wording. Raw tool input is not changed by display sanitization.
- Added **17** cases including an actual Runner final-text regression. Focused guard/Runner suite: **43 passed**. Full `PYTHONPATH=src uv run pytest -q`: **876 passed, 7 deselected**, 21.72 s. Ruff and whitespace validation passed. No frontend implementation or data-contract change, paid model call or physical EDA execution in this package.
- This does not certify arbitrary designator grammars or semantic correctness of model prose. Verified refdes with fabricated parameters, quoted-property/unit/condition checks and zero-tool sign-off assertions remain open. Formal report generation must continue from structured deterministic records; T06/A08 and M0–M3 remain incomplete.


### Seventh implementation package — 2026-10-24

- Separated model explanations from formal deterministic assessment records. `RunResult.response_kind` and the serialized chat contract distinguish model explanation, insufficient evidence and offline notice; `claim_verification` is fixed to `unverified`. White React messages do not inherit the welcome's former L1 badge. Per-tool trust labels still describe tool sources, not prose correctness.
- Runner marks usable results from server-dispatched tool payloads. Zero tools, unknown tools, execution errors and unconfigured tools cannot unlock model prose: a fixed no-new-assessment message is returned instead. Structured negative lookups remain usable lookup facts. Workbench normalization enforces the same boundary; no regex-based sign-off truth guarantee is claimed.
- Removed the workbench trace fallback that borrowed profile tokens for a tool that returned none. Only the current call's actual evidence is eligible for token-provenance matching. Backtick-wrapped source tokens and EV tokens are audited/displayed consistently; matching token chips explicitly do not certify property/value/unit/conditions.
- Added 12 backend regression cases. Seven adverse no-tool/error/unconfigured prose cases reproduced unsafe output before implementation; a negative-lookup case pins the valid explanatory path. API regressions use an actual Runner and real validation dispatch: model prose claims `U3 900 V / PASS / approved profile / accepted risk` with a genuine returned datasheet token, but full workbench state, profile JSON and CSV export remain identical before/after. Such prose is still displayed as unverified explanation; it has not been semantically certified or parsed into a formal finding.
- Final full `PYTHONPATH=src uv run pytest -q`: **888 passed, 7 deselected**, 34.78 s while frontend checks ran concurrently. Ruff and diff whitespace checks pass. Frontend **83 passed**; generated contract check, TypeScript and production build pass. E2E **10 passed**, 17.0 s, real backend/fake AI, including explanation labeling and prior import/rerun/export/responsive paths. An initial typecheck caught missing required serialized fields in handwritten TS/fallback fixtures; these were corrected before the passing run.
- Rebuilt checked-in SPA assets and regenerated the white offline sample. In-app browser confirmed the explanation label, the wrapped unknown object and separate tool trace; screenshot retained. Public sample electrical counts remain unchanged: 1 PASS / 0 WARN / 3 ERROR / 17 UNKNOWN plus four profile gaps. No live/paid model, target Windows/Cadence run or peer acceptance was performed.
- Remaining: property/unit/condition verification for any future formal AI proposal, broad claim/citation adversarial coverage, remaining family heuristic voltage authority, BOM conflicts, reviewed-profile approval/subset, persistent history/dependency invalidation, target EDA and peer gates. T06/A08 and the full M0–M3 objective remain open.


### Eighth implementation package — 2026-10-24

- Migrated MOSFET Vgs/Vds and NPN VEBO/VCEO numerical-bound comparisons from name/hint inference to selected-mode confirmed min/max envelopes with common references. New shared terminal evaluator uses signed intervals; same-net differential is zero. Missing/unconfirmed/typical-only/cross-domain inputs, invalid or missing rating/source, unsupported NPN polarity and arithmetic overflow cannot certify a result. New rule version: 2.
- Entirely in-bound envelopes can PASS this limited numerical comparison; entirely out-of-bound envelopes FAIL. Boundary-crossing intervals remain UNKNOWN without a joint-state/correlation model. VCEO explicitly describes only comparison with the supplied profile upper bound, not proof of base-open applicability. No transistor functionality, transient/current/SOA/thermal acceptance is claimed, and profile provenance was not independently reapproved.
- Separated missing-terminal numeric applicability from connection defects: Q12 retains missing-emitter FAILs, while VEBO/VCEO return UNKNOWN. Main public component totals remain 1 PASS / 0 WARN / 3 ERROR / 17 UNKNOWN plus four profile gaps. Emitted-record distribution is now **145 = 108 PASS + 5 FAIL + 32 UNKNOWN**. Two duplicate numeric errors changed classification; this is not a physical circuit repair.
- Retained prior high-side, reverse B-E and overvoltage regressions using explicit synthetic operating facts instead of silently inferring test premises from net labels/hints. Added portable low/high-side synthetic input documents. The seeded MOS case now mutates the confirmed gate envelope from 10 V to 25 V while keeping net identity; clean and mutated runs carry the voltage document. All **7/7** expected differential cases still detect, with **0** unexpected differential findings; no population-level accuracy is inferred.
- Added **35** terminal-rating unit cases and **3** real API import/rerun/export cases. API gates prove Vgs PASS at 58−48 V, ERROR at 78−48 V, and UNKNOWN for a [67,69] V gate against 48 V source (crosses the ±20 V limit). All are synthetic explicit premises, not measured or independently labeled design truth.
- Final full `PYTHONPATH=src uv run pytest -q`: **926 passed, 7 deselected**, 20.16 s. Ruff and whitespace checks pass. Frontend **83** unit tests; contract/type/build pass; E2E **10 passed**, 16.6 s, real backend/fake AI. Existing fixture expectations were updated only after checking the changed proof assumptions; no topology regression was deleted.
- Regenerated the main white offline sample plus a separate high-side DC example. Browser inspected Vgs=[10,10] V, both source records and scope limits in the light React UI; viewport screenshot retained. Changed the header's unconditional “真实数据” to “已导入” after observing it on a synthetic input. Some `voltage_fact:` evidence currently renders as unknown source; canonical fact locators/classification remain an open T08 item.
- Remaining: pin/supply/diode/bootstrap/MCU/I2C/other heuristic voltage authority, BOM conflict handling, full condition/profile approval gates, fact locator UX, persistent decision history and dependency fingerprints, Windows/Cadence and independent peer evaluation. No live model/target hardware or target EDA was used. The complete objective and M0–M3 remain open.
