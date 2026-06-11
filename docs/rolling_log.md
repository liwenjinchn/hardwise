# Hardwise Rolling Log

> Scheduled improvements queued behind specific code milestones. When the trigger ships, knock the corresponding TODO off this file and move the content to its destination (usually CLAUDE.md or docs/architecture.md).
>
> This file exists because the editorial rule on CLAUDE.md and README.md forbids "TODO: add later" placeholders — those would be temporal framing. Park the TODOs here instead.
>
> Format per entry: **Trigger** / **Where it lands** / **What to add**.

---

## Constrained LLM validator roadmap — staged after Copilot workbench

**Trigger**: The Allegro Copilot workbench (`serve-workbench` plus
`design-validator-ui --ai-snapshot`) is stable enough to demo selected-component
questions, evidence traces, and the unknown-refdes path.

**Where it lands**: `docs/PLAN.md` DR-013 records the architectural decision.
Implementation should be split into future Trellis tasks, with `docs/architecture.md`
and `docs/faq.md` updated only when a stage ships.

**What to build**: Move Hardwise from a deterministic-only validator toward a
constrained LLM validator. Deterministic validators remain the highest-confidence
source of `PASS` / `WARN` / `ERROR`; grounded LLM review is added later for
long-tail coverage, and only when board objects are registry-verified and
datasheet claims have page/token evidence.

| Stage | Product shape | Data/logic needed | Ship gate |
|---|---|---|---|
| C0 | Copilot workbench closeout | Finish current fake/live/snapshot paths, tests, docs, and commit | A local demo can ask about the selected component, show trace, and wrap `U999` |
| C1 | Six-section review report polish | Re-render existing `ValidationReport` truth into model check, pin summary, pin path, compliance matrix, evidence/page details, and final summary | `mixed_controller_power_stage` visibly explains the existing `U12` / `U8` / `U3` hard errors without changing validator semantics |
| C2 | Evidence-first UI | Trust labels (`deterministic`, `grounded`, `manual`), page/token chips, tool trace, and topology path shown beside each finding | Review detail makes evidence provenance obvious without opening raw JSON or markdown |
| C3 | Coverage/profile loop | Document-index candidates -> draft profile -> human review -> ready profile -> validation target | A large public board can move from grouped coverage gaps to reviewed profile candidates without auto-validating unfinished drafts |
| C4 | High-value deterministic family expansion | Select families from coverage data; likely LED polarity, small BJT/VCEO margin, common LDO/buck/gate-driver/MCU-debug refinements | At least one current no-profile/manual class becomes an L1 deterministic finding with tests and profile evidence |
| C5 | Grounded LLM long tail | L2 claim schema, datasheet retrieval requirement, evidence downgrade path, and report trust labels | **Trace-level done** (DR-014 第 4 条 discharge): per-tool trust-tier gating proven — L2-cites-evidence / unsupported→L3 / L2-cannot-override-L1 all tested. A no-profile component receives a grounded suggestion only when the answer cites retrieved datasheet evidence; missing evidence downgrades to manual. Sentence-level prose spec-claim gating remains a heavier future slice (separate DR if pursued). |
| C6 | Hosted shell | Upload/login/project persistence around the local trust loop | Hosted demo preserves the same guard/ledger/tool contracts and does not expose model secrets to the browser |

**Acceptance details for C1 report polish**:

1. Do not change validator verdicts or add new electrical rules in this stage.
2. Reuse existing `ValidationReport`, `component_checks`, pin rows, topology path
   facts, and evidence tokens.
3. The report should read like a hardware review artifact: model match,
   pin-check summary, pin function / connection path, consistency check,
   compliance matrix, thermal/electrical evidence where available, and final
   issue summary.
4. If evidence lacks an actual datasheet page token, render the gap explicitly
   instead of implying page-level proof.

**Acceptance details for C3 coverage/profile loop**:

1. Unready profile drafts must be marked `needs_review` and excluded from
   automatic validation.
2. Candidate generation should prioritize BOM/document groups that are frequent,
   safety-relevant, or likely to become deterministic family validators.
3. Public document indexes and public datasheets remain the only allowed inputs.
4. The loop should help choose the next deterministic family; it should not
   become live supplier lookup, PLM, lifecycle, price, availability, or PCB scope.

**D2 split after mainboard D1**:

1. D2a selects one `try_existing_validator_profile` family from the D1
   next-family advisory before any profile or validator work starts. Prefer
   `transistor`, `diode`, or a narrow `ic` power-management slice over the
   large `unknown` bucket.
2. D2b backfills public document-index evidence for the selected family only.
   Missing public evidence keeps the family in planning/manual state.
3. D2c adds at most one reviewed profile/validator slice, and only when the
   public datasheet evidence and existing deterministic validator semantics are
   sufficient.
4. D2d reruns the mainboard smoke and records whether manual coverage moved.
   It must not hide unchanged manual rows or change unrelated PASS/WARN/ERROR
   truth.

**Acceptance details for C5 grounded LLM**:

1. L2 answers must cite retrieved datasheet page/token evidence for every
   datasheet specification claim.
2. L2 answers may reference only registry-verified board objects; the existing
   Refdes Guard remains the final egress check.
3. Unsupported claims become L3 reviewer-to-confirm text, not factual findings.
4. L2 must not override L1 deterministic results. It may explain or translate
   them, but the structured validator remains authoritative.
5. Tests must include an unsupported-spec case that proves the claim is
   downgraded when evidence retrieval fails.

**Status (DR-014 第 4 条, 2026-06-05)**: acceptance items 1-5 are satisfied at
the **per-tool trace** granularity, not per-sentence. The trust tier rides on
each `ToolCallTrace`: `search_datasheet` is L2 only when retrieved hits carry
`datasheet:<pdf>#p<N>` provenance (`grounding.py:trust_tier_for_datasheet_search`),
fails closed to L3 with no hits / no collection (`runner.py`), and the L1
`run_component_validation` verdict lives on a separate trace that an L2 row never
merges into. Tested by `tests/agent/test_runner.py` (L2-evidence + unsupported→L3)
and `tests/agent/test_validation_bridge.py::test_runner_l2_search_does_not_override_l1_validation`.
Deferred (heavier, not "thin"): **sentence-level prose gating** — parsing the
final answer text so each spec-claim sentence must carry a backing token. Today
only the Refdes Guard scans answer prose; spec-claim entailment is not enforced
at the sentence layer. Pursue only behind a new DR if an interview/demo needs it.

---

## Final validator roadmap — staged after Allegro+BOM intake

**Trigger**: V2.7 Allegro/PST + schematic BOM intake report shipped.

**Where it lands**: `docs/architecture.md`, `docs/PLAN.md`, and implementation slices as each stage ships. Keep this as the staged roadmap until a slice graduates into code + tests.

**What to build**: Move Hardwise toward the target "design validator" product shape: component list, datasheet match, per-component pin-level validation, PASS/WARN/ERROR summaries, downloadable reports, and schematic linkage. The route must stay inside the pre-Layout schematic-review node and must not become `.brd`, boardview, placement, routing, PCB geometry, PLM, pricing, lifecycle, or supplier-risk tooling.

| Stage | Product shape | Data/logic needed | Ship gate |
|---|---|---|---|
| V2.8 | Report index view | Prefix summary, BOM item groups, mismatch-only and summary-only report modes, short source tokens | Public Allegro+BOM sample can be scanned without opening a 4000-row flat table |
| V2.9 | Datasheet/document match layer | BOM item / MPN to datasheet links with `matched / no_result / ambiguous / manual_needed` states | Report shows which component groups have usable public datasheets |
| V3.0 | Pin Profile | Structured pin profile per selected part: pin no/name/function/limits/recommended topology | A small public profile set can drive deterministic pin comparison |
| V3.1 | Single-component validation report | Deterministic validator for one selected refdes using schematic topology, optional BOM identity, and structured pin profile limits | At least one regulator component produces pin-level PASS/WARN/ERROR rows with source tokens |
| V3.2 | Local static validator UI | Component table, selected validation detail, schematic-net pane, scope pane, download action | Local HTML mirrors the validator workflow using public sample data |
| V3.3 | XL1509 buck-converter template | Public XL1509 profile + synthetic Allegro/BOM fixture, with deterministic output-net inductor/freewheel-diode rules | DCDC fixture catches `1N4007W` freewheel diode and `6.8uH` inductor while preserving the UI contract |
| V3.4 | Multi-validation UI/index | Run and render more than one selected component profile in one artifact | UI can show multiple validated devices and switch detail panes without duplicating validation logic |
| V3.5 | Validation targets manifest | Store explicit refdes-to-profile assignments in YAML | Batch UI can be rerun from a committed manifest without auto profile matching |
| V3.6 | Profile candidate manifest | Suggest explicit refdes-to-profile candidates from BOM identity and local profile library | Reviewer gets matched/unmatched profile coverage without automatic validation |
| V3.7 | Product-like validator UI polish | Rework batch UI into a three-column workbench with Chinese report sections and issue-first detail | Static artifact looks closer to the target screenshot while preserving the same validation truth |
| V3.8 | EG2132 gate-driver template | Add deterministic half-bridge driver checks for VCC, logic inputs, gate loads, switch node, and bootstrap path | U3-style driver fixture catches low-voltage bootstrap diode without layout/timing scope creep |

**V2.8 acceptance details**:

1. `report-allegro-bom` keeps full mode as the default for reproducibility.
2. `--summary-only` omits the full component table and shows index sections only.
3. `--mismatch-only` emits only status + mismatch sections for fast triage.
4. Source cells use short tokens in large tables, while report header keeps the full netlist/BOM paths.

**V2.9 acceptance details**:

1. `report-allegro-bom --document-index <csv-or-tsv>` adds local datasheet/document match sections to summary/full reports.
2. Matching is BOM-item identity indexing: MPN first, part-like value only as fallback, optional manufacturer narrowing.
3. Output status is one of `matched`, `no_result`, `ambiguous`, or `manual_needed`; it is not electrical PASS/FAIL.
4. Each rendered document row carries a `doc:<file>#line<N>` source token.
5. The command performs no live supplier lookup and no PLM, lifecycle, price, availability, supplier-risk, `.brd`, boardview, placement, routing, or PCB geometry work.
6. `--document-index` is rejected with `--mismatch-only`, because mismatch triage intentionally omits index sections.

**V3.0 acceptance details**:

1. `DatasheetProfile` remains backward-compatible with v1 JSON and adds `pins[]` for structured pin facts.
2. Each `PinProfile` row carries pin number, name, category, function, optional limits, recommended topology, and evidence tokens.
3. `data/datasheet_profiles/l78.json` is a public schema-v2 fixture with VI/GND/VO rows.
4. `report-pin-profile <profile.json>` renders pin summary/detail sections for manual inspection.
5. The command does not perform schematic validation, PASS/FAIL judgement, live supplier lookup, PLM, lifecycle, price, availability, supplier-risk, `.brd`, boardview, placement, routing, or PCB geometry work.

**V3.1 acceptance details**:

1. `validate_component_against_profile()` returns a `ValidationReport` for one component and one structured profile.
2. V3.1 rule coverage is intentionally narrow: profiled pin exists, pin has a net, ground pins connect to recognized ground nets, power-input nets compare against structured voltage limits, and fixed power-output nets compare against nominal voltage.
3. `report-component-validation <netlist_or_pst> <refdes> <profile.json> --bom <bom>` renders overall status plus pin-level PASS/WARN/ERROR rows.
4. The first shipped smoke path uses the public/synthetic L78 regulator fixture and reports VI/GND/VO as `PASS/WARN/ERROR=3/0/0`.
5. Unknown component families and unsupported pin categories remain WARN/manual-review territory until a family-specific deterministic template is added.
6. The command performs no live supplier lookup and no PLM, lifecycle, price, availability, supplier-risk, `.brd`, boardview, placement, routing, or PCB geometry work.

**V3.2 acceptance details**:

1. `report-validator-ui <netlist_or_pst> <bom> <refdes> <profile.json>` writes one self-contained HTML file.
2. The UI shows component index, selected component identity, PASS/WARN/ERROR counts, pin validation table, schematic-net members, scope boundary, and a markdown download link.
3. It reuses `validate_component_against_profile()` and does not introduce a separate validation truth.
4. It requires no web server, npm build, WebSocket, backend session state, `.brd`, boardview canvas, placement, routing, or PCB geometry.
5. The first smoke path uses the public/synthetic L78 regulator fixture and opens directly from disk.

**V3.3 acceptance details**:

1. `data/datasheet_profiles/xl1509.json` adds a public structured XL1509-12E1 profile with VIN/OUTPUT/FEEDBACK/ON/OFF/GND pin rows and DCDC recommended limits.
2. `validate_component_against_profile()` remains the single entry point; XL1509-specific checks live behind a profile-dispatched buck topology path.
3. Component-level checks record peripheral/topology facts separately from pin rows: OUTPUT net inductor presence/value and freewheel diode family.
4. The public synthetic fixture `xl1509_buck.net` + `xl1509_buck_bom.csv` reports overall `ERROR` because `D5=1N4007W` is not a Schottky-style freewheel diode and `L1=6.8uH` is below the profile minimum.
5. Nominal Schottky + inductor-range tests return no ERROR; missing inductor returns ERROR; unknown diode family returns WARN; wrong FB rail returns ERROR.
6. Markdown and UI reports reuse `ValidationReport.component_checks` and remain single-selected-component artifacts.
7. The command performs no live supplier lookup and no PLM, lifecycle, price, availability, supplier-risk, `.brd`, boardview, placement, routing, thermal layout, or PCB geometry work.

**V3.4 acceptance details**:

1. `report-validator-ui-batch <netlist_or_pst> <bom> REFDES=profile.json [...]` writes one self-contained HTML file.
2. Each target is explicit; V3.4 does not auto-match profiles to every component.
3. The command runs `validate_component_against_profile()` once per target and reuses the same `ValidationReport` shape.
4. The UI shows component index rows plus multiple validated component detail panes, status chips, schematic-net panes, scope panes, and per-component markdown downloads.
5. The smoke fixture contains one L78 PASS result and one XL1509 ERROR result in the same schematic artifact.
6. It requires no web server, npm build, WebSocket, backend session state, `.brd`, boardview canvas, placement, routing, or PCB geometry.

**V3.5 acceptance details**:

1. `report-validator-ui-batch` accepts either positional `REFDES=profile.json` targets or `--targets-manifest <yaml>`.
2. The manifest shape is `project` plus a non-empty `targets` list containing `refdes` and `profile`.
3. Refdes values are uppercased and duplicates are rejected before validation runs.
4. Manifest profile paths remain current-working-directory relative, matching the positional target behavior.
5. Positional targets and `--targets-manifest` are mutually exclusive to avoid hidden override order.
6. The mixed fixture manifest validates the same U1 PASS and U12 ERROR results as the positional CLI path.
7. It does not auto-match profiles, infer profiles from BOM MPNs, add supplier/PLM state, parse `.brd`, inspect boardview, or use PCB geometry.

**V3.6 acceptance details**:

1. `suggest-validation-targets <bom> --profiles data/datasheet_profiles` writes a YAML candidate manifest.
2. Candidate matching uses normalized exact match from BOM MPN first, then part-like value, to local profile `part_number`.
3. Each candidate records `matched`, `no_result`, `ambiguous`, or `manual_needed`; unmatched rows remain visible in the default output.
4. `--matched-only` writes the minimal V3.5 `project + targets[]` manifest shape for matched rows only.
5. The mixed fixture reports U1 and U12 as matched, with passive/peripheral rows as no-result.
6. It does not run validation, auto-accept targets, fetch datasheets, infer missing profiles, add supplier/PLM state, parse `.brd`, inspect boardview, or use PCB geometry.

**V3.7 acceptance details**:

1. `report-validator-ui-batch` still writes one self-contained static HTML file with no npm build, server, WebSocket, or backend state.
2. The batch renderer now uses a workbench layout: top project/status summary, left component index/filter, middle validation cards, and right report detail.
3. The default active detail is issue-first: ERROR before WARN before PASS, so the mixed fixture opens on `U12 ERROR`.
4. Detail panels use Chinese product labels and report sections: `器件`, `验证`, `验证报告`, `引脚检查汇总`, `器件基本信息`, `型号核对`, `引脚功能与连接关系`, `综合合规性检查`, and `综合总结`.
5. `component_checks` render as a separate `外围/拓扑检查` area so XL1509 peripheral errors such as `D5=1N4007W` and `L1=6.8 uH` are not buried in pin rows.
6. It does not add new validation families, automatic validation, hosted app behavior, supplier/PLM state, `.brd`, boardview, placement, routing, or PCB geometry.

**V3.8 acceptance details**:

1. `data/datasheet_profiles/eg2132.json` adds a public structured EG2132 profile with `VCC/HIN/LIN/GND/LO/VS/HO/VB` pin rows and half-bridge gate-driver recommendations.
2. `validation/gate_driver.py` is enabled only for EG2132 or profiles declaring `recommended.topology_family: half_bridge_gate_driver`.
3. Component-level checks cover VCC range, HIN/LIN connectivity, HO/LO gate-load reachability, VS switch-node reachability, and VB/VS bootstrap diode/capacitor topology.
4. The synthetic fixture reports overall `ERROR` because `D1=MBRA210LT3G` has only a low reverse-voltage hint for a 24 V-class bootstrap path.
5. Nominal bootstrap diode/load tests return no component ERROR; missing bootstrap capacitor, missing gate load, bad VCC, and missing logic input return ERROR; unknown bootstrap diode rating returns WARN.
6. V3.8 does not add MCU, LED, transistor, timing/deadtime, MOSFET loss, simulation, layout/current-loop, supplier/PLM, `.brd`, boardview, placement, routing, or PCB geometry scope.

---

## KiCad schematic topology parser — remaining after named-net bridge

**Where it lands**: `data/checklists/sch_review.yaml` → R005 (dangling /
unexpected unconnected schematic nets) and any future topology-aware R007 slice.

**Shipped bridge (2026-06-12)**: R006-style net-name checks no longer wait on
full KiCad topology. `adapters/kicad_schematic_nets.py` extracts explicit
`.kicad_sch` local/global/hierarchical labels and power-symbol values into
`SchematicNetRecord`; `inspect-kicad --schematic-net --check-net-names` reuses
`validation/net_naming.py` `NamingPolicy`, with optional `--naming-policy`
YAML. This is naming evidence only: no wire fanout, pin endpoints, `.kicad_pcb`,
or PCB geometry.

**Still staged**: R005 dangling-net/fanout checks need a real schematic topology
parser: wire connectivity, local/global label merge, power-symbol merge,
hierarchical sheet propagation, and symbol pin endpoint mapping to `refdes/pin`.
PCB-side `pcb_nets` remains invalid as pre-Layout schematic-review evidence.

**Strict R006 policy shape, when a site YAML opts in**:

| 子项 | 规则 |
|---|---|
| 字符集 | `[A-Z0-9_]` only；禁止小写、特殊字符、双下划线 `_ _` |
| 后缀 | `_N` 表示低电平有效（如 `RST_N`、`CS_N`） |
| 长度 | ≤ 32 字节 |
| 地网络 | 数字 `GND` (不显示)；模拟 `AGND1/AGND2` (显示)；机壳 `EGND` (显示) |

Check 逻辑（伪代码）：`re.fullmatch(r"[A-Z0-9_]+(?<!_)(?<!__)", net_name)` 且 `len(net_name) <= 32`；不符 → `severity=medium, action=按命名规范重命名`。

**R007 — 分类 net 命名规则**（仍为公开通用命名习惯候选）

| 类别 | 模式 | 例 |
|---|---|---|
| 时钟 single-ended | `CLK_<freq>_<receiver>` | `CLK_33M_ICH` |
| 时钟 differential | `CLK_<freq>_<rcv>_DP[N]/DN[N]` | `CLK_100M_SATA_DP0` |
| 复位 | `RST[_T][_R]_<fn>[_N]` | `RST_PCH_PLTRST_N` |
| 电源 | `P<voltage>[_STBY/DUAL][_<rcv>]` | `P3V3_STBY`, `P12V_CPU0` |
| 总线 PCIe | `<T>_PCIE<width>_P<port>` | `CPU0_PCIE16_P0` |
| 总线 I2C | `<T>_I2C<n>_{SDA,SCL}` | `CPU0_I2C0_SDA` |
| 差分 | `_DP/_DN` 放在 net 名最后；总线时跟编号 | `SATA_DP0` |
| 串联端接后 | net 流出串阻后加 `_R`，流出耦合电容后加 `_C` | `CLK_33M_R`, `DDR_DQ0_C` |

Check 逻辑：按 prefix 路由到不同 regex；任何"看起来像但不符合"（如 `clk_33m_ich`、`CLK33M`、`POWER_5V`）→ `severity=medium, action=按分类命名规范重命名`。

**先决条件 (planned)**：KiCad **schematic topology** 解析能产出 net names plus
`refdes/pin` endpoint membership. 最小可行版本先支持同一 sheet 内 wire 连通、
local/global label 合并、power symbol 合并、symbol pin endpoint 映射；
hierarchical sheet 可第二步补。R005 和任何 topology-aware R007 只能吃这份
schematic-side 输入。

**安全边界**：R006/R007 只能来自公开通用命名习惯和本仓库公开 fixture 反馈；不要使用公司内部硬件团队规范，即使材料已经脱敏。示例模式（PXX 表电源、CLK_ 表时钟、差分 P/N 后缀）只能作为公开候选，必须先用公开项目或合成 fixture 单测验证，再进入规则库。

---

## Pin-table follow-ons — staged after workbench intake

The core workbench intake is shipped: `design-validator-ui --pin-table`,
`serve-workbench --pin-table`, and `POST /api/workbench/import` accept an
optional Capture pin-table CSV; `workbench/context.py` runs R008/R009/R010, rejects
unknown-refdes findings, and `workbench/view_model.py` surfaces accepted rows
as L1 `pin_table_check` review tasks. These tasks do not change
`ValidationReport` PASS/WARN/ERROR totals.

R010 nc-conflict is now shipped: an NC-marked but wired pin becomes a
medium-severity, reviewer-to-confirm L1 task, because the pin-table row proves
contradiction but not whether the NC marker or the wire is wrong.

Remaining candidate follow-on checks from the same data, in value order:
off-page-orphan (off-page name on exactly one page), then net-naming checks
(the R006/R007 family can run on the pin-table `net` column). Hard bounds:
same `Finding` shape, no new validation truth without a documented denominator
change, no PCB/PLM scope.

---

## Eval dual-track: seeded-defect benchmark + defects4KiCad mining — staged for interview prep

**Trigger**: interview scheduled (not a submission blocker). Motivation: the
current eval pack reports counts (437 findings, 0 failures), not rates — there
is no recall/precision number to answer "how accurate is it", and the eval
corpus is KiCad while the demo mainline is Allegro netlist/PST+BOM.

**Search conclusion (2026-06-11, grok multi-query, cross-verified)**: no public
"schematic + human-labeled defects" dataset exists — commercial AI schematic
review tools (galvano.ai, Netlist.io, ThomsonLint, AllSpice) publicly state
they rely on private design data. The gap is industry-wide, which makes the
harness design itself the story.

**Architecture — two tracks, one number**:

```
optimization signal (infinite, free)      holdout (small, real)
Track A: seeded-defect mutation set   →   Track B: defects4KiCad pilot
agent scores → tune rules → re-run        verify-only, never tuned against
```

Track A answers "what's the rate"; Track B answers "but did you just overfit
your own mutations" — the classic critique of mutation oracles. Neither track
alone survives that question.

**Track A — seeded-defect benchmark (Allegro-native, ~3-5h)**: programmatically
inject known defects into clean fixtures (`tests/fixtures/allegro/pst/`):
drop footprint fields, strip cap rated-voltage suffixes, alter NC pin wiring,
break BOM line matches — 3-5 cases per shipped rule. Ground truth by
construction; zero labeling. Output one headline number:
"N seeded defects, recall X/N, Y new false positives". Mutation-testing
analogy is the interview term. Each future check (e.g., Capture pin-table
checks above) ships with its own seeded cases.

**Track B — defects4KiCad mining pilot (~3-4h timebox)**: mine git history of
the 5 repos already in `eval/manifest.yaml` for commits touching `.kicad_sch`
with fix-like messages — the commit message is a human-written defect
description, the pre-fix tree is a defective schematic, free real gold. Search
confirmed no prior art (no defects4j-style schematic mining exists publicly).
Verify 10-20 cases by hand (minutes each — verification, not labeling). Scope
caveat: filter for defect classes current rules cover (component/field-level:
footprint, value, NC); net-topology defects (missing pull-up) need the queued
schematic net parser (R005+) and become its motivation, not this pilot's scope.

**Why KiCad is the only minable source (and why that's fine)**: code LLMs work
because source is text with public git history; in EDA only KiCad satisfies
both (.kicad_sch is S-expression text, large public repo base). Cadence
formats are binary/proprietary with no public fix history — mining there is a
dead end, full stop. But defect patterns are EDA-agnostic; carriers are
EDA-specific. Mined KiCad defects replay through the kicad adapter into the IR
and validate the shared rules layer — the same layer the Allegro path uses.
Track A runs Allegro-native, so the mainline is covered where it matters.

**Supplementary sources (optional, "one more month" answers)**:

- KiCad source tree `qa/tests/eeschema/erc/` — ERC regression fixtures with
  expected violations; narrow, engine-edge-case flavored; ~1h to harvest for
  ERC-overlap rules.
- PCB-Bench (ICLR 2026, verified live: github.com/digailab/PCB-Bench) —
  ~3,700 expert QA on placement/routing/design rules + 174 complete OSHWHub
  projects (mostly LCEDA format). QA-style, not defect labels: use the 174
  projects as corpus expansion and the QA set as a knowledge-layer sanity
  check, not as gold.
- TI/ADI reference designs (OrCAD/Allegro files, presumed-correct) — negative
  control corpus for false-positive measurement on the Cadence side; no fix
  history, so no defect gold.
- Community review threads (r/PrintedCircuitBoard, EEVblog) — confirmed never
  scraped into a dataset; image-heavy. Use for rule discovery (recurring
  human-flagged issues → checklist candidates → Sleep Consolidator), never as
  eval instances.

**Scope bound**: Track A = one injection script + one scoring report; Track B
= 10-20 verified cases, manifest repos only, no new repos. No human gold-label
set, no monitoring dashboard, no community scraping — those are "one more
month" interview answers, not work items.

---

## Rules-layer re-audit conclusions — staged for interview prep

**Trigger**: interview scheduled. Source: a 2026-06-11 re-audit of the rules
layer against the original checklist source material and the schematic design
spec it lives under (full audit is a private reference doc; only sanitized
conclusions land here, abstract "checklist 第 N 条" references per the
`sch_review.yaml` convention). The narrative, naming-family, and asset-sync
conclusions shipped 2026-06-11 — see the discharged list. What remains staged:

**Review work-product is evidence tables, not verdicts**: the source review
method asks for output tables (GPIO/net list, link list, I2C mapping table,
polarized-component list, cap voltage min/max table) far more often than
pass/fail. Target product shape: the report should be able to emit a
review-deliverable pack (checklist back-fill table + per-item evidence tables
+ feedback-list draft). Long-term shape, not a near-term slice; record in
`docs/PLAN.md` as a DR when pursued.

**Polarized-component inventory table (第 18 条, ~1h)**: refdes-prefix + BOM
class, pure table output — the cheapest proof of the table-first shape above.

**Series-termination naming check (deferred remainder of the naming family)**:
the `_R`/`_C` suffix convention makes series elements *recognizable* from net
names, but checking 第 2 条 ("series resistor reserved on low-speed buses")
honestly requires correlating the name with actual series topology — a
name-only version would guess. Stays behind net-topology correlation work.

**Scope bound**: no current-annotation semantics (第 12/21 条), no
back-feed/anti-backflow topology patterns (第 13 条), no cross-connector link
tracing (第 5/14 条 full form), no deliverable-pack product build. 第 3/19/20
条 stay blocked behind the Capture pin-table export entry above.

---

## Discharged improvements (keep for audit)

> When an item moves out of this file, leave a one-line entry below noting where it landed.

- 2026-06-11 — Rules-layer re-audit conclusions 1/3/4 shipped on `reaudit/rules-layer`:
  - **Narrative corrections** landed in `docs/faq.md` (Q1 check-selection principle, Q6 naming-rules dependency fix) and as rationale comments on R001/R003 in `data/checklists/sch_review.yaml`.
  - **Naming-policy check family** landed as `validation/net_naming.py` (charset/double-underscore/uppercase-opt-in, max-length, `_DP`/`_DN` pair check incl. trailing index; policy-as-data via `NamingPolicy` + `load_naming_policy`, site YAML never committed; `_P`/`_N` pairing deliberately off-default — collides with active-low). Wired into `project_index.net_checks`; 10 seeded tests in `tests/validation/test_net_naming.py`; public fixtures naming-clean → zero new findings, noise gate held.
  - **Honest corrections found while implementing**: power-rail and ground recognition already shipped in `pins.voltage_for_net` / `pins.is_ground_net` (not rebuilt); the series-termination `_R`/`_C` check was *not* shipped — name-only would guess, it stays staged above behind topology correlation.
  - **Asset sync** landed in `sch_review.yaml`: R005 entry now records the shipped Allegro implementation (`validation/nets.py`) and scopes `planned` to the KiCad checklist path; new boundary memo documents that Allegro net-level families are registered in code, not in this yaml.
- 2026-06-11 — Four early "Triggered by Day 2-7" entries retired as superseded; none was executed as written, their substance landed elsewhere or drifted past the spec:
  - **Day 2-3 directory tree → CLAUDE.md "Layout"**: CLAUDE.md later became a thin agent overlay (Drift Guard); module layout lives in `docs/architecture.md` (flow diagram + per-module tables) and AGENTS.md "Where to look". The planned tree also predates `validation/`, `workbench/`, `bom/`, `documents/`, `report/` — reality outgrew it.
  - **Day 4 on-disk layout (mirror Wrench Board `memory/{device_slug}/`)**: storage shipped as SQLAlchemy relational (SQLite/PostgreSQL, `store/relational.py`) + Chroma, documented in `docs/faq.md` Q3 and architecture.md. The Wrench Board mirror was never the shape; following this entry today would be a regression.
  - **Day 5 CLI subcommand table**: the CLI grew far beyond the four planned commands (`inspect-kicad`, `report-*`, `design-validator-ui`, `serve-workbench`, `suggest-validation-targets`, `eval`, `verify-api`, …) and names locked organically. `uv run hardwise --help` self-documents; add a doc table only if a consumer actually needs one.
  - **Day 7 architectural anti-rules**: the substance landed in AGENTS.md — Hard rule 3 (two-layer refdes defense), "Tools return structured null, never fabricated", "Two stores, one join key" (the denormalization anti-rule), and the Sleep Consolidator human gate. The report-length cap never earned a near-miss and stays unwritten per this entry's own "anti-rules from a near-miss" standard.

- 2026-05-13 — "first tool registered in `agent/tools.py`" trigger landed → `CLAUDE.md` gained a "Tool manifest" section (between Models and Run/test/lint); 4 tools shipped (`list_components` / `get_component` / `get_nc_pins` / `search_datasheet`) with the `closest_matches` discriminated-union pattern replacing the original `get_net / check_bom / lookup_drc` placeholder shape. Names drifted as predicted; manifest reflects the actual Slice 3 store surface.
- 2026-05-14 — Slice 5 task 3 landed as a **scope correction**: the implemented net reader is PCB-side diagnostic infrastructure, not the schematic net parser required for pre-Layout review.
  - **Parser / `BoardRegistry.pcb_nets` / `store/relational.py pcb_nets+pcb_net_members`**: full KiCad PCB truth — 111 nets on `pic_programmer` (34 signal + 77 `unconnected-(Ref-Pad)`). Underlying layers never drop info, but this data comes from `.kicad_pcb` and is therefore **post-Layout evidence only**.
  - **CLI `inspect-kicad --net`**: now labelled `PCB-side net summary`; default view shows 34 PCB signal nets and `--all-nets` flips to the full 111 to match KiCad's PCB Net Inspector. Header prints `pcb nets: 34 signal (+77 unconnected = 111 total in PCB)` plus `source: .kicad_pcb (post-Layout fact; not pre-Layout review evidence)`.
  - Helper: `hardwise.adapters.kicad.pcb_signal_nets(pcb_nets)` — keep the unconnected-* filter KiCad/PCB-specific.
  - Test lock: parser stores `pcb_nets == 111` + 34 signal partition; SQLite round-trip 111 with GND member count = 40; CLI default vs `--all-nets` E2E asserts both source label and listing membership. `pytest -q` 144 passed; `ruff check .` clean.
  - Follow-up: add a synthetic `.kicad_pcb` unit test that explicitly lights both net syntaxes handled by `_pad_net_name()`; `pic_programmer` only gives implicit coverage for whichever KiCad version generated the fixture.
  - R005/R006/R007 remain queued above because they need a real schematic net parser: wire + local/global label + power symbol + hierarchical label + symbol pin endpoint resolution from `.kicad_sch`.
- 2026-05-26 — V2.9 stage details landed in code/docs: local document-index parsing + BOM item document matching + report sections + synthetic fixture smoke. The roadmap keeps V3.0+ queued for pin profiles and component validation, but V2.9 is no longer just a planned item.
- 2026-06-11 — Capture pin-table export discharged: `scripts/capture_pin_table_export.tcl` (v5; 12/12 columns validated on a real 81-page / 15879-pin design, pin-type enum cross-checked at 99.9%), adapter `adapters/capture_pin_table.py` + synthetic fixture, checks R008 (floating input) / R009 (unconnected power pin), and the `report-pin-table` CLI all shipped on `feat/capture-pin-table`. Final schema lives in the adapter docstring; bring-up story in `docs/learning_log.md` (2026-06-11). Remainder staged above as "Pin-table workbench intake".
- 2026-05-27 — V3.0 stage details landed in code/docs: schema-v2 `DatasheetProfile.pins`, L78 public pin-profile fixture, `report-pin-profile`, renderer and focused tests.
- 2026-05-27 — V3.1 stage details landed in code/docs: deterministic `validation/component.py`, `report-component-validation`, L78 regulator netlist+BOM fixtures, renderer and focused tests. Next component-family templates remain queued behind explicit public profiles and fixtures.
- 2026-05-27 — V3.2 stage details landed in code/docs: `report-validator-ui` creates a single-file local HTML UI with component index, selected validation detail, schematic-net pane, scope pane, and report download. V3.3 is queued for the next component-family template rather than more UI surface.
- 2026-06-11 — Weekend closeout handoff discharged: the closeout (generic inductor/ferrite validation, PE537BA profile, pressure reruns, docs refresh) shipped and its measured facts live in `docs/closeout_pressure_summary.md` and README. The standalone `weekend_closeout_plan.md` checklist was removed in the docs cleanup; history stays in git.
