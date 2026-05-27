# Hardwise Rolling Log

> Scheduled improvements queued behind specific code milestones. When the trigger ships, knock the corresponding TODO off this file and move the content to its destination (usually CLAUDE.md or docs/architecture.md).
>
> This file exists because the editorial rule on CLAUDE.md and README.md forbids "TODO: add later" placeholders — those would be temporal framing. Park the TODOs here instead.
>
> Format per entry: **Trigger** / **Where it lands** / **What to add**.

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

## Triggered by Slice 5 — KiCad schematic net parser shipping (R005 dangling-nets)

**Where it lands**: `data/checklists/sch_review.yaml` → R005 (dangling / unexpected unconnected schematic nets), R006 (通用 net 命名规则), and R007 (分类 net 命名规则).

**What to add**: 123.md 第 5 章 (脱敏后的某硬件团队原理图规范) 提炼出的 net naming convention，作为 candidate rules 待 **schematic-side** net parser 上线后才可执行。PCB-side `pcb_nets` 不能作为 pre-Layout schematic-review evidence，因为评审节点还没有 `.kicad_pcb`。

**R006 — 通用 net 命名规则**（123.md §5.1 / §5.10 / §5.12）

| 子项 | 规则 |
|---|---|
| 字符集 | `[A-Z0-9_]` only；禁止小写、特殊字符、双下划线 `_ _` |
| 后缀 | `_N` 表示低电平有效（如 `RST_N`、`CS_N`） |
| 长度 | ≤ 32 字节 |
| 地网络 | 数字 `GND` (不显示)；模拟 `AGND1/AGND2` (显示)；机壳 `EGND` (显示) |

Check 逻辑（伪代码）：`re.fullmatch(r"[A-Z0-9_]+(?<!_)(?<!__)", net_name)` 且 `len(net_name) <= 32`；不符 → `severity=medium, action=按命名规范重命名`。

**R007 — 分类 net 命名规则**（123.md §5.2–§5.9）

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

**为什么不在 Slice 3 实现**：

1. 需要 KiCad schematic net parser：wire 连通、local/global label 合并、power symbol 合并、hierarchical label 跨页传播、symbol pin endpoint 映射到 `refdes/pin`；Slice 3 只做到 pin parser，Slice 5 task 3 目前只完成了 **PCB-side diagnostic parser**（读 `.kicad_pcb`），不能作为 pre-Layout 证据；
2. 公开 demo 项目 `pic_programmer` 用的是 KiCad 默认 net 命名（如 `Net-(D1-Pad1)`），不遵守 123.md 这套企业级规范，强行套用会输出大量 false positive；
3. 这两条规则的真实价值在企业级项目，pic_programmer 等公开 demo 跑不出有意义的结果，但代码逻辑可单测覆盖。

**先决条件 (planned)**：KiCad **schematic** net 解析能产出 `list[SchematicNetRecord(name, refdes_pin_list, source_labels, source_wires)]`。最小可行版本先支持同一 sheet 内 wire 连通、local/global label 合并、power symbol 合并、symbol pin endpoint 映射；hierarchical sheet 可第二步补。R005/R006/R007 只能吃这份 schematic-side 输入。

**安全边界**：R006/R007 的规则原文来自 123.md（脱敏后的某硬件团队原理图规范文件）；命名规则本身是行业通用做法（PXX 表电源、CLK_ 表时钟、差分 P/N 后缀），不携带任何具体项目代号 / 客户名 / 料号 / 内部系统名。

---

## Triggered by Day 2–3 — KiCad parser shipping

**Where it lands**: `CLAUDE.md` → new "Layout" section (between Stack and Models).

**What to add**: A directory tree like Wrench Board's, one line per directory. Should cover at minimum:

```
src/hardwise/
  adapters/          EDA boundary; one file per format. KiCad first, Cadence later.
  ingest/            File → store glue (PDF chunk, EDA → SQL).
  store/             Two stores: relational (refdes/nets/BOM/DRC) + vector (datasheet chunks).
  agent/             Tool-use loop, tier routing, prompts, tool manifest.
  guards/            Two-layer anti-hallucination: refdes guard + evidence ledger.
  memory/            Sleep Consolidator + candidate-rule pool (rules.md).
data/                Local input — KiCad projects + datasheet PDFs (gitignored except .gitkeep).
docs/                architecture.md / interview_qa.md / learning_log.md / rolling_log.md.
reports/             Generated review reports (markdown, gitignored).
```

Move the trigger off this file once shipped.

---

## Triggered by Day 4 — both stores wired up

**Where it lands**: `CLAUDE.md` → new "On-disk layout" section (after Layout).

**What to add**: Mirror Wrench Board's `memory/{device_slug}/` schema for Hardwise:

```
data/projects/{project_slug}/   # KiCad project files (input, gitignored)
data/datasheets/                # Public PDFs (input, gitignored, shared across projects)
data/hardwise.db                # SQLite — schema in src/hardwise/store/relational.py
data/chroma/                    # Chroma local persistence
reports/{project_slug}-{YYYYMMDD}.md     # Generated review report
src/hardwise/memory/rules.md             # Candidate rule pool (committed; small)
```

Document the slug rule, the timestamp format, and which files are gitignored vs committed.

---

## Triggered by Day 5 — CLI commands beyond `hello`

**Where it lands**: `CLAUDE.md` → new "CLI surface" section (after Run/test/lint).

**What to add**: Subcommand table.

```
| Command | What it does |
|---|---|
| hardwise ingest <project_path> | Parse KiCad + datasheets, populate both stores. |
| hardwise review <project_slug> | Run agent loop, write markdown report to reports/. |
| hardwise consolidate <report> | Extract candidate rules into memory/rules.md. |
| hardwise hello | Sanity check the install. |
```

Lock command names only after the third subcommand ships; renaming early is cheap, late is expensive.

---

## Triggered by Day 7 — first review report generated end-to-end

**Where it lands**: `CLAUDE.md` → new "Architectural anti-rules" subsection inside "Hard rules".

**What to add**: Concrete "do not" rules learned from running the loop in anger. Candidate items to watch for:

- "Do not let the agent generate refdes without a tool call." (You'll see it try.)
- "Do not put datasheet content in the relational DB; do not put refdes in the vector store." (The temptation is to denormalize when something is slow.)
- "Do not promote candidate rules without the human gate." (The Sleep Consolidator will look so reliable you'll want to skip review.)
- "Do not let the report exceed N pages." (Whatever N turns out to be when reviewers actually read it.)

Each anti-rule must reference a real moment when reality tried to violate it. Anti-rules pulled out of thin air are noise; anti-rules from a near-miss are gold.

---

## Discharged improvements (keep for audit)

> When an item moves out of this file, leave a one-line entry below noting where it landed.

- 2026-05-13 — "first tool registered in `agent/tools.py`" trigger landed → `CLAUDE.md` gained a "Tool manifest" section (between Models and Run/test/lint); 4 tools shipped (`list_components` / `get_component` / `get_nc_pins` / `search_datasheet`) with the `closest_matches` discriminated-union pattern replacing the original `get_net / check_bom / lookup_drc` placeholder shape. Names drifted as predicted; manifest reflects the actual Slice 3 store surface.
- 2026-05-14 — Slice 5 task 3 landed as a **scope correction**: the implemented net reader is PCB-side diagnostic infrastructure, not the schematic net parser required for pre-Layout review.
  - **Parser / `BoardRegistry.pcb_nets` / `store/relational.py pcb_nets+pcb_net_members`**: full KiCad PCB truth — 111 nets on `pic_programmer` (34 signal + 77 `unconnected-(Ref-Pad)`). Underlying layers never drop info, but this data comes from `.kicad_pcb` and is therefore **post-Layout evidence only**.
  - **CLI `inspect-kicad --net`**: now labelled `PCB-side net summary`; default view shows 34 PCB signal nets and `--all-nets` flips to the full 111 to match KiCad's PCB Net Inspector. Header prints `pcb nets: 34 signal (+77 unconnected = 111 total in PCB)` plus `source: .kicad_pcb (post-Layout fact; not pre-Layout review evidence)`.
  - Helper: `hardwise.adapters.kicad.pcb_signal_nets(pcb_nets)` — keep the unconnected-* filter KiCad/PCB-specific.
  - Test lock: parser stores `pcb_nets == 111` + 34 signal partition; SQLite round-trip 111 with GND member count = 40; CLI default vs `--all-nets` E2E asserts both source label and listing membership. `pytest -q` 144 passed; `ruff check .` clean.
  - Follow-up: add a synthetic `.kicad_pcb` unit test that explicitly lights both net syntaxes handled by `_pad_net_name()`; `pic_programmer` only gives implicit coverage for whichever KiCad version generated the fixture.
  - R005/R006/R007 remain queued above because they need a real schematic net parser: wire + local/global label + power symbol + hierarchical label + symbol pin endpoint resolution from `.kicad_sch`.
- 2026-05-26 — V2.9 stage details landed in code/docs: local document-index parsing + BOM item document matching + report sections + synthetic fixture smoke. The roadmap keeps V3.0+ queued for pin profiles and component validation, but V2.9 is no longer just a planned item.
- 2026-05-27 — V3.0 stage details landed in code/docs: schema-v2 `DatasheetProfile.pins`, L78 public pin-profile fixture, `report-pin-profile`, renderer and focused tests.
- 2026-05-27 — V3.1 stage details landed in code/docs: deterministic `validation/component.py`, `report-component-validation`, L78 regulator netlist+BOM fixtures, renderer and focused tests. Next component-family templates remain queued behind explicit public profiles and fixtures.
- 2026-05-27 — V3.2 stage details landed in code/docs: `report-validator-ui` creates a single-file local HTML UI with component index, selected validation detail, schematic-net pane, scope pane, and report download. V3.3 is queued for the next component-family template rather than more UI surface.
