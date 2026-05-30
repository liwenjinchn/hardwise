# Hardwise Learning Log

> Every issue debugged is a unit of internalized knowledge. This file is not a complaint board — it's the journal of "what surprised me when reality didn't match my mental model."
>
> Format per entry: **Symptom** / **Root cause** / **Fix** / **Takeaway**. Add a HW analogy in root cause when it actually clarifies; don't force one.
>
> Interview hook: "what surprised you while building this?" → entries here are the honest answer.

---

## 2026-05-29 · V3.13 · V1 should validate one real power family, not all devices

**Symptom**

Grouped coverage made真实项目可读了，但如果下一步继续“按器件一个个补 profile”，项目又会发散成一个无限
器件库维护任务。真实 Allegro 项目里有 132 个 BOM/device groups，其中电源相关 IC 很适合作为第一条
深验证链路，但不能承诺全 BOM 自动验证。

**Root cause**

V1 的闭环单位应该是“全项目 coverage + 少数高价值 family validation”。全项目层负责暴露 132 个 groups、
document/profile 状态和缺口；验证层只在 structured profile + family validator 都可信时输出
PASS/WARN/ERROR。否则就会把 coverage、datasheet resolution、fact extraction 和 electrical judgement
混成一个看似自动、实际不可审计的大功能。

**Fix**

选 `MPQ8626` 同步 buck 作为 V1 power family target。新增 `mpq8626.json` structured profile，使用
`part_number_aliases` 匹配 `MPQ8626GD` / `MPQ8626GD-Z`；新增 `power_v1_docs.csv` 本地公开文档索引，
链接到 MPS 公开产品/资料页；扩展 buck validator 支持 `SW1/SW2`、`PL` 前缀电感和同步 buck
“不需要外部续流二极管”的规则。真实项目中 `U13/U20/U23/U26` 自动进入验证。

**Verification**

真实公开 Allegro 文件夹 smoke 加 `--document-index data/document_indexes/power_v1_docs.csv` 后输出：
4010 components / 132 groups / document matched=2 BOM groups / validated=4 /
PASS-WARN-ERROR=4-0-0 / manual=4006。JSON 中 `MPQ8626GD` 和 `MPQ8626GD-Z` 两个 groups 都是
`profile_status=matched`、`document_status=matched`、`validation_status=PASS`。浏览器 smoke 确认
HTML 显示 132 groups、4 个 validated devices、MPQ8626 docs、`buck_inductor` 和同步 buck 结论。

**Takeaway**

V1 的收束语句是：全项目 coverage 可见，power family 深验证。不要把“新器件很多”当成要无限补
MPN profiles；先让 document/profile/family 三层状态可审计，再按 family 扩。

## 2026-05-28 · V3.12 · Real-project coverage needs BOM groups, not raw refdes rows

**Symptom**

真实 Allegro/PST 项目导入后有 4010 个 design components。即使 `design-validator-ui` 能在
`validated=0` 时生成 artifact，逐位号展示仍然会把 reviewer 淹没在 4010 条 no-profile/manual rows 里，
不像一个可审计的项目入口。

**Root cause**

Profile 和 datasheet 的扩展单位不是单个 refdes，而是 BOM item / device identity。电容、电阻、连接器、
test point 和 IC 应该先按 BOM group 聚合，再显示 normalized identity、family、profile status 和 document
status。否则每导入一个新项目，Hardwise 看到的都是“几千个孤立缺口”，而不是“几十/上百个可补的器件组”。

**Fix**

新增 `validation/component_identity.py` 和 `validation/component_groups.py`，从 BOM item 构建
`component_groups`：真实 MPN 优先，`GW_*`、`MARK`、`HOLE_*`、`TEST_POINT_*` 等占位名不当作真
MPN；passives 用 value 作为 identity；connector / mechanical / test point 明确分 family。
`design-validator-ui --document-index` 接入本地 document index，HTML/Markdown/JSON 都输出同一套
group coverage。

**Verification**

真实公开 Allegro 文件夹 smoke：自动选择 `SWITCH BOARD 144-VA_20240712 1401(1).BOM`，输出
4010 components / BOM matched=4010 / validated=0 / manual=4010，并把 4010 rows 聚合成 132 个
component groups。浏览器 smoke 确认 HTML 有 `Component Group Coverage`、`Docs` 列和真实 IC 组
如 `MP5991`。

**Takeaway**

真实项目的第一层产品闭环是 group-first coverage。先把“哪些器件族/identity 需要 profile 或 datasheet”
变成可审计清单，再进入自动下载、事实抽取和 family validator。

## 2026-05-28 · Trellis workspace files must stay outside Hardwise lint/test scope

**Symptom**

After Trellis was initialized in the repo, `uv run ruff check .` started reporting style errors under
`.trellis/scripts/`, even though those files are generated workflow tooling rather than Hardwise source.

**Root cause**

Ruff scans the repository tree unless configured otherwise. The project already had the same boundary for public eval
checkouts, but Trellis added another generated/tooling tree with Python files.

**Fix**

Added `.trellis` to Ruff's `exclude` list and pytest's `norecursedirs` so repo quality gates cover Hardwise-owned code,
tests, and docs instead of generated workflow tooling.

**Takeaway**

Local workflow/runtime folders need an explicit lint/test boundary as soon as they enter the repo tree.

---

## 2026-05-28 · V3.11 · Zero-profile real projects still need a workbench

**Symptom**

真实 Allegro/PST 项目可以成功解析 topology，BOM 也能 100% join，但本地 profile library 对它可能
`matched=0`。旧的 `design-validator-ui` 会在这种情况下退出失败，让 reviewer 看不到已经可信的
intake facts 和 profile coverage 缺口。

**Root cause**

CLI 把“没有 deterministic validation result”误当成“不能生成 artifact”。这混淆了两层事实：
EDA/BOM intake 已经可信，电气 PASS/WARN/ERROR 只是 profile 覆盖后的下一层。没有 profile 时应该
展示 coverage boundary，而不是失败或假装验证。

**Fix**

新增项目级 workbench renderer。`design-validator-ui` 现在把 `ProjectValidationIndex` 交给 renderer：
有 validated rows 时继续展示现有多器件 validation detail；没有 validated rows 时展示
Profile coverage gap、profile status counts、前 50 条 no-profile/manual rows、scope boundary，并继续写
markdown/JSON sidecars。

**Verification**

Focused tests cover zero-profile CLI output and renderer HTML. Smoke path with a temporary profile directory containing
only `l78.json` over `stm32g030_mcu` produces 7 components / 0 validated / PASS-WARN-ERROR 0-0-0 / 7 manual.

**Takeaway**

Coverage is a valid review artifact. Hardwise should fail only when evidence cannot be parsed or indexed, not when the
honest result is “we can import this project, but profile coverage is not there yet.”

---

## 2026-05-28 · V3.10 · MCU checks need a startup/debug slice, not a fake full MCU validator

**Symptom**

截图里的 `U8` 问题很像一个完整 MCU review：SWD、BOOT、NRST、电源、ADC、PWM、甚至外设复用和
固件配置都能展开。直接叫“MCU 验证”容易让人以为 Hardwise 已经能读懂完整 alternate-function
matrix 或 firmware。

**Root cause**

当前输入只有 schematic netlist + BOM identity + structured profile。它能稳定判断的是连接事实：
电源脚是否在 3.3 V rail、NRST/BOOT0 是否有默认态、SWDIO/SWCLK 是否接到期望 debug net、
少量 GPIO 是否有命名连接。它不能稳定判断固件里是否启用了某个 alternate function、时钟树是否正确、
启动模式是否符合量产流程，或 PCB 上 SWD 走线质量。

**Fix**

新增 `validation/mcu.py`，并把 family 明确命名为 `mcu_basic`。规则只输出 component-level checks：
`mcu_vdd_vdda_rail`、`mcu_vbat_rail`、`mcu_nrst`、`mcu_boot0`、`mcu_swdio`、`mcu_swclk`
和两个 fixture GPIO 连接检查。坏 fixture 只复现 SWDIO/SWCLK swap；nominal fixture 要求无
component ERROR；未知电压或 reset topology 只 WARN。

**Verification**

Focused tests cover SWDIO/SWCLK swap, nominal topology, wrong VDD, floating NRST, floating BOOT0,
unknown voltage/reset WARN, single-component CLI, batch UI, design-validator UI, and profile candidate matching.
Smoke path:
`uv run hardwise design-validator-ui tests/fixtures/allegro/mixed_controller_power_stage.net tests/fixtures/allegro/mixed_controller_power_stage_bom.csv --output /tmp/hardwise-v3.10-controller-workbench.html --index-output /tmp/hardwise-v3.10-controller-index.md --index-json /tmp/hardwise-v3.10-controller-index.json`.

**Takeaway**

MCU validation should grow by stable review slices. SWD/BOOT/RESET/POWER is a deterministic schematic slice;
firmware and full AF-matrix review are different input contracts and should wait for their own evidence layer.

---

## 2026-05-28 · V3.9 · Product-shaped entry should reuse the same validation truth

**Symptom**

目标截图是一个“设计验证器”工作台：打开项目后直接看到器件列表、验证摘要、问题卡片和报告详情。
而现有 `report-validator-ui-batch` 还要求手写 `REFDES=profile.json` 或 manifest，不像产品入口。

**Root cause**

Hardwise 已有两块能力但没有接成一条入口：`suggest_profile_candidates()` 能从 BOM identity
匹配本地 profile，`validator_multi_ui` 能渲染多器件工作台。缺的是项目级薄层，把 matched
profile 跑同一个 `validate_component_against_profile()`，同时把 no-profile/manual 行保留下来。

**Fix**

新增 `validation/project_index.py` 和 `report/project_validation_markdown.py`，再加 CLI
`design-validator-ui <netlist_or_pst> <bom>`。它自动匹配本地 profile、渲染深色静态工作台，
并可选输出 markdown/JSON project index。未匹配器件不会被隐藏或伪验证，而是进入 manual/no-profile
行。

**Verification**

`uv run hardwise design-validator-ui tests/fixtures/allegro/mixed_power_stage.net tests/fixtures/allegro/mixed_power_stage_bom.csv --output reports/design-validator.html --index-output reports/design-validator-index.md --index-json reports/design-validator-index.json`
输出 18 components / 3 validated / PASS-WARN-ERROR 1-0-2 / 15 manual。Browser snapshot confirms
the workbench has component index, validation cards, and U12 ERROR default detail. Full suite:
328 passed, 7 deselected; ruff clean.

**Takeaway**

截图级产品感不需要第二套判断逻辑。正确做法是把已有 deterministic truth object 接到更顺手的入口，
并把未覆盖范围显式暴露给 reviewer。

---

## 2026-05-27 · V3.8 · Bootstrap checks are topology checks, not timing checks

**Symptom**

目标截图里 gate driver 相关问题很诱人：自举二极管、半桥节点、HO/LO 输出、输入 PWM、
甚至死区时间和 MOSFET 损耗都能讲。但 V3.8 如果一次性做完这些，会把 schematic topology、
timing simulation、layout current loop 和器件热损耗混在一起。

**Root cause**

EG2132 这类 half-bridge driver 有一部分事实能从 schematic netlist + BOM + structured profile
稳定判断：VCC rail、HIN/LIN 是否连接、HO/LO 是否到 Q gate path、VS 是否在半桥开关节点、
VB/VS 是否有 bootstrap capacitor、bootstrap diode 是否明显低耐压。死区、栅极波形、开关损耗和
bootstrap 回路布局则需要时序、负载、MOSFET 参数或 PCB 几何，不属于当前输入。

**Fix**

新增 `validation/gate_driver.py`，只输出 `component_checks`。规则对确定事实给 PASS/ERROR：
`MBRA210LT3G` 在 24 V-class bootstrap path 中按低耐压 ERROR；缺电容、缺 gate load、VCC 超范围、
逻辑输入缺连接也 ERROR。对未知 diode rating 返回 WARN，不伪造确定结论。

**Verification**

Unit tests cover bad bootstrap diode, nominal bootstrap path, missing bootstrap capacitor, missing gate load,
unknown diode rating, VCC over-range, and missing HIN. CLI/UI tests verify `report-component-validation`,
`report-validator-ui-batch`, and `suggest-validation-targets` all surface EG2132.

**Takeaway**

新增 family template 时，先问“这个结论靠当前输入能不能稳定证明”。能证明的放进 deterministic
component checks；需要波形、布局或供应链的数据，宁可留在未来 scope，也不要靠报告文案补出来。

---

## 2026-05-27 · V3.7 · UI polish should not create a second validation truth

**Symptom**

V3.4/V3.6 的 batch HTML 已经能展示 `U1 PASS` 和 `U12 ERROR`，但观感仍像工程导出的
HTML artifact。要向目标截图靠近，很容易顺手在 UI 层重新组织甚至重新判断错误摘要。

**Root cause**

产品界面需要更好的信息层级，不需要新的判断层。Hardwise 的可信边界来自
`ValidationReport`：pin rows 和 `component_checks` 已经是 deterministic validation 的输出。
如果 UI 为了“看起来像报告”重新推理 D5/L1，截图会更像，但证据链会变脏。

**Fix**

把 `report/validator_multi_ui.py` 拆成 layout、assets、section helpers，UI 只读取既有
`ValidationReport`。V3.7 新增三栏工作台、issue-first 默认详情、中文章节、pin summary cards、
以及 `外围/拓扑检查` cards，但不改 `validate_component_against_profile()` 或 schema。

**Verification**

Focused UI/CLI tests assert the mixed fixture opens on `U12 ERROR`, includes product labels,
`1N4007W`, `6.8 uH`, and the scope boundary. Full suite, ruff, diff check, CLI smoke, and browser
visual check are part of the V3.7 closeout.

**Takeaway**

UI 可以重排证据，但不能发明证据。越接近产品形态，越要守住“报告只是同一个 truth object 的投影”
这个边界。

---

## 2026-05-27 · V3.6 · Candidate generation should show misses, not hide them

**Symptom**

V3.5 已经能从 YAML manifest 复现 U1/U12 的 batch validation，但下一步如果只输出
matched targets，很容易让人误以为 Hardwise 已经覆盖了整份 BOM。mixed fixture 里 D5、L1、
Q12、R76 和电容都没有 profile；这些“没覆盖”的事实本身也需要暴露出来。

**Root cause**

Profile candidate generation 是 evidence-indexing 问题，不是 validation 问题。它可以确定
“BOM identity 是否能和本地 profile part_number exact match”，但不能因此推断这个器件已经被审查。
如果隐藏 no-result/manual/ambiguous 行，reviewer 会失去 profile coverage 的边界感。

**Fix**

新增 `validation/profile_candidates.py` 和 `suggest-validation-targets`。默认 YAML 输出包含
`matched / no_result / ambiguous / manual_needed`，让候选和缺口一起出现；只有显式传
`--matched-only` 时，才输出 V3.5 可直接消费的最小 `project + targets[]` manifest。

**Verification**

Focused tests cover U1/U12 matched, peripheral no-result, passive manual-needed, duplicate-profile
ambiguous, missing profile directory, and CLI output. Smoke:
`uv run hardwise suggest-validation-targets tests/fixtures/allegro/mixed_regulators_bom.csv --profiles data/datasheet_profiles --output /tmp/hardwise-v3.6-target-candidates.yaml`
outputs `matched=2, no_result=8, ambiguous=0, manual_needed=0`.

**Takeaway**

自动化 profile assignment 的第一步不是“自动全过”，而是把能确定匹配的目标和无法匹配的缺口
放在同一张表里。这样后续 reviewer 或模型代理才知道自己站在哪块地上。

---

## 2026-05-27 · V3.5 · Explicit manifest before automatic profile matching

**Symptom**

V3.4 的 batch UI 已经能同时展示 U1 PASS 和 U12 ERROR，但命令行需要手写
`U1=data/datasheet_profiles/l78.json U12=data/datasheet_profiles/xl1509.json`。这对一次 smoke
足够，对跨电脑继续开发或让别人复现实验就太脆弱：target assignment 藏在 shell history 里。

**Root cause**

“哪些 refdes 应该用哪些 profile”是一个独立决策层。自动 profile matching 需要 BOM MPN
normalization、manufacturer/package disambiguation、document-index confidence 和人工确认策略。
如果 V3.5 直接自动猜，就会把 profile selection 的不确定性混进 deterministic validation，
让 U12 这种明确错误的证据链变得不干净。

**Fix**

新增 `validation/targets.py`，把 target parsing 收敛成一处：positional `REFDES=profile.json`
和 YAML manifest 都产出同一个 `ValidationTarget(refdes, profile_path)`。`report-validator-ui-batch`
新增 `--targets-manifest`，并拒绝 manifest 与 positional targets 混用。manifest profile path 仍按
当前工作目录解析，保持和旧 CLI 一致。

**Verification**

Focused tests cover parser errors, duplicate refdes, manifest CLI smoke, positional compatibility,
and mixed input rejection. Smoke:
`uv run hardwise report-validator-ui-batch tests/fixtures/allegro/mixed_regulators.net tests/fixtures/allegro/mixed_regulators_bom.csv --targets-manifest tests/fixtures/allegro/mixed_regulators_targets.yaml --output /tmp/hardwise-v3.5-mixed-ui.html`
outputs `PASS/WARN/ERROR=1/0/1` and HTML contains `U1 PASS`, `U12 ERROR`, `1N4007W`, and `6.8 uH`.

**Takeaway**

Manifest 是“显式人工选择”的可复现载体，不是 profile 自动匹配。先把选择记录下来，后续再让
matching layer 逐步给出候选和置信度，系统边界会清楚很多。

---

## 2026-05-27 · V3.4 · Multi-device UI still needs explicit profile assignment

**Symptom**

目标产品截图里左侧有很多器件、右侧有验证详情，很容易把 V3.4 做成“自动给全 BOM 找 profile
并全部验证”。但 Hardwise 当前只有 L78 和 XL1509 两个明确 family template；如果自动套 profile，
会把 datasheet matching、profile selection 和 validation 三个问题混在一起。

**Root cause**

多器件 UI 的关键不是自动判断所有器件，而是证明同一份 schematic/BOM artifact 可以承载多个
确定性 validation result。Profile assignment 本身是另一层问题：它需要 datasheet/document
match、MPN normalization、package disambiguation 和人工确认。V3.4 如果把这些提前合并，会破坏
V3.1-V3.3 已经建立的“一个 refdes + 一个 structured profile = 一个可审计判断”契约。

**Fix**

新增 `report-validator-ui-batch <netlist_or_pst> <bom> REFDES=profile.json [...]`，要求调用方显式
给出每个 refdes 的 profile。CLI 对每个 target 复用 `validate_component_against_profile()`，
再把多个 `ValidationReport` 交给 `report/validator_multi_ui.py` 渲染到同一个静态 HTML。mixed
fixture 同时包含 `U1=L7805` 和 `U12=XL1509-12E1`：U1 PASS，U12 ERROR。

**Verification**

Focused tests cover renderer and CLI batch output. Smoke:
`uv run hardwise report-validator-ui-batch tests/fixtures/allegro/mixed_regulators.net tests/fixtures/allegro/mixed_regulators_bom.csv U1=data/datasheet_profiles/l78.json U12=data/datasheet_profiles/xl1509.json --output /tmp/hardwise-v3.4-mixed-ui.html`
outputs `PASS/WARN/ERROR=1/0/1` and HTML contains `U1 PASS`, `U12 ERROR`, `1N4007W`, and `6.8 uH`.

**Takeaway**

显式 profile assignment 是这个阶段的保险丝。它让 UI 先变成多器件 review artifact，同时不假装
Hardwise 已经解决了全 BOM profile 自动匹配。

---

## 2026-05-27 · V3.3 · Buck validation needs component-level checks, not overloaded pin rows

**Symptom**

目标截图里的 U12 问题不是单纯“某个 pin 接错”：OUTPUT pin 的风险来自外围拓扑组合，
包括 switch node 上是否有电感、续流二极管是否为合适类型、以及电感值是否落在 datasheet
推荐范围。如果把 D5 和 L1 的结论硬塞进 Pin 2 的 summary，报告能看起来像目标截图，但数据
结构会把 pin fact 和 peripheral fact 混在一起。

**Root cause**

L78 的 V3.1 规则是 pin-local：VI/GND/VO 各自可以由 net name 和 profile limits 判定。Buck
converter 不一样：OUTPUT pin 是一个 topology anchor，真正要看的对象是同一 net 上的邻接器件。
这类结论需要和 pin rows 并列，而不是伪装成 pin-level verdict。

**Fix**

把 validation 拆成三层：`validation/pins.py` 保留 generic pin rules；`validation/dcdc.py`
只在 profile 明确为 XL1509/buck 时运行；`validation/types.py` 给 `ValidationReport` 增加
`component_checks`。XL1509 fixture 中，8 个 pin rows 仍然全部 PASS；overall status 由两个
component checks 拉成 ERROR：`D5=1N4007W` 非 Schottky-style diode，`L1=6.8uH` 低于 68uH
profile minimum。Markdown 和 static UI 都渲染 component checks，但不改变 L78 的 pin count 行为。

**Verification**

Focused tests cover bad fixture, nominal Schottky + 100uH, missing inductor, unknown diode WARN,
and wrong FB rail ERROR. CLI smoke:
`uv run hardwise report-component-validation tests/fixtures/allegro/xl1509_buck.net U12 data/datasheet_profiles/xl1509.json --bom tests/fixtures/allegro/xl1509_buck_bom.csv --output /tmp/hardwise-v3.3-u12-validation.md`
outputs overall `ERROR` with pin counts `8/0/0` and component check counts `0/0/2`.

**Takeaway**

用“pin-local checks + component-level topology checks”分层后，报告能接近产品目标截图，同时数据
结构仍然诚实：pin 没错就别把它标错，外围拓扑有问题就作为外围检查独立呈现。

---

## 2026-05-27 · V3.2 · A UI can be an artifact before it is a product surface

**Symptom**

目标界面里有 component list、验证摘要、单器件 detail 和报告下载。V3.1 已经能生成单器件
markdown，但工程师还不能像产品界面那样先扫器件列表、再点进一个器件看 pin validation 和
schematic nets。如果直接上完整 Web app，又会把 MVP 拉进 hosted state、WebSocket、canvas
和前端构建栈，偏离 pre-Layout schematic-review proof。

**Root cause**

V3.2 需要证明的是信息架构，而不是证明 Hardwise 已经是 SaaS。现有 repo 已有静态 HTML
报告模式，V3.1 也已经有 deterministic `ValidationReport`。最小正确路径是把同一组事实渲染成
单文件 HTML artifact：component index + selected detail + topology pane + scope boundary +
download link，而不是引入第二套 validation truth 或 PCB viewer。

**Fix**

新增 `src/hardwise/report/validator_ui.py`，渲染本地静态 validator UI。CLI 新增
`report-validator-ui <netlist_or_pst> <bom> <refdes> <profile.json>`：加载 Allegro schematic
topology，join schematic BOM identity，复用 `validate_component_against_profile()`，输出一个可直接
从磁盘打开的 HTML。UI 明确显示 scope：不解析 `.brd`、boardview、placement、routing、PCB geometry，
也不做 live supplier / PLM / lifecycle / pricing / availability。

**Verification**

Focused tests:
`uv run pytest tests/report/test_validator_ui.py tests/test_cli_validator_ui.py -q`
→ 3 passed；focused ruff clean。Smoke:
`uv run hardwise report-validator-ui tests/fixtures/allegro/l78_regulator.net tests/fixtures/allegro/l78_regulator_bom.csv U1 data/datasheet_profiles/l78.json --output reports/l78-validator-ui.html`
生成 component index + U1 detail 的 HTML，选中器件仍是 `PASS/WARN/ERROR=3/0/0`。

**Takeaway**

先把用户工作流压成 artifact，再决定是否需要真正的 app。对 Hardwise 这种评审节点工具来说，
静态 UI 已经能验证“工程师怎么扫读结果”，同时不会把边界滑到 boardview 或供应链产品。

---

## 2026-05-27 · V3.1 · Single-component validation needs a narrow deterministic join

**Symptom**

V3.0 已经能把 L78 datasheet pin facts 输出成 profile report，但它还不能回答“U1 这颗器件在
当前 schematic netlist 里接得对不对”。如果直接让模型根据 netlist、BOM 和 datasheet 文本写判断，
又会回到自由生成报告：位号、pin、net 和证据边界都不够可审计。

**Root cause**

单器件验证不是新的 parser，也不是新的 report renderer；它是一个 join：schematic topology 提供
refdes/pin/net，BOM 提供 MPN/value/manufacturer identity，structured profile 提供 pin function
和 voltage limits。只有这三层先 deterministic 对齐，PASS/WARN/ERROR 才能稳定复现。

**Fix**

新增 `src/hardwise/validation/component.py`，定义 `PinValidation` 和 `ValidationReport`，并实现
`validate_component_against_profile()`。V3.1 只支持窄规则：profile pin 是否存在、是否连接 net、
ground 是否接到已识别地网、power input 是否在结构化电压限制内、fixed power output 是否匹配
nominal voltage。CLI 新增 `report-component-validation`，先加载 Allegro schematic topology，
可选应用 schematic BOM identity，再对单个 refdes 渲染 markdown 报告。

**Verification**

Focused tests:
`uv run pytest tests/validation tests/report/test_component_validation_markdown.py tests/test_cli_component_validation_report.py -q`
→ 7 passed。Smoke:
`uv run hardwise report-component-validation tests/fixtures/allegro/l78_regulator.net U1 data/datasheet_profiles/l78.json --bom tests/fixtures/allegro/l78_regulator_bom.csv --output /tmp/hardwise-v3.1-u1-validation.md`
输出 `PASS/WARN/ERROR=3/0/0`，报告包含 VI/GND/VO、`datasheet:l78.pdf#p3/#p4/#p6`
和 scope boundary text。

**Takeaway**

先让一个器件家族的 deterministic report 站住，再扩展 MCU、gate driver、DCDC、MOSFET 或 connector。
Unsupported category 应该 WARN 给人工复核，而不是硬凑一个看似完整的 verdict。

---

## 2026-05-27 · V3.0 · Pin profiles are facts, not validation verdicts

**Symptom**

V2.9 之后路线图写着 V3.0 Pin Profile、V3.1 单器件验证报告。目标界面里已经有
PASS/WARN/ERROR，但如果 V3.0 直接输出 pin-level PASS/FAIL，就会跳过一个更基础的问题：
每个 pin 的名称、功能、限制和推荐拓扑是否已经被结构化、带来源地记录下来。

**Root cause**

Datasheet 证据有两种形态：长文本适合向量检索，结构化 pin facts 适合 deterministic comparison。
早期 `DatasheetProfile` 已经有 `abs_max/recommended/pin_function`，足够跑 DS001，但不够驱动
单器件 pin-level report。V3.0 需要先把 datasheet pin 表变成 schema，而不是让后续规则从 PDF
或自然语言里重新猜 pin function。

**Fix**

`DatasheetProfile` 保持 v1 JSON 兼容，新增 `PinProfile` 和 `pins[]`：每行包含
pin number/name/category/function/limits/recommended_topology/evidence。公开 `l78.json`
升级到 schema v2，包含 VI/GND/VO 三个 pin rows。新增 `report-pin-profile` 和
`report/pin_profile_markdown.py`，可以把 profile 渲染成 markdown pin summary/detail，
并在报告里明确不做 schematic validation、电气 PASS/FAIL、供应链/PLM 或 PCB 工作。

**Verification**

Focused tests: `uv run pytest tests/ir/test_profile.py tests/report/test_pin_profile_markdown.py tests/test_cli_pin_profile_report.py tests/ir/test_types.py tests/checklist/test_ds001.py -q`
→ 32 passed；focused ruff clean。Smoke:
`uv run hardwise report-pin-profile data/datasheet_profiles/l78.json --output /tmp/hardwise-v3.0-l78-pin-profile.md`
生成 3-pin profile report，包含 VI/GND/VO、`datasheet:l78.pdf#p3/#p4/#p6` source tokens 和
scope boundary text。

**Takeaway**

Pin validation 要建立在 pin facts 之上。V3.0 的价值是把 datasheet pin 表变成可审计输入；
V3.1 才应该把这些 facts 与 schematic netlist/BOM identity 结合，生成 PASS/WARN/ERROR。

---

## 2026-05-26 · V2.9 · Datasheet match should be an indexed evidence state, not a supplier search

**Symptom**

目标产品形态里有器件列表、datasheet 链接和单器件验证报告。如果 V2.9 直接做“自动找 datasheet”，
很容易滑到 live supplier search、PLM、生命周期/价格/库存，或者把“找到了文档”误写成“电路设计正确”。
这会偏离 Hardwise 的 pre-Layout schematic-review node，也会让公开样本 demo 变得不可复现。

**Root cause**

成熟验证器常常要求 netlist + BOM + datasheet/document source，但这三者不是同一层：
netlist 是 topology，BOM 是 component identity，datasheet/document link 是 evidence index。
V2.9 需要回答的是“这组 BOM item 有没有可用公开文档证据入口”，不是“供应链上哪家有货”或
“这个 pin 连接是否 PASS”。

**Fix**

新增 `src/hardwise/documents/`：`parse_document_index()` 读取本地 CSV/TSV document index，
支持 MPN/manufacturer/value/title/URL/path 等列别名；`match_documents_to_bom()` 按 BOM item
的 MPN 优先匹配，缺 MPN 时只接受 part-like value，passive 值如 `10K` / `100nF` 进入人工状态。
输出四种显式状态：`matched`、`no_result`、`ambiguous`、`manual_needed`，并用
`doc:<file>#line<N>` 记录来源。`report-allegro-bom --document-index` 渲染 summary 和 per-item
document rows；`--mismatch-only` 明确拒绝 `--document-index`，因为 mismatch triage 不渲染索引层。

**Verification**

Focused tests: `uv run pytest tests/documents tests/report/test_allegro_bom_markdown.py tests/test_cli_allegro_bom_report.py -q`
→ 16 passed；focused ruff clean。固定 synthetic fixture smoke:
`uv run hardwise report-allegro-bom tests/fixtures/allegro/pst tests/fixtures/allegro/document_match/bom.csv --summary-only --document-index tests/fixtures/allegro/document_match/docs.csv --output /tmp/hardwise-v2.9-document-smoke.md`
生成包含 `Datasheet / Document Match Summary`、`PN-123 datasheet` 和 `doc:docs.csv#line2` 的报告。

**Takeaway**

Document match 是证据索引层，不是 AI 判断层。先把“哪个 BOM item 对应哪份公开文档、证据状态是否唯一”
做成 deterministic artifact，后续 pin profile / single-component validation 才能在 source token 上继续推进。

---

## 2026-05-26 · V2.8 · Allegro+BOM reports need an index before they need a UI

**Symptom**

V2.7 的 Allegro+BOM intake report 在公开样本上已经做到 `4010/4010 matched`，
但完整报告超过 4000 行。它技术上完整，却不适合 reviewer 先扫一眼：如果每次都从
flat component table 开始，用户只能滚表找重点，也看不出哪些 prefix、BOM item 或
mismatch 类型值得优先看。

**Root cause**

商业设计验证器的界面先给 component list、状态摘要和可点击 detail，再展开单器件报告。
Hardwise 还没有 Web UI，但 markdown 也需要相同的信息架构：先 index，再 detail。
V2.8 的正确问题不是“马上生成 PASS/FAIL 验证结论”，而是让 netlist+BOM 的事实层能按
reviewer 的读图路径浏览，给后续 datasheet match、pin profile 和单器件验证报告留出
稳定入口。

**Fix**

`report-allegro-bom` 默认 full mode 保持可复现的完整 component table，同时新增
`Component Prefix Summary`、`BOM Item Groups` 和短 source token
（`bom:<file>#line<N>` / `design:<source>#<refdes>`）。CLI 新增 `--summary-only`
输出状态、前缀统计、BOM item groups 和 mismatch；新增 `--mismatch-only` 只输出状态与
BOM/design mismatch 章节。两种模式互斥，避免 ambiguous report shape。

**Verification**

Focused tests: `uv run pytest tests/report/test_allegro_bom_markdown.py tests/test_cli_allegro_bom_report.py -q`
→ 9 passed；focused ruff clean。公开 Allegro+BOM 样本 smoke 三种输出都为
`4010/4010 matched, 0 mismatches`：full report 4209 行，summary-only 194 行，
mismatch-only 27 行。

**Takeaway**

报告可读性不是 UI 才需要解决的问题。先把 markdown 组织成 index-first 形状，后面做
datasheet/document match、pin-level validation 和 Web UI 时才能复用同一套事实入口，
而不是让模型绕过 registry/BOM 直接生成看似完整的验证结论。

---

## 2026-05-26 · V2.7 · Allegro+BOM output must be component-centric intake, not net review

**Symptom**

V2.5/V2.6 已经能解析 Allegro/PST topology 并把 BOM refdes 全量 match 到
`Design.components`，但只打印 counts 还不能回答“现在能不能生成报告”。如果沿用早期
KiCad 的 net/规则视角，很容易把 Allegro netlist+BOM 输出做成 net-centric summary，
偏离用户要的器件角度。

**Root cause**

Allegro netlist-only 场景的第一份可交付物不是 electrical review finding，而是
component intake：先证明每个 refdes 在设计 registry 中存在、BOM identity 对得上、
每个器件有哪些 pins/nets，以及这些事实来自哪一行 BOM / 哪个 netlist source。只有
这一层可信了，后续 datasheet/profile/checklist 才有可靠 join key。把它叫 review 会
暗示已经做了电气规则判断；实际没有。

**Fix**

新增 `src/hardwise/report/allegro_bom_markdown.py` 和 CLI
`hardwise report-allegro-bom <netlist-or-pst> <bom>`。报告头记录 netlist/BOM/counts，
mismatch 章节列 BOM-only / design-only / duplicate / quantity mismatch，主体表按
design component 一行一个 refdes，包含 match status、value、MPN、manufacturer、
package、pin count、bounded nets、BOM source line 和 design source token。报告正文
明确不做 PLM、lifecycle、pricing、supplier-risk、layout、boardview 或 electrical-rule
review。

**Verification**

Focused tests cover renderer clean/mismatch paths and CLI report writing:
`uv run pytest tests/report/test_allegro_bom_markdown.py tests/test_cli_allegro_bom_report.py -q`.
公开 PST+BOM 样例 smoke：
`uv run hardwise report-allegro-bom "<public sample>/allegro" "<public sample>/SWITCH BOARD 144-VA_20240712 1401.BOM" --output reports/public-allegro-bom-intake.md`
输出 `4010/4010 matched, 0 mismatches`，生成 4042 行 component-centric intake report。

**Takeaway**

“能生成报告”不等于“能做完整评审”。V2.7 的正确交付物是可追溯的器件事实清单，
把 netlist topology 和 BOM identity 组织成 reviewer 能扫读的入口，同时守住
pre-Layout schematic-review scope。

---

## 2026-05-26 · V2.6 · BOM refdes shape must follow the EDA registry

**Symptom**

V2.6 第一版 BOM parser 用了“位号必须包含数字”的正则，解析公开 Cadence `.BOM` 时把末尾的 `VA` 漏掉了。PST registry 里实际存在 `VA` 这个 placed part，导致 BOM 展开为 4009 rows，而 netlist Design 有 4010 components；join 结果出现一个 design-only refdes。

**Root cause**

Refdes Guard 的输出扫描正则适合拦截模型文本里的常见 `U1/R2/C3`，但 BOM parser 不能直接套同一个形状。BOM 的 Reference column 是 EDA 导出的对象列表，合法性应该由 `Design.refdes_set` 兜底，而不是由窄正则提前排除。真实 EDA 里会有 `SOCKET1`、`TH1`，也会有少数无数字但 registry-valid 的 designator。

**Fix**

新增 `src/hardwise/bom/`，拆成 `types.py` / `parser.py` / `matcher.py`：parser 读取 Cadence `.BOM` 和简单 CSV/TSV，展开跨行 Reference；matcher 用 refdes join 到 `Design.components`，报告 matched / BOM-only / design-only / duplicate / quantity mismatch；`apply_bom_to_design()` 只补 value/manufacturer/part_number/properties，不修改 nets/pins。CLI 新增 `inspect-bom-match`，明确输出 scope 是 component identity match only。

**Verification**

`uv run pytest tests/bom tests/test_cli_bom_match.py -q` 覆盖 parser/matcher/CLI。真实公开样例：`uv run hardwise inspect-bom-match "<public sample>/allegro" "<public sample>/SWITCH BOARD 144-VA_20240712 1401.BOM"` 输出 4010 design refdes / 4010 BOM rows / 4010 matched / 0 mismatch。Final gate: `uv run pytest -q` 和 `uv run ruff check .` clean。

**Takeaway**

BOM matcher 是 identity layer，不是 refdes 形状裁判。宽一点提取候选，再让 EDA registry 验证，比在 parser 正则里猜所有公司的命名习惯更稳。

---

## 2026-05-26 · V2.5 · Allegro netlists give topology, BOM gives identity

**Symptom**

V2.5 最初只写了 Allegro `$PACKAGES + $NETS` adapter。Grok Search 调研 EDA.cn / 华秋设计审查工具和 CADY 后发现，成熟产品的 non-native EDA 入口通常是 **netlist + BOM**：网表负责连接关系，BOM 负责器件型号 / MPN / datasheet 匹配。随后公开 Allegro 样本暴露出另一个现实格式：OrCAD/Capture 到 Allegro 的常见导出不是 Telesis 单文件，而是 PST 三件套 `pstxprt.dat` / `pstxnet.dat` / `pstchip.dat`。

**Root cause**

把 “Allegro support” 说成单一 parser 很容易滑偏：如果只解析一种网表，会漏掉真实 Capture/Allegro handoff；如果把 BOM 解析塞进 netlist adapter，又会污染 EDA boundary。正确分层是：adapter 只读 EDA 导出的结构事实；BOM 是 component-matching layer，用 refdes join 到 `Design.components`。

**Fix**

新增 `src/hardwise/adapters/allegro_netlist.py`，按 Telesis / Allegro third-party ASCII netlist 解析 `$PACKAGES`、optional `$A_PROPERTIES`、`$NETS`，支持 quoted names、comma-separated lists、trailing-comma continuation，并对 duplicate refdes、unknown net refdes、pin on multiple nets 直接报错。又新增 `src/hardwise/adapters/allegro_pst.py`，解析 Capture/Allegro PST 的 `pstxprt.dat` placed parts、`pstxnet.dat` nets / `NODE_NAME` endpoints、可选 `pstchip.dat` primitive properties。两条路径都聚合成 `Design(source_eda="allegro_netlist")`，只填 components / nets / connected pins；datasheet 字段保持空，等待后续 BOM matcher 或 profile 层补。

**Verification**

`uv run pytest tests/adapters/test_allegro_netlist.py tests/ir/test_build_allegro_netlist.py tests/adapters/test_allegro_pst.py tests/ir/test_build_allegro_pst.py tests/test_cli_allegro_netlist.py -q` covers both adapters and CLI detection. `uv run hardwise inspect-allegro-netlist tests/fixtures/allegro/minimal_third_party.net` 输出 4 components / 4 nets；PST fixture 输出 3 components / 3 nets / 9 properties。公开 PST 样本目录输出 4010 components / 3422 nets / 12030 properties，最大网 `GND` 有 5973 members。Final gate: `uv run pytest -q` 和 `uv run ruff check .` clean。

**Takeaway**

网表不是 BOM，BOM 也不是 PLM。对 Hardwise 来说，Telesis/PST netlist 是“谁连谁”的 topology，BOM 是“这个位号到底是什么器件”的 identity。二者都重要，但必须分层接入。PST 里名为 `NC` 的 net 也仍然只是一个 net name，不能自动等价成 datasheet no-connect pin 结论。

---

## 2026-05-26 · CLI · Typer Path turns empty db path into current directory

**Symptom**

V2.5 closeout 验证 KiCad regression 时，我按 CLI help 写法跑 `--db-path ''` 想跳过 SQLite store，结果 Typer 把空字符串解析成 `Path('.')`，review 试图 `unlink('.')`，触发 `PermissionError: Operation not permitted: '.'`。报告本身已经生成了 28 findings，但 auxiliary store 阶段失败。

**Root cause**

`db_path` 参数声明成 `Path | None` 太早做了路径 coercion，空字符串不再是可区分的“用户想跳过”，而变成当前目录。help 文案和实际行为不一致。

**Fix**

把 `review --db-path` 的参数类型改成 `str | None`，新增 `_review_db_path(project_name, db_path)`：`None` -> `reports/<project>.db`，空/空白字符串 -> `None`（跳过 store），其他值 -> `Path(value)`。新增 `tests/test_cli_helpers.py` 锁住三条路径。

**Verification**

`uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003 --no-consolidate --db-path '' --no-run-trace` 现在只输出 report 行，不再写 store；同一次也验证了 KiCad baseline 仍是 28 findings / 121 components reviewed。

**Takeaway**

CLI 里“空字符串有业务含义”时不要让 Typer 先转成 `Path`。先保留为 `str`，在业务 helper 里归一化，行为会更可测试。

---

## 2026-05-26 · V2.4 · Datasheet profile must follow PDF evidence, not old plan text

**Symptom**

V2.4 spec 草稿写着 L78 `abs_max.vin` evidence 指向 `l78.pdf#p2`，但实际用 `pdfplumber` 抽 `data/datasheets/l78.pdf` 时，page 2 是 block diagram，真正的 "Absolute maximum ratings" 表在 PDF 第 4 页。

**Root cause**

计划里的页码是早期草稿，不是可验证 source token。Hardwise 的证据规则要求 finding 指向真实来源；如果为了满足计划文本把 profile 写成 `#p2`，DS001 会看起来“验收通过”，但 provenance 是错的。

**Fix**

`DatasheetProfile` 落成 Pydantic JSON model，`data/datasheet_profiles/l78.json` 使用真实 token：`datasheet:l78.pdf#p4`。`ingest-datasheet --extract-profile` 走 deterministic L78 extractor，不依赖 live LLM；`DS001` 只在请求该 rule 时运行，U3 因缺少 schematic-side Vin net 电压输出 `reviewer_to_confirm`，不猜应用电压。

**Verification**

`uv run pytest -q`：215 passed, 7 deselected。`uv run ruff check .` clean。`hardwise review ... --rules R001,R002,R003` 仍是 28 findings；`--rules R001,R002,R003,DS001 --report-style component` 是 29 findings，其中新增 U3 / DS001 / `datasheet:l78.pdf#p4`。`ingest-datasheet data/datasheets/l78.pdf --extract-profile` 写出 profile JSON。

**Takeaway**

Datasheet-driven checks 的核心不是“把 PDF 摘成 JSON”，而是 JSON 里的每个数字都能回到真实页码。计划文本可以错，source token 不能跟着错。

---

## 2026-05-26 · V2.3 · Component report should expose structure without changing truth

**Symptom**

V2.2 已经把内部调度改成 `Design.components -> CheckSpec`，但 classic report 仍然是 flat finding table。面试演示时看不到“先按元件归拢，再看每个元件的证据和 pin finding”的 V2 价值；如果直接替换默认报告，又会让已有 e2e / demo 文档承担不必要的行为变更。

**Root cause**

报告格式是产品界面，不只是代码输出。classic report 对齐《SCH_review_feedback_list 汇总表》，适合回归和交付；component-centric report 对齐工程师读图习惯，适合审阅和面试展示。两者应该共享同一组 `Finding` 和 evidence token，而不是分裂出两套 truth。

**Fix**

新增 markdown-only `--report-style component` 和 `src/hardwise/report/component_markdown.py`。classic report 保持默认；component report 读取同一个 `Design`，先输出 121 个 component summary，再只展开有 finding 的 component。`CheckSpec` runner 给 `Component.decision` 写 `pass|warn|fail` rollup，报告不重新发明判定。

**Verification**

`uv run pytest -q`：203 passed, 7 deselected。`uv run ruff check .` clean。classic CLI 仍输出 28 findings / 121 components reviewed；component CLI 用独立 db path 复跑，同样输出 28 findings / 121 components reviewed，并在 report 中出现 `Component Summary`、`### U4 - LT1373` 和 U4 pin 3 的 R003 row。

**Takeaway**

一次架构迁移最好先让新视角“可选可见”，再决定是否改默认体验。这样既能展示 component-centric 的产品价值，也不会把格式变更误判成规则行为变更。

---

## 2026-05-26 · V2.2 · Per-component dispatch needs a provenance bridge

**Symptom**

V2.1 的 `Design` 已经把对象图切成 `Component -> Pin`，但 R001/R002/R003 的真实证据 token 仍然依赖 `ComponentRecord.source_file` / `NcPinRecord.source_file`。如果 V2.2 直接让规则只吃 `Component`，报告可以跑，但 `sch:...#refdes` 这类 provenance 会被削弱。

**Root cause**

IR 层先解决“按元件分发”的对象边界，parse-level registry 仍然保存“证据来自哪个文件”的边界。两者不是重复数据：`Design` 是 review 工作台，`BoardRegistry` 是 EDA 台账和 source token 来源。V2.4 之前强行把所有 provenance 塞进 `Pin` / `Component`，会扩大 IR scope。

**Fix**

新增 `CheckContext(registry, collection)` 作为桥：V2.2 runner 访问 `Design.components` 并调用 `CheckSpec(Component, Design, CheckContext)`，规则内部通过 context 回查 raw schematic record / NC pin record 来生成原有 evidence token。`Finding.pin_number` 作为向后兼容可选字段落地，R003 pin-scoped finding 会同时挂到 `Component.findings` 和匹配的 `Pin.findings`。

**Verification**

`uv run pytest -q`：198 passed, 7 deselected。`uv run ruff check .` clean。`uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003` 仍输出 28 findings / 121 components reviewed；V2.2 snapshot test 锁住 R002 六个电容和 R003 相关 refdes surface。

**Takeaway**

架构迁移可以先换“调度方向”，不必同一刀搬完所有数据所有权。对硬件评审来说，component-centric 是工作流视角；source-token registry 是证据视角，两者通过窄 context 连接，比把 provenance 到处复制更稳。

---

## 2026-05-16 · Submission closeout · 停止用功能数量证明项目价值

**Symptom**

Hardwise 已经能跑 `review`、`ask`、eval smoke、trace、HTML report 和双库，但 README / PLAN / interview answers 仍然残留“继续补 R004/R005、继续扩平台”的语气。项目看起来像没做完的大系统，而不是已经收束的 portfolio MVP。

**Root cause**

最初的叙事把五大机制、五条规则、双库、prompt cache、consolidator、eval harness 都放到同一层级。这样会稀释真正的主张：硬件评审 Agent 的可信度首先来自对象层和证据层约束，而不是规则数量。R004/R005 又依赖 schematic-side net parser，一旦把它们当提交门槛，项目会重新滑回无底洞。

**Fix**

README 改为 “Core Proof”：Refdes Guard、Evidence Ledger、Structured Tool Loop 是主角；Sleep Consolidator、Tiered Routing、Prompt Caching 降级为 supporting mechanisms。PLAN 增加 Submission boundary，明确 R004/R005、GitHub Action、larger gold-label eval、Cadence/Allegro adapter 都是 post-MVP。interview_qa 增加 final answer shape，把 Q6 改成“先补可信度和可交付性，不先加更多规则”。

**Takeaway**

项目收束本身就是工程判断力。两周 MVP 的价值不是证明“我能把硬件评审平台做大”，而是证明“我知道哪些部分可解、哪些部分不能在当前证据条件下硬讲”。功能数量是配角，trust boundary 是主线。

---

## 2026-05-16 · Synthetic must-catch · MVP 先锁 false negative safety floor

**Symptom**

Noise-Control Harness v0 已经能在 public corpus 上给出 decision 分布，但它仍然不能单独证明“已知重大问题不会漏”。Public corpus 是真实工程压力测试，不是专家 gold-label 答案集；人工标注 calibration 又需要额外定义标准和投入时间。

**Root cause**

MVP 的验证目标被拆成两类：public corpus 证明真实项目可复现、能定位 regression；synthetic must-catch 证明关键已知场景不会在 rule 演进中退化。前者是广度，后者是安全底线。把这两件事混成一个“准确率”指标，反而会让招聘叙事变虚。

**Fix**

新增 `tests/harness/test_must_catch.py`，用最小 `ComponentRecord` / `NcPinRecord` / `BoardRegistry` 构造 5 个产品级 must-catch 场景：R001 新器件无 footprint、R002 电容缺 `/V`、R002 电容已有 `/V` 不报、R003 IC NC 无 datasheet → `reviewer_to_confirm`、R003 connector 批量 NC → 1 条 `likely_ok` low finding。为支持最后一条，R003 connector summary 补了一条 EDA `evidence_chain`，不引入 datasheet 证据。

**Takeaway**

Synthetic cases 不是为了替代真实 corpus，而是给 harness 加一块可自动回归的 safety floor。MVP 阶段先保证“已知关键问题不能漏、已知低价值提醒不能回流”，比先做 20-30 条人工标注更直接；human-labeled calibration 仍然是下一层，用来量化 precision/recall。

---

## 2026-05-16 · Noise-Control Harness v0 · finding 数不够，还要看 decision 分布

**Symptom**

Public corpus harness 已经跑出 5 repos / 6 个有 components 的 KiCad projects / 1707 components / 437 findings，另有 10 个空 KiCad directory 被标成 skipped；总数本身不能回答硬件工程师真正关心的问题：哪些是明确需要修的字段，哪些只是证据不足需要确认，哪些是连接器/模块上通常合理的低优先级提示。

**Root cause**

R001/R002/R003 的 rule 输出里已经有 `decision` 字段，但 public eval 主要看 `findings_by_rule` 和 guardrail 计数。也就是说 harness 能证明“没有崩、没有 refdes 幻觉”，但还不能证明“没有把 reviewer 注意力浪费在低价值提醒上”。另外 R002 旧行为会对已写 `/V` 后缀的电容生成 info finding；这在单 demo 里有教学价值，但放到 corpus 噪音控制里会消耗注意力。

**Fix**

- R001 空 footprint 写 `decision=reviewer_to_confirm`。
- R002 只对缺额定电压后缀的电容生成 `likely_issue`；已有 `/V` 后缀不再生成 finding。
- R003 在 registry-only eval 路径里给 IC/module NC 写 `reviewer_to_confirm`，connector-like NC summary 写 `likely_ok`。
- Eval summary 增加 `findings_by_rule_decision: dict[str, dict[str, int]]`，HTML 增加全局 + per-rule 两张 decision 表，CLI 输出 decision counts + percentage。
- 完整 public smoke 当前 decision split：298 likely_issue / 99 reviewer_to_confirm / 40 likely_ok / 0 undecided。
- 完整 public corpus checkout 后，pytest 会递归进第三方 repo 自带测试；本地 `.claude/worktrees` 也会制造重复 test module。把 `eval/projects` 和 `.claude` 加入 pytest `norecursedirs`，与 Ruff exclude 保持同一边界。

**Takeaway**

Eval harness 的第一层是可重复跑，第二层是 guardrail 不退化，第三层才是 attention allocation。MVP 不需要先做大 gold-label 数据集；先把机器结论分桶，让每次 rule 调整都能看到 likely_issue / reviewer_to_confirm / likely_ok 的迁移方向。`likely_ok` 占比高不自动代表系统过度乐观，公开 corpus 里 connector/header/module 多时它会自然偏高，关键是 per-rule matrix 能定位这种偏差来自哪里。

---

## 2026-05-16 · P0 trace.jsonl · 运行记录不能从 CLI stdout 反推

**Symptom**

准备做 `rules list` 时，现有 `review` 只把运行结果分散在三处：人读的 report、stdout 的 `report/store/consolidator` 行、以及可能追加的 `memory/rules.md`。这些都能看，但都不是稳定 API。后续如果先拆 CLI 或直接做 rules list，很容易把展示逻辑绑死在 Typer 输出文本上。

**Root cause**

少了一个"运行记录 ledger"层。Report 是给硬件评审会议看的，stdout 是给当前终端用户看的，`memory/rules.md` 是候选规则池；三者都不是"一次 review run 的机器可读事实表"。把 rules list 建在这些文本上，等于把后续 CLI 结构绑定到当前文案。

**Fix**

新增 `src/hardwise/run_trace.py`：

- `ReviewRunTrace` Pydantic schema 固定一行 JSONL 的字段；
- `ReviewRunSummary` 先在 CLI 内收束结构化运行事实，避免从 stdout 反推；
- `build_review_trace()` 记录 requested/rules_run、report path、components/NC pins、findings by rule/severity/decision、guard 计数、vector/store/consolidator 结果；
- `append_jsonl()` 追加到 `<report-dir>/trace.jsonl`；
- `hardwise review` 默认写 trace，支持 `--trace-output PATH` 和 `--no-run-trace`；
- trace 写失败只打 stderr warning，不阻塞 report/store/memory 主流程；
- 单测锁 schema/counting，E2E 锁默认写入与关闭路径。

**Takeaway**

CLI stdout 不是内部接口。凡是后续命令要消费的事实，先写成结构化 artifact，再决定怎么展示。`trace.jsonl` 现在是 rules list / demo run history / audit view 的共同输入，CLI split 只是把调用点搬家，不应该改变记录格式。P0 先接受路径不规范化和无文件锁：这是单人本地 demo 的合理简化，等并发运行或跨目录聚合出现再补。

---

## 2026-05-15 · Slice 5 task 3 · "net parser" 实际读的是 `.kicad_pcb`，与 pre-Layout 评审锚点冲突——降级为 PCB-side diagnostic

**Symptom**

按 Slice 5 task 3 的工单实现了 `parse_nets()` + `BoardRegistry.nets` + SQLite `nets/net_members` + `inspect-kicad --net`，跑 `pic_programmer` 输出 111 nets（34 signal + 77 unconnected），ruff/pytest 全绿。功能上完全正常。但写完准备登记 docs 时被一句话拦下：「评审阶段还没有 pcb 文件」。一翻代码，`parse_nets()` 里 `for pcb_path in sorted(project_dir.glob("*.kicad_pcb"))` 写得明明白白——这个 parser 的输入是 `.kicad_pcb`，是已布完线的 PCB 文件。

**Root cause**

把 KiCad demo 项目的「项目目录里碰巧 PCB 已经画完」当成了 schematic-review 节点的合法输入。CLAUDE.md 的 Hard rule #5 明文写「Demo anchor: schematic-review node only ... 任何 cross-node feature ... 是 out of scope」，`docs/review_node.md` 也定义了节点输入只有 `.kicad_sch` + datasheet + checklist。但 demo 数据集 `pic_programmer` 里 `.kicad_sch` 和 `.kicad_pcb` 同时存在——不写一行话明确「parser 拒绝读 `.kicad_pcb`」，就会自动顺着 KiCad 文件结构走最容易解析的那一面（PCB 里 net 是显式聚合好的；schematic 里 net 是 wire + label + hierarchical label + symbol pin endpoint 拓扑推断出来的，难度高一个量级）。

**HW analogy**：QA 阶段还没有第一版 PCB，但工程师拿到了上一版的 layout 数据，于是用它「先验证一下 net 拓扑工具好不好用」——工具确实能跑，但 QA 流程的合法证据来源被悄悄掉包了，下游谁拿这份「net 拓扑结论」去查 R005 dangling-net 都是无效证据。

**Fix**

不删现有实现——它对「已完成 KiCad 项目的 PCB 网络读取 / SQLite round-trip 证明」是有价值的。但立刻降级它的叙事地位、改名防止误用：

- `parse_nets` → `parse_pcb_nets`，docstring 显式标「Not valid as pre-Layout schematic-review evidence」
- `NetRecord` → `PcbNetRecord`；`BoardRegistry.nets` → `pcb_nets`（为未来 `schematic_nets` 留位）
- SQL 表 `nets / net_members` → `pcb_nets / pcb_net_members`；`query_nets` → `query_pcb_nets`
- `signal_nets` / `is_unconnected_net` → `pcb_signal_nets` / `is_unconnected_pcb_net`
- CLI `inspect-kicad --net` 的 header 加一行 `source: .kicad_pcb (post-Layout fact; not pre-Layout review evidence)`
- `docs/rolling_log.md` 把 R005 dangling-net 的前置条件改成「需要 schematic net parser（wire + local/global label + hierarchical label + symbol pin endpoint 解析）」，不能凭 PCB-side 数据上 R005

**Takeaway**

Pre-Layout 评审节点的合法证据来源**只有** `.kicad_sch` / datasheet / checklist。任何新 parser 写完前先问一句「这个 parser 读的是哪个文件后缀？是不是评审节点那一刻能拿到的？」KiCad demo 项目「碰巧 PCB 已画完」是数据集污染，不是输入合法性的依据。CLAUDE.md 里 Hard rule #5 加一句「pre-Layout 评审证据只能来自 `.kicad_sch` / datasheet / checklist」会更难走错——但 CLAUDE.md 是 reference 不是 changelog，本身已经隐含了这条，更落地的做法是任何 PCB-side parser 函数名都带 `pcb_` 前缀，让命名层就拒绝混淆。

---

## 2026-05-14 · Slice 5 prep · R003 datasheet 闭环上线后，77 条 finding 全部 `reviewer_to_confirm`——这是对的

**Symptom**

`hardwise review data/projects/pic_programmer --rules R003 --vector --no-consolidate` 跑完，77 条 NC pin finding **全部** 拿到 `decision=reviewer_to_confirm`，没有一条 `likely_ok` 也没有 `likely_issue`。从启发式的角度看，似乎是规则失效——明明 Chroma 里有 157 个 L78 datasheet chunks，应该至少对 L78 相关 NC pin 触发一些 `likely_ok` 才对。

**Root cause**

不是规则失效，是**数据匹配问题在结构层面就已经无解**。两层错配并存：

1. **唯一 ingest 的 datasheet 对应的部件没有 NC pin**：Chroma 里只有 L78 (`part_ref="U3"`, 157 chunks)。L78 是 3 pin 线性稳压器（IN/GND/OUT），物理上不存在 NC pin。pic_programmer 真正出现 NC pin 的器件是 U4 (PIC16F627) 和 J1 (DB-9 connector)——这两个的 datasheet 没 ingest。
2. **part_ref 命名约定还不统一**：早期 `hardwise ingest-datasheet --part-ref U3 ...` 用了 refdes 作为 part_ref；R003 这一版按 DR-009 设计走 `component.value` 推 part_ref（典型值是 `LM7805` / `PIC16F627` 这种部件型号）。两条约定不在同一个 namespace 里，filter 会全部 miss——但 R003 的回退路径会在 "filter 0 hit → 用未过滤 top-k" 时让 L78 chunks 进入候选；问题是 L78 chunks 文本里根本不会出现 "pin 17" / "pin 18" 这类 PIC 的 NC pin 编号，所以 `\bpin\s*N\b` 正则全部不匹配，整段判断落到 `reviewer_to_confirm`。

也就是说：**(a) 没数据可证 (b) 仅有的数据跟问题不在一个语义平面**。两个原因任一存在都会让 R003 输出 `reviewer_to_confirm`——这正是规则的「无证据时不瞎判」分支应有的响应。

**HW analogy**：板子飞线测试时只接了 X 通道的探头，结果发现 Y 通道全部「无信号」就喊故障——根本就没采到 Y 通道，无信号才是正确的测量结果，不是 DUT 坏。

**Fix**

不"修"这个现象——它本身是规则正确分支的体现。但落地两件事让证据明确：

1. **interview_qa Q3 v4.0 把这个负样例当作设计正确性证据写进去**：「没有可用证据时输出 `reviewer_to_confirm` 比编一个 `likely_ok` 出来更有可信度，这是 Layer 1 工具事实通道 + Layer 2 启发式分类之外的第三道安全设计——规则自己的『不知道』分支」。
2. **rolling_log 加一条**：要让 likely_ok / likely_issue 的真实数字出现在 demo 上，需要 ingest 一份覆盖 PIC16F627 NC pin 的 datasheet，并把 ingest 端的 part_ref 约定显式锁到 `component.value`（不能再用 refdes）。这条「补 datasheet」工作纳入 Slice 5 之后的 demo polish，不阻塞 A4 收口。

**Takeaway**

1. **「规则跑出 0 个正样例」≠「规则失效」**。一个有 NC handling 闭环的 rule，在没有覆盖该部件的 datasheet 时**就应当**全输出 `reviewer_to_confirm`。Demo 上拿到这种诚实输出，比 demo 出 7 条假阳性更能说明系统设计可信。
2. **启发式分类必须有第三个 fallback bucket**（这里是 `reviewer_to_confirm`）。如果只有 `likely_ok` / `likely_issue` 二选一，规则在证据不足时必然乱判——没有第三个 bucket 的设计是「装作什么都知道」，跟 hallucination 性质上等价。
3. **数据约定（ingest 端 part_ref）和数据消费（R003 端 part_ref）必须在同一个 namespace**。本次的 mismatch 说明 namespace 没文档化时，DR-009 落地等于在错配数据上跑——结构没错，数据不在。下一个 ingest 工具升级要把 `--part-ref` 约束到 `component.value` namespace 并加校验。

---

## 2026-05-14 · Slice 5 prep · sanitizer 在 part number 上的 false positive 是 spec 的必然，不是 bug

**Symptom**

把 Layer 2 sanitizer 从 cli ask 单点搬到 runner 出口 + ToolCallTrace 副本之后，原本绿的 `test_runner_text_only_returns_text` 红了：模型 fixture 的回答 `"U3 是 LM7805 稳压器"` 出口被 wrap 成 `"U3 是 ⟨?LM7805⟩ 稳压器"`。LM7805 是 LDO 的标准部件型号，不是 refdes，**不应该**被 wrap——但 wrap 了。

**Root cause**

CLAUDE.md 硬规则 #3 把 refdes 形状定死成 `\b[A-Z]{1,3}\d{1,4}\b`。这条正则在**意图**上是覆盖 KiCad refdes（U3 / IC1 / R10 / J5 / BAT1），在**语法**上它同样命中所有 "1-3 个大写字母 + 1-4 个数字" 的连续 token——LM7805、BC547、STM32、NE555 全中。Sanitizer 在做 `registry.has_refdes(...)` 时这些 part number 都不在 refdes_set 里，于是全部 wrap。

regex 本身没分辨 refdes 和 part number 的能力，因为两者在 token 层面**形状重合**——靠 regex 区分是不可能任务。

**HW analogy**：跟 layout 阶段 "DFM 报警把所有走线都标了" 一样——规则书写得太宽，把"可能违规"和"实际违规"都圈进来。要么修规则，要么接受 over-report 然后人审。

**Fix**

不修 regex（CLAUDE.md spec 锁了，改它要 amend），而是**接受 over-wrap 作为 Layer 2 的设计 trade-off**：宁可把 part number 也包成 `⟨?LM7805⟩`，也不要漏掉 hallucinated refdes（这是 hard rule #3 的安全方向）。两个失败测试更新断言反映新行为；新加的 `test_verified_refdes_passes_through_untouched_everywhere` 在 fixture 文本里避开了 part number，专门测「所有 token 都是已 verify refdes 时的 0-wrap 通路」。

**Takeaway**

1. **Regex sanitizer 的语法形状是"宁包错不漏"的安全侧。** 一个 over-wrap 的 part number 顶多让 UX 难看（reviewer 看到 `⟨?LM7805⟩` 知道这是规则在保险）；一个漏过的 hallucinated refdes 直接让 hard rule #3 失效。两条路上，规则书必须站在严格那一侧。
2. **defense-in-depth 的两层不是平等的。** Layer 1（工具事实通道）才是"事实层"——`get_component('U999')` 返回 `{found: false, closest_matches: [...]}` 是 ground truth。Layer 2 sanitizer 是"显示层"的保险，它没有义务区分语义——它只负责把所有"未在 registry 出现的形状匹配 token"打上未验证标记。语义判断（这是 refdes 还是 part number）应该回到 Layer 1（工具调用）去解决——例如未来可以让 `list_components` 同时返回 part numbers，或者在 prompt 里教模型"part number 写完整名字，refdes 用反引号包"。
3. **Pre-existing 测试在 fixture 里埋着对"无副作用"的隐含假设。** 当 runner 行为变化（从透传到 sanitize），靠 fixture 里的 part number 漏出来的不是 bug，而是**测试断言陈述的旧合同已经过期**。修测试比修代码合理——这种修测试不是迁就实现，是让断言反映新的真实合同。

---

## 2026-05-16 · Prompt cache cold-start follow-up：MiMo 有 read hit，但不暴露 creation 计数

**Symptom**

Slice 4 的 prompt-cache 证据已经有 `cache_read_input_tokens` 非零，但此前 `cache_creation_input_tokens` 一直是 0。为了补"第一次写 cache"这条链路，今天用唯一 system prompt 做 cold-start probe：同一个 cacheable prompt 连续请求两次，期望第一轮 creation 非零，第二轮 read 非零。

**Probe**

用当前 `.env` 的 MiMo Anthropic-format endpoint（`ANTHROPIC_BASE_URL=https://token-plan-sgp.xiaomimimo.com/anthropic`，model=`mimo-v2.5`）跑无 tools 的最小探针，避免 Hardwise 的稳定 `tools` schema 先命中缓存前缀。raw `response.usage.model_dump()`：

| run | input | output | cache_creation_input_tokens | cache_read_input_tokens |
|---|---:|---:|---:|---:|
| 1 | 5445 | 16 | `null` | `null` |
| 2 | 5 | 16 | `null` | **5440** |

同日也跑了 Hardwise payload（`pic_programmer`，唯一 nonce system prompt），结果仍然是 read hit 而 creation 不回传：例如 `U4` 问答第一轮 `cache create/read=0/1536`，第二轮 `0/3072`。

**Conclusion**

MiMo proxy 的 prompt cache read path 是实的：第二次同 prompt 请求只收 5 个 input tokens，并返回 `cache_read_input_tokens=5440`。但它当前不暴露 creation accounting：cold prompt 第一轮只是把 5445 tokens 算进普通 `input_tokens`，`cache_creation_input_tokens` 仍是 `null`，不是非零。

这意味着 README / interview answer 不能写"cache_creation 已验过非零"。准确说法是：Hardwise 的 `cache_control` wiring 与 `cache_read` 命中已在 MiMo 上实测；严格的"creation 非零 + 紧跟 read 命中"审计需要换一个会回传 creation 字段的 endpoint（官方 Anthropic API 或另一个 Anthropic-compatible provider）。当前 `.env` 的 key 是 MiMo proxy key；直连 `https://api.anthropic.com` 返回 `401 invalid x-api-key`，所以今天无法完成官方端复验。

**Takeaway**

兼容协议不等于兼容观测面。第三方 proxy 可以执行 server-side cache，同时不完全复刻官方 usage accounting 字段；面试时要把"机制生效"和"字段级审计"分开讲，前者有实证，后者仍是供应商可观测性缺口。

## 2026-05-13 · Slice 4 · MiMo 代理也认 Anthropic `cache_control`，prompt cache 是 wiring 不是玄学

**Symptom**

Slice 4 mechanism #5 是 Prompt Caching，按 Anthropic 文档把 system prompt 包成 `[{"type":"text","text":...,"cache_control":{"type":"ephemeral"}}]` 喂给 `messages.create`。但上游不是 Claude 是 MiMo proxy（`xiaomimimo.com/anthropic`），文档只说"speaks Anthropic message format"，没承诺 cache 语义。完全可能 wire 了 cache_control 但 proxy 静默丢字段，最后 `usage.cache_read_input_tokens` 永远是 0——mechanism 看起来"实现了"但其实从未触发。

**Root cause**

不算 bug，是**验证缺口**。"Anthropic-format compatible" 是协议层兼容（同样的 JSON schema、同样的 tool_use/tool_result 块），不蕴含 cache 行为兼容（cache 是 server-side feature，proxy 可以选择不实现）。simulator 全过 ≠ 板子真亮——必须在 production endpoint 上测 `response.usage.cache_*_input_tokens` 的真实数字。

**HW analogy**：跟供应商 datasheet 说 "USB 2.0 compliant" 一样——你得自己上示波器扫一发 SETUP/IN/OUT 包的 enumeration timing，才知道他家 PHY 有没有偷掉某个 optional feature。datasheet 兼容性是"主张"，不是"证据"。

**Fix**

`agent/runner.py:RunResult` 加 4 个字段：`input_tokens / output_tokens / cache_creation_tokens / cache_read_tokens`，每一轮 `messages.create` 之后从 `response.usage.{input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens}` 累加。CLI `hardwise ask` 在结果尾部打印一行 `tokens in/out: X/Y | cache create/read: A/B`，直接肉眼看是否触发。

**验证数字**（pic_programmer，tier=normal，model=mimo-v2.5，system prompt ~1.4K tokens）：

| 提问 | iterations | input | output | cache_create | cache_read |
|---|---|---|---|---|---|
| `U3 是什么器件？` | 2 | 1635 | 240 | 0 | **1472** |
| `U999 是什么器件？` | 2 | 129 | 171 | 0 | **2944** |
| `U4 这颗器件有几个 NC 脚？` | 2 | 196 | 154 | 0 | **2944** |

当时对 `cache_create=0` 的解释是 cache 已被更早的会话写热（不是没命中，是命中**别人**写的）。第二、三次 `cache_read=2944` ≈ 2×1472 是两次迭代各命中一次系统 prompt cache。**Mechanism #5 在 MiMo 上有真数字，不是 wiring-only。** 2026-05-16 的 cold-start follow-up 进一步收窄了结论：MiMo read path 确实可观测，但 creation accounting 不回传，不能把 `cache_creation_input_tokens` 写成已验证非零。

**附带结论**：MiMo proxy 也完整支持 Anthropic 的 `tools=[...]` + `tool_use/tool_result` 语义——`messages.create(tools=TOOL_DEFINITIONS, ...)` 不需要任何兼容代码，跟跑 Claude 一模一样。Slice 4 的 agent loop 没有为 proxy 写一行特化代码。

**Takeaway**

任何 "X-format compatible" 的供应链兼容声明（API protocol、协议栈、driver、IP 核）都只是**起点**而不是**终点**。第一次落地必须做一次端到端 verify pass：取一个 mechanism-critical 字段（这里是 `cache_read_input_tokens`），在生产端点跑一次，肉眼看数字非零。这次是 1 小时 wire + 3 次 ask 命令搞定，未来跨主机/跨 proxy/跨 model family 切换时同样的脚本就是 verification suite。Mechanism 不是"我写了代码"，是"我有可复现的数字"。

---

## 2026-05-13 · Slice 3 · ORM 抽象的价值不在抽象本身，在 deps 切换的物理验证

**Symptom**

DJI JD 第 4 条明确点名 PostgreSQL/MySQL，但 `store/relational.py` 用的是 SQLite + SQLAlchemy 2.0。简历叙事"可平滑切换到 PG"是条件式自吹，技术面试官扫一眼可能判定"个人项目级"。需要把 PG 真跑通一次。

**Root cause**

不是 ORM 写得不好，是没物理验证过。SQLAlchemy 2.0 的 `DeclarativeBase` + 标准 `Column(Integer, String)` 早就是数据库无关的，但 `create_store` 内部硬编码 `sqlite:///` 拼 URL，没暴露后端选择的开关。"我写了 SQLAlchemy" 不等于 "我用过 PostgreSQL"——简历看的是后者。

**HW analogy**：跟"原理图过了 ERC" ≠ "板子真能上电"一样。仿真通过、规则通过、网络通过都不能替代第一块板子真接上电源验证。ORM 跨库兼容也是一样——文档说兼容，不等于这台机器上真跑过。

**Fix**

- `_resolve_url()` dispatch：含 `://` 的字符串直传，否则按 SQLite 路径包 `sqlite:///`。`create_store(db_url_or_path)` 接受 `str | Path`。
- CLI 加 `HARDWISE_DB_URL` env var override，优先级最高；不 set 时默认行为不变（`reports/<project>.db`）。
- `psycopg2-binary>=2.9.9` 进 `[project.optional-dependencies] postgres` group，基础安装保持轻量。
- `tests/store/test_relational_postgres.py` 3 个 round-trip smoke test，`@pytest.mark.slow + @pytest.mark.skipif(no env var)` 双 gate；CI 上 0 影响。

**Postgres 启动踩坑**：原本想用 Docker，但 `Docker.raw` 文件 owner=root（macOS 系统权限错乱），Docker Desktop 用户态 daemon 无法 resize，启动失败。改走 `brew install postgresql@16 + brew services start` 2 分钟搞定——比修 Docker 快、不需要 sudo。后续 cross-platform 仍可用 docker run，README 两种方式都列了。

**验证数字**：`HARDWISE_DB_URL=postgresql+psycopg2://$USER@localhost:5432/hardwise uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003` 输出 `store: postgresql+psycopg2://... (121 components, 77 NC pins)`。`psql -d hardwise -c "SELECT COUNT(*) FROM components;"` 返回 121，`nc_pins` 返回 77，跟 SQLite 跑出来的数字完全一致。

**Takeaway**

ORM 抽象的价值是在 deps 切换时**省下了多少代码改动**——这次实测的代码改动是 1 个 `_resolve_url()` 工具函数 + 1 个 env var override + 1 个 optional dep group，~30 行。但简历价值不在这 30 行上，而在"真的换过一次"。投递时段做这种动作的 ROI 极高：1 小时本地工作 → 简历从条件式（"可切换"）升级到事实式（"双后端实跑"），技术面被追问时可以现场跑通 `brew services start postgresql@16 && createdb hardwise && uv run hardwise review ...` 三行。

**Next**：MySQL 同样模式（`pymysql` + `mysql+pymysql://`），何时跑取决于是否有面试官追问"MySQL 也能切吗"——目前 ROI 低于做 Slice 4 R004。

---

## 2026-05-12 · Slice 3 · KiCad 里 `pin.at` 不是引脚根部，是引脚尖端（连线点）

**Symptom**

写 R003 的 NC pin 检测时，第一份计划照着"通用 EDA 引脚模型"的直觉假设：每个引脚有 (起点 pin.at, 长度 length, 方向 rotation)，可连接的端点 = `pin.at + length * direction(rotation)`。按这个推算 J1/DB9 pin 5（lib 坐标 (-11.43, 10.16)、length 7.62），叠加 J1 在 schematic 上的 (31.75, 91.44) rot=180 之后，怎么算都对不上 no_connect 标记的 (43.18, 81.28)。

**Root cause**

KiCad 的 `.kicad_sch` 里 lib_symbols 中的 `(pin <type> ... (at x y rot) (length L) ...)`：
- `at` **就是引脚的可连接尖端**（电气端点、wire 实际落点），不是引脚根部。
- `length` 是引脚的几何长度，用来从尖端向 body 方向画一条线；`length` 不参与可连接点的位置计算。
- 即引脚的绝对位置只要 `symbol_at + rotate(pin.at, symbol_rotation_deg)`，**不要加 length×direction**。

经验证：J1 DB9 在 (31.75, 91.44) rot=180，pin 5 的 lib `at=(-11.43, 10.16)`，标准 2D 旋转 = (43.18, 81.28)，与 no_connect 坐标精确相等。同理 LT1373 (U4) 在 (196.85, 137.16) rot=0，pin FB- 和 S/S 的 lib `at` 直接对上 (171.45, 143.51) 和 (171.45, 130.81)。

**HW analogy**：跟 PCB footprint 的 pad 锚点一样——pad 在原点是"焊盘中心"，不是焊盘的某个边角。把这种"锚点 = 连接点"的约定写错的工具会输出错的 DRC。

**Fix**

`src/hardwise/adapters/kicad_pins.py:_transform()` 直接用 `symbol_at + rotate(pin.at, rotation_deg)`，tolerance 0.01mm 做坐标比对。结果：pic_programmer 主表 6 个 no_connect 全部匹配上具体的 refdes/pin_number（J1 的 4/5/6/9 + U4 的 3/4），子表 71 个 NC pin 也全部命中——总数 77 与原始 `grep -c no_connect` 结果完全吻合。

**Takeaway**

**遇到坐标算不对，先怀疑锚点约定，不要先怀疑旋转矩阵。** 坐标变换公式可以靠数学直接验，但锚点约定（at 指尖端 / 根部 / 中心）是工具方言，只能用一个已知样例反推。下次接其他 EDA 工具（Cadence / Altium）的 footprint / pin 数据，第一件事是用一个**已知 NC pin** 反推锚点定义，再写匹配代码。

---

## 2026-05-12 · Slice 3 · `sentence-transformers` 不需要装，Chromadb 自带 ONNX 嵌入模型

**Symptom**

PLAN 一开始把 `sentence-transformers>=3.0.0` 列在 Slice 3 依赖里。这个包会拖进 `torch`，整个安装大约 400MB。担心首次 `uv sync` 太久。

**Root cause**

读 Chromadb 文档发现：从 0.4 起，`chromadb` 默认 embedder 是 ONNX 版本的 `all-MiniLM-L6-v2`，依赖 `onnxruntime`（轻量，~10MB），与 `sentence-transformers` 独立。只要不显式传 `embedding_function`，`Client.get_or_create_collection()` 就走默认 ONNX 路径。

**Fix**

`pyproject.toml` 只加 `chromadb>=0.5.0` 和 `pdfplumber>=0.11.0`，不要 `sentence-transformers`。首次 `uv sync` 装的全部依赖加起来 ~120MB，比预算 400MB 小一个数量级。`tests/store/test_vector.py` 4 条 slow 测试在首次跑时下载 ONNX 模型（~80MB，进 `~/.cache/chroma`），后续运行 <1s 每个。

**Takeaway**

**装包前，先查清楚下游有没有等价的内置选项。**`sentence-transformers` 是个伟大的库，但它的体积成本是为 GPU 训练场景买的；Hardwise 这种"离线 ingest + 偶发查询"场景，ONNX CPU 路径就够用。MVP 阶段每加一个重依赖都要问"它能不能不上"——Wrench Board reference 不会自动等价 dependency 选择。

---

## 2026-05-11 · Slice 2 · R002 的 net 侧推断为什么不在这一刀做

**Symptom**

写 Slice 2 plan 的第一稿时，本能想法是"R002 的 yaml `required_evidence` 列了两条（`EDA.component.value` + `EDA.nets.power_domain`），所以两条都得实现，否则 R002 不算完整"。第一稿因此规划了"加最小 KiCad net parser"作为本 slice 的隐含前置。

**Root cause**

实测 `pic_programmer` 数据后发现两件事：

1. 整个项目只有 `pic_programmer:VCC` 和 `pic_programmer:GND` 两个 power symbol，schematic 里**没有任何显式电压标号**（没有 `+3V3` / `+5V` / `+VBAT` 这类带数字的 power symbol）。这意味着即使写出完美的 net parser，对每颗 cap 解析出"接在 VCC 上"也无济于事——`VCC 到底是 5V 还是 3.3V`不是 EDA 字段、是**评审者的领域知识**，schematic 本身根本不携带这条信息。

2. 强行做"net 推断"会把这件"领域知识"塞进 agent 的猜测里。比如硬编码"VCC=5V"，或者用 power_rails.yaml 让评审者声明——前者会瞎判，后者只是把人工标注换了个地方。两种都偏离 agent 应该做的事。

**HW analogy**：让 BOM 工具自动判断"这颗 0603 电阻能不能过 100mA"——电流是系统设计的事，BOM 工具不该猜，它只该指出"这颗的封装 0603 / 0.1W，请系统设计者确认工作电流"。R002 一样：agent 该说"C3 已标 25V，请确认这条 net 的工作电压 ≤ 20V"，不该自己猜 working voltage。

**Fix**

1. Slice 2 R002 只实现 value 侧解析：
   - `value` 含 `/<num>V` 后缀 → info finding（"已声明耐压 NV，评审者请人工对照 80% 规则"）。
   - 不含 → medium finding（"value 字段未声明耐压，请补全"）。
   - 完全不出 high severity。
2. Yaml 的 `R002.rule` 文本重写为两阶段表达——明确"Slice 2 = value 完整性；Slice 3+ = 接 net parser 后补 80% 比较"。yaml 和代码行为对齐，未来读 yaml 的人不会问"为什么没有 high finding"。
3. Net parser 推到 Slice 3（与 SQLite 一起进来更合理——nets 本来就属于关系存储的内容）。

**Takeaway**

**Agent 的边界不是"能做什么"，是"该做什么"。** 当一条规则的证据来源里混着"EDA 字段（机器可读）"和"评审者领域知识（人脑里的）"时，agent 只对前者负责；后者必须显式地以"reviewer to confirm"的形式回到人。这条对 Sleep Consolidator 也成立——candidate 不会自动晋升为 active 规则，因为"规则要不要进生产"是人的判断、不是统计阈值能下的结论。

更广义：把每一条 required_evidence 都按"机器证据 vs 人证据"标个色——前者全自动，后者必须打 reviewer-to-confirm 的旗子。混淆这两类是 agent 设计里最容易踩的坑。

---

## 2026-05-10 · Slice 1 · pic_programmer 跑出 0 finding 不是 bug，是 demo 设计的诚实结果

**Symptom**

R001（"新建器件候选识别 — footprint 字段为空"）在公开样例 `pic_programmer` 上跑出 0 finding。第一反应是"是不是 R001 写错了"。

**Root cause**

实测：`parse_schematic(pic_programmer)` 返回 124 个 record，其中 58 个 footprint 为空——但**这 58 个全部以 `#` 开头**（`#PWR05` / `#FLG01` 这类 KiCad 虚拟电源 flag / no-connect 标记）。R001 故意过滤虚拟器件后，**真实器件 0 个 footprint 为空**。

`pic_programmer` 是 KiCad 官方完整 demo，PCB layout 早就完成，所有真实器件 footprint 都已回填。这是"已完成项目"的预期状态——评审时本来就不该有"footprint 待 layout 团队回填"的器件。

**HW analogy**：拿一份已经投产 N 年的成熟 BOM 跑 ECN 检查器，输出"无 ECN 触发"是合理的；不能因为输出空就说工具坏。

**Fix**

不改 R001。改的是 demo 解释：

1. CLI 输出明确显示"0 candidate findings, 121 components reviewed"作为结果
2. R001 单测用手搓 fixture 覆盖正反例（真实 refdes 空 / 真实 refdes 填 / 虚拟 refdes 空），而**不依赖** demo 项目上 finding 命中
3. 面试 Q1 v0.5 答案直接写明这是诚实输出，并解释 R001 的真实价值在带新建器件的项目上才会显现
4. PLAN.md DR-006 / docs/review_node.md 都把这个事实写进去，避免下次自己也疑惑

**Takeaway**

**单元测试 ≠ demo 项目命中。两者要分开 acceptance。** 单元测试覆盖规则的"正反例正确性"，demo 项目证明"端到端能跑"——前者用 fixture，后者用真实数据。如果 demo 数据恰好不命中规则，那也是一种合法的"reviewed → no flag"输出。

更广义的教训：**vertical slice 的 acceptance 不能是"必须看见 finding"**，而应该是"管道跑通 + 输出结构对齐 + guards 生效 + 单测覆盖"。否则会因为数据偶然性反向调整规则逻辑，污染设计。

---

## 2026-05-10 · Slice 1 · BoardRegistry 必须区分 raw schematic vs merged

**Symptom**

写 R001 时发现：如果用 `parse_project(pic_programmer).components` 的 footprint 字段判定，会把 PCB-completed 项目里所有器件都判为"footprint 已填，无新建候选"——即使 sch 端原本是空的。R001 的判定信号被破坏。

**Root cause**

`adapters/kicad.py:30-31` 的 merge 逻辑：

```python
if not existing.footprint:
    merged[refdes] = existing.model_copy(update={"footprint": pcb_component.footprint})
```

这是 v0.1 时为了让 Refdes Guard 拿到完整封装信息而写的——对 Refdes Guard 是好事，但 R001 想看的是"sch 阶段原始字段是不是空"，merge 后字段已经被 PCB 端覆盖。

**HW analogy**：你想检查"原料状态"，但拿到的是"加工后状态"。两者不是一份数据。

**Fix**

`BoardRegistry` 加两个 raw 字段：

```python
schematic_records: list[ComponentRecord] = Field(default_factory=list)
pcb_records: list[ComponentRecord] = Field(default_factory=list)
```

`parse_project()` 同时填 raw + merged。`components` 字段语义不变（merged view，给 Refdes Guard 用）；`schematic_records` 是 sch-only raw view（给 R001 等"需要看 sch 阶段原始状态"的规则用）。沉淀为 PLAN.md **DR-008**。

**Takeaway**

**数据 merge 是有损的，原始视图必须并存。** 早期定数据模型时，只要后续可能有"我要看上游某一阶段的原始状态"的需求，就保留 raw 视图——不要假设 merge 后的视图能回溯。

广义教训：**Pydantic model 不是单一 truth 的容器，是多个 truth view 的集合。** 该字段一份，view 字段多份。Slice 1 这次是低成本扩字段；如果 Slice 3 才发现要这样改，下游所有规则代码都得改。

---

## 2026-05-09 · Day 2 · Coaching correction — shipped code without module I/O explanation

**Symptom**

After the KiCad parser shipped, the user pointed out: "我不是只是为了做出来，是为了边做边学，你要说一下你做的每个模块输入是什么，输出是什么等等." The code worked, but the learning loop was incomplete.

**Root cause**

I optimized for delivery proof (`inspect-kicad`, tests, lint) and under-served the coaching goal. For this project, a module is not done when it runs; it is done when the user can explain its purpose, input, output, design reason, and verification path.

**Fix**

Added a "Day 2 shipped module I/O" table to `docs/architecture.md` covering `ComponentRecord`, `BoardRegistry`, `parse_schematic`, `parse_pcb`, `parse_project`, and `inspect-kicad`. Also added a reusable "Module explanation template" so future modules follow the same format.

**Takeaway**

Hardwise has two deliverables: working code and transferable understanding. Every future module needs a short teaching pass before and after implementation: purpose, input, output, why, verification, interview sentence. If any part is missing, the module is not actually shipped for this user's goal.

---

## 2026-05-09 · Day 2 · KiCad parser verification — sandbox, dev deps, virtual refdes order

**Symptom**

Three small surprises appeared while validating the first KiCad registry parser:

```
error: failed to open file `/Users/liwenjin/.cache/uv/sdists-v9/.git`: Operation not permitted
error: Failed to spawn: `pytest`
error: Failed to spawn: `ruff`
```

After the parser did run, the first CLI screen was dominated by KiCad virtual symbols such as `#PWR01` and `#FLG06`, hiding real review targets like `C1`, `D11`, and `U3`.

**Root cause**

1. Codex sandbox allowed writes in the project but not reads under the user-level `uv` cache, so `uv run ...` needed an approved run.
2. The project had runtime dependencies installed, but dev dependencies were not installed yet; `pytest` and `ruff` were declared under `[project.optional-dependencies].dev` but missing from `.venv`.
3. KiCad stores power symbols and power flags as schematic symbols with refdes-like names. They are valid registry entries, but poor first-screen demo material.

**Fix**

1. Re-ran validation with approved `uv run`.
2. Ran `uv sync --extra dev` to install `pytest` and `ruff`.
3. Changed registry sort order so physical refdes print before virtual `#PWR` / `#FLG` entries.

**Takeaway**

Validation friction is still information. A demo command should print the objects a hardware engineer cares about first, even if the underlying registry keeps virtual symbols for correctness. Also, Day-1 setup should include `uv sync --extra dev` once tests exist, not only plain `uv sync`.

---

## 2026-05-08 · Day 1 · API verify — load_dotenv override + lowercase model id

**Symptom**

Two failures in sequence on the first `uv run hardwise verify-api`:

```
# 1. wrong base URL
calling MiMo-V2.5 via https://anyrouter.top
error: AuthenticationError: Error code: 401 - 无效的令牌

# 2. wrong model identifier (after fix #1)
calling MiMo-V2.5 via https://token-plan-sgp.xiaomimimo.com/anthropic
error: BadRequestError: Error code: 400 - Not supported model MiMo-V2.5
```

**Root cause**

Two unrelated bugs surfaced together:

1. **`python-dotenv`'s `load_dotenv()` does not override existing environment variables by default.** The user had `ANTHROPIC_BASE_URL=https://anyrouter.top` exported globally on the Mac (from another Anthropic-format proxy used by other projects). When Hardwise loaded its `.env`, the existing env var won; Hardwise's value was silently ignored.

2. **API model identifiers are not the same as marketing names.** The user wrote "MiMo-V2.5" (camel-case + dot), but the actual API id is `mimo-v2.5` (lowercase + hyphen). Discovered by curling `/v1/models` on the proxy, which exposes an OpenAI-style listing endpoint.

**HW analogy**: a connector pin labeled "VBAT" on a schematic is rarely "VBAT" in the BOM database — it's `vbat_main` or `V_BATT_3V3` or some normalized identifier. Marketing names ≠ engineering identifiers; always look up the registry.

**Fix**

1. `src/hardwise/cli.py` — changed `load_dotenv()` to `load_dotenv(override=True)`. Hardwise's `.env` now wins against any pre-existing shell env. Trade-off documented: if Hardwise is ever deployed to CI where env is the source of truth, this needs revisiting.

2. `.env`, `.env.example`, `CLAUDE.md` — model values changed from `MiMo-V2.5` to `mimo-v2.5`. CLAUDE.md Models section now also documents the model-list curl command so future identifier confusion is one command away from resolution.

**Takeaway**

Two generalizable rules:

1. **For local CLI tools, `load_dotenv(override=True)` is the correct default.** The principle of least surprise is "the .env in this project IS the source of truth here." Anyone deploying to CI can flip it back; users debugging locally will lose hours otherwise.

2. **Always probe the upstream's model-list endpoint before committing to a model name.** Most LLM-as-a-service proxies (OpenAI-compatible or Anthropic-compatible) expose `/v1/models` or `/models` regardless of which protocol they speak. One curl beats five guesses.

Both were caught in the first verify call — which is itself the third generalizable rule: **build a `verify-api` CLI command on Day 1**, not in a panic on Day 7. The cost was 5 minutes; the value was catching both bugs before any real code touched the API.

---

## 2026-05-08 · Day 1 · CLAUDE.md scaffolding — abstract vs concrete

**Symptom**

The Day-1 CLAUDE.md was structurally correct (right sections, right intent) but **abstract**: "Refdes Guard verifies output against the EDA registry" without specifying the regex, the layer split, or the file path. User compared it to Wrench Board's CLAUDE.md, where the equivalent rule specifies `\b[A-Z]{1,3}\d{1,4}\b`, the two-layer mechanics (tool returns `{found:false, closest_matches:[...]}` + post-hoc sanitizer), and the exact file (`api/agent/sanitize.py`).

The gap was concentrated in three places:
- Hard rules said *what* but not *how*
- Stack section had no version pins
- No Models section linking env var → model → tier → use case
- No "tools return structured null" or "file size guard" rules
- No editorial meta-rule, so dated context ("started 2026-05-08") leaked in

**Root cause**

Two compounding mistakes:
1. **Wrong genre.** I wrote CLAUDE.md as a *narrative* document (explaining what the project is and why it exists). Narrative belongs in README. CLAUDE.md is a *spec* — operational reference with file paths, regexes, schemas, and command-level rules.
2. **Missing meta-rule.** Without an explicit "no temporal framing" rule, dated context drifts in. Wrench Board's editorial rule at the bottom of their CLAUDE.md is the immune system that prevents this; mine had no immune system.

**HW analogy**: a netlist with refdes but no values is structurally correct but unbuildable. CLAUDE.md without concrete specs is the same shape — present, well-organized, non-functional.

**Fix**

Refactored CLAUDE.md to mirror Wrench Board's spec-density:
- Hard rule on anti-hallucination now specifies the regex, the two layers, the wrapping format `⟨?U999⟩`, and the implementation file
- Stack pins major versions (`anthropic >= 0.40.0` etc.)
- New Models section: env var → model → tier → use case table
- Conventions added: structured-null return, ~300-line file size guard, verify-before-done
- New Commit hygiene section with conventional-commits + ask-before-push
- New "Two stores, one join key" rule preventing future schema mixing
- Editorial rule at bottom — strips any sentence that won't read accurate in six months

Items needing code progress before they can be specific (layout tree, tool manifest, on-disk schema, CLI surface, anti-rules from real review runs) deferred to `docs/rolling_log.md` with explicit code-milestone triggers, not date-based deadlines.

**Takeaway**

CLAUDE.md is **specs, not narrative**. Two tests for whether a sentence belongs:

1. Could a fresh session execute against it without grepping the codebase?
2. Will it still read as accurate six months from now (no dates, no "currently"-framed claims)?

If either answer is no, the sentence belongs in README, memory, learning_log, or rolling_log instead.

Generalizes beyond Hardwise: any time I scaffold a CLAUDE.md from scratch, default to spec mode (regex, file paths, schemas, command-level rules), not narrative mode. And always include the editorial meta-rule on Day 1 — it's free and it self-enforces every future edit.

---

## 2026-05-08 · Day 1 · CLI scaffold — Typer single-command collapse

**Symptom**

```
$ uv run hardwise hello
Usage: hardwise [OPTIONS]
Try 'hardwise --help' for help.
Got unexpected extra argument (hello)
```

**Root cause**

Typer collapses a `Typer()` app with only one `@app.command()` into a *single-command app* — the lone command becomes the implicit default, so the positional argument `hello` is parsed as an extra arg to that default command, not as a subcommand selector.

**HW analogy**: a multi-pin connector with only one wire soldered. The system auto-degrades to "single signal" mode and stops expecting channel selection. To keep multi-channel semantics, you have to explicitly declare the connector pinout — even with only one channel populated.

**Fix**

`src/hardwise/cli.py` — added `@app.callback()` with an empty body. The callback forces Typer into multi-command mode regardless of how many commands are registered.

```python
@app.callback()
def _root() -> None:
    """Force Typer to treat this as a multi-command app even when only one command is registered."""
```

**Takeaway**

When a framework auto-detects intent based on shape (here: number of commands), the scaffold needs to match the *eventual* shape, not the *current* shape. Adding the callback at Day 1 was free; discovering it after the user runs `hello` cost two round-trips. **Build for the shape you're heading toward, not the one you have today.** This generalizes to schemas, type hints, and DB models too.

---

## 2026-05-16 · Refdes Guard false positives on pin names + R003 connector noise

**Symptom**

After running `hardwise review` on pic_programmer:
1. Sanitizer reported "17 unverified refdes wrapped" — tokens like `RA0`, `RB7`, `GP4`, `P6` wrapped as `⟨?RA0⟩`
2. R003 generated 77 findings (84 total) — report flooded with connector NC pins, burying the 2 IC findings that actually need review

**Root cause**

1. **Refdes Guard**: regex `\b[A-Z]{1,3}\d{1,4}\b` matched **pin names** (PIC port names like `RA0`, `RB7`) and **pin numbers** (`P6`, `P9`) that appeared in R003 finding messages like `U5 pin 17 (RA0)`. These aren't refdes — they're pin function names from the schematic symbol. Guard saw them, checked the registry (which only contains component refdes like `U5`, not pin names), and wrapped them.

2. **R003 noise**: R003 generated one finding per NC pin. Connectors P2 (28-pin DIP socket) and P3 (40-pin socket) had 22 and 32 NC pins respectively — all intentionally unused. Hardware engineers don't need 32 separate "confirm this NC pin" warnings for a socket; they need one "this socket has 32 unused pins, confirm design intent" summary.

**HW analogy**:
- Refdes Guard: a BOM checker that flags every resistor *value* (e.g. "10K") as a missing part number because it matches the part-number regex but isn't in the approved vendor list. The value field isn't a part number — it's a parameter.
- R003 noise: an assembly checklist that lists every unused pin on a 40-pin ZIF socket individually instead of saying "socket has 18 unused positions — confirm test coverage."

**Fix**

1. **Refdes Guard** (`src/hardwise/guards/refdes.py`):
   - Added `_looks_like_pin_name(text, start, end)` — detects if a token appears inside a pin-name parenthetical by searching backward for `(` and forward for `)`, then checking if `pin \d+` precedes the opening paren.
   - Handles both single-function pins `pin 17 (RA0)` and multi-function pins `pin 12 (ICSPC/RB6)` where the token is after `/` inside parens.
   - `sanitize_text` now skips wrapping if `_looks_like_pin_name` returns True.

2. **R003 connector aggregation** (`src/hardwise/checklist/checks/r003_nc_pin_handling.py`):
   - Added `_is_connector_like(refdes, registry)` — returns True for refdes starting with `J`/`P`/`CN` OR footprint containing `Connector`/`Jumper`/`MountingHole`.
   - **Critical**: explicitly excludes `U`/`IC` prefix — ICs in DIP sockets (footprint `DIP-8_W7.62mm_Socket_LongPads`) are still ICs, not connectors. The `Socket` in the footprint name refers to the mechanical package, not the electrical function.
   - Groups connector NC pins by refdes, generates one `severity=low` summary finding per connector (e.g. "P3 has 32 NC pins (31, 34, 26, ...) on a connector-like part").
   - IC NC pins remain `severity=medium` and are reported individually for datasheet review.

3. **HTML report** (`src/hardwise/report/html.py`):
   - Added Chinese-friendly message for grouped connector findings.

**Verification**

- pic_programmer review now produces:
  - **0 unverified refdes wrapped** (down from 17)
  - **29 findings total**: 7 R002 (cap voltage) + 3 R003 connector summaries (low) + 19 R003 IC pins (medium)
  - U4 (LT1373 regulator): 2 NC pins flagged individually ✓
  - U5 (PIC 18-pin MCU): 13 NC pins flagged individually ✓
  - P2/P3 (DIP sockets): 1 summary each instead of 54 individual findings ✓

**Takeaway**

**Defense-in-depth anti-hallucination needs context-aware bypass.** The Refdes Guard is Layer 2 (regex scan) after Layer 1 (tool discipline). But a pure regex can't distinguish refdes from pin names without context. The fix isn't to weaken the regex (that would let real unknown refdes slip through) — it's to add a **context filter** that recognizes when a match is in a non-refdes syntactic position.

**Noise reduction for review tools: group by intent, not by schema.** R003's schema is "one finding per NC pin" — correct for ICs where each pin needs datasheet verification. But connectors follow a different intent: "confirm bulk unused pins match design scope." Treating both the same floods the report. The fix groups by **component class** (connector vs IC) and adjusts both severity and granularity accordingly.

Generalizes: any rule that produces >10 findings of the same pattern on one component should ask "is this component class different?" before generating the full list.

---

## 2026-05-16 · Eval Pack v0 uses public regression oracle, not expert gold labels

**Symptom**

The single `pic_programmer` demo was doing too much work in the story: parser fixture,
rule demo, and evidence of product reliability. That made the project feel more fragile
than it is, because every sample-specific quirk changed the headline number.

**Root cause**

There is no ready-made public "expert gold-label schematic review findings" dataset for
KiCad. The closest public resource is `kicad-happy-testharness`: real KiCad projects,
pinned commits, regression baselines, assertions, and Layer 3 findings. Its own docs are
explicit that most assertions are consistency checks, not independent correctness proof.

**HW analogy**: treating one completed reference board as the whole validation plan is like
qualifying a power design from one known-good bench unit. It proves the flow can work, but
not that the process is robust across board families.

**Fix**

Added a small `Hardwise Eval Pack v0`:

1. `eval/manifest.yaml` selects five public repos from the kicad-happy smoke/corpus lists,
   pinned to their upstream commits.
2. `hardwise eval` can clone missing repos with `--download`, discover KiCad project
   directories, run R001/R002/R003, and write `eval-summary.json` + `eval-summary.html`.
3. The report labels the trust boundary as "public regression oracle / pseudo-gold, not
   expert gold labels" so the project does not overclaim.
4. `--limit-projects` was fixed to stop before cloning later repos, so iteration can run
   one external project without downloading the whole manifest.

**Verification**

- Local harness test against `data/projects/pic_programmer`: 1/1 project passed, refdes
  wrapped count stayed 0.
- External smoke with `Jana-Marie/analog-toolkit` from the kicad-happy-selected corpus:
  1/1 project passed, 26 findings, JSON and HTML summaries generated.

**Takeaway**

For this MVP, "public, pinned, reproducible, and honest about trust level" beats chasing
a non-existent perfect gold dataset. The eval pack should be presented as a reliability
and noise-control harness first; expert correctness can be a later tier.

---

## 2026-05-16 · Harness surfaced connector pin names that look like refdes

**Symptom**

The first external eval smoke on `Jana-Marie/analog-toolkit` passed structurally, but
reported `unverified_refdes_wrapped=1`. The wrapped token came from an R003 connector
summary: `J1 has 1 NC pins (A4) ...`, where `A4` is a connector pin name, not a
component reference designator.

**Root cause**

Refdes Guard correctly scans broad tokens like `A4`, because real designs can use short
reference designators. But connector pin naming also commonly uses row/position names
like `A4` or `B7`. The earlier pin-name bypass only covered IC-style forms such as
`pin 17 (RA0)` and missed generated NC pin-list summaries.

**Fix**

The pin-name context filter now also treats tokens inside generated `NC pins (...)`
parentheticals as pin names, and recognizes alphanumeric pin identifiers in forms like
`pin A4 (A4)` / `pin GND3 (GND)`. Eval summaries also carry
`unverified_refdes_samples`, so a future nonzero guardrail count points directly to the
offending finding instead of requiring ad hoc reproduction.

**Verification**

Full public-corpus smoke (`eval/manifest.yaml`, 5 repos / 6 component-bearing KiCad
project directories) passed structurally: 1707 components parsed, 231 NC pins, 437
findings, 10 empty KiCad directories skipped, `unverified_refdes_wrapped=0`,
`findings_dropped_no_evidence=0`.

**Takeaway**

This is exactly what the eval harness should do: expose a real integration boundary, not
just print a bigger-looking score. Guardrail metrics need examples attached, otherwise
they are not actionable for engineering review.

---

### 2026-05-20 — Eval project counts should exclude empty KiCad directories

**Symptom**

`reports/eval/eval-summary.json` reported 16 passed projects, but the hackrf checkout
included empty hardware subdirectories with `components=0` and `findings=0`.

**Root cause**

The eval harness treated every directory containing a `.kicad_sch` file as a passed
project, even when parsing produced no component registry. That was structurally valid
but inflated the headline project count.

**Fix**

Mark zero-component directories as `skipped_empty`, add `projects_skipped_empty`, and
count `projects_total/projects_passed` only from component-bearing projects.

**Takeaway**

Eval metrics should separate discovery breadth from meaningful coverage. Bigger totals
are weaker than honest totals when the report is used in an interview.

---

## 2026-05-16 · Eval corpus checkouts must not enter repo lint scope

**Symptom**

After downloading the public eval corpus under `eval/projects`, `uv run ruff check .`
started reporting lint errors from third-party files inside the checked-out projects.

**Root cause**

The eval corpus is input data for Hardwise, not source code owned by this repo. Running
repo lint over those checkouts conflates upstream project style with Hardwise quality.

**Fix**

Ignored local eval checkouts and generated eval reports in `.gitignore`, and added
`eval/projects` / `reports/eval` to Ruff's exclude list.

**Takeaway**

Harness artifacts need their own boundary. Public corpus data should be reproducible and
pinned, but it should not become part of the product's lint/test ownership surface.

---

## 2026-05-25 — V2.1 IR foundation closed

**Symptom:** none (greenfield slice).

**What shipped:** `src/hardwise/ir/{__init__.py, types.py, build.py}` plus `tests/ir/{test_types.py, test_build.py}`. `Pin / Component / Net / Design` BaseModels + `build_design(registry)` KiCad aggregator. 190 tests pass, ruff clean. `hardwise review` CLI behavior unchanged (V2.1 only adds new modules).

**Two reconciliations with the V2 spec made during planning:**

1. Spec used `@dataclass` for IR types; existing codebase (`adapters/base.py`, `checklist/finding.py`) uses pydantic `BaseModel`. Plan chose BaseModel for codebase consistency + JSON round-trip headroom V2.4 will need.
2. Spec §3.7 DS001 example referenced `Finding.pin_number`, which doesn't exist on the `Finding` BaseModel. V2.1 deferred this — V2.2 plan will add `pin_number: str | None = None` to `Finding` as a backward-compatible optional field (mirrors the DR-009 extension pattern).

**Takeaway:** When the brainstorm uses informal `@dataclass` sketches, the implementation plan should reconcile against the codebase's actual model framework. Carrying the inconsistency forward would force a mid-sub-slice refactor.

**Next:** V2.2 plan (per-component check flip + `Finding.pin_number` extension + R001-R003 outer-loop rewrite). To be drafted in a fresh planning session.

---

## 2026-05-29 — V1.1-V1.3 coverage loop should advance by reviewable groups

**Symptom**

After V1, the real Allegro project could be imported and grouped, but the next useful
step was still too manual: no concise document-index draft, no safe profile-draft
lifecycle state, and only one validated family path. A candidate CSV also risked
including passive-looking values such as `470uF 2.5V 20%` when the grouped family fell
back to `unknown`.

**Root cause**

Grouped coverage was readable in HTML/Markdown/JSON, but it did not yet create a
review artifact that a human could fill into `document-index` rows. Draft profiles had
the same file shape as reviewed profiles, so they needed an explicit lifecycle field to
avoid accidental validation. Candidate filtering also trusted `suggested_family` too
much and needed a second passive-value guard on the identity itself.

**Fix**

Added the V1.1-V1.3 loop:

- `build-document-index-candidates <validation-index.json>` writes a stable CSV of
  non-passive, non-mechanical, unmatched groups for document review.
- `draft-datasheet-profile ... --identity ...` writes `review_status=needs_review`
  profile scaffolds, and profile matching skips anything not marked `ready`.
- `pca9548a.json` plus an `i2c_mux` validator add a second real family path beyond the
  MPQ8626 buck validator.
- Candidate generation now filters passive-looking identities even when family
  inference says `unknown`.

**Verification**

- `uv run pytest -q` → 358 passed, 7 deselected.
- `uv run ruff check .` → all checks passed.
- Real public Allegro smoke with `data/document_indexes/family_v1_3_docs.csv` selected
  `SWITCH BOARD 144-VA_20240712 1401(1).BOM`, matched BOM `4010/4010`, produced 132
  groups, and validated 9 components: U13/U20/U23/U26 via MPQ8626 plus
  U8/U9/U10/U11/U130 via PCA9548A. Rollup was PASS/WARN/ERROR = 9/0/0, manual = 4001.

**Takeaway**

The scalable unit is not “one-off device JSON forever”; it is group coverage → document
index row → needs-review profile draft → reviewed profile/family validator. Each stage
has an explicit human gate, so new projects can expose gaps without pretending to verify
parts Hardwise does not yet understand.

## 2026-05-29 — MOSFET Vgs is gate-to-source, not gate-to-ground

**Symptom**

The try/trellis MOSFET validator (`MosfetValidator._check_vgs_range`) read
`voltage_for_net(gate.net)` and compared that single number against the ±20 V
abs max, calling it "Vgs". On a low-side FET it looked right. On a high-side
FET — source on the switch node at, say, 48 V, gate bootstrapped to 58 V — it
would read 58 V and ERROR a perfectly healthy gate drive.

**Root cause**

Vgs is a *differential*: `V_gate − V_source`. Gate-to-ground only equals Vgs
when the source happens to be at ground (low-side). The old code hard-coded the
low-side assumption. A second, quieter copy of the same bug lived in the profile
schema: labelling the Source pin `category: "ground"` makes the generic
`validate_pin` demand a ground net, so the high-side source would also
false-ERROR one layer up. The validation-guidelines doc actively recommended
`Source → ground`, so the trap was being taught forward.

**Fix**

Migrated MOSFET to the clean codex pattern as `validation/mosfet.py`:

- `Vgs = voltage(gate) − voltage(source)`, summary always prints
  `gate X V - source Y V` so the reference node is auditable.
- When gate or source has no statically known voltage (PWM drive, floating
  switch node) → WARN, explicitly "not assuming ground". Never fabricate 0 V.
- Same differential treatment for `Vds = voltage(drain) − voltage(source)`.
- Profile Source pin recategorised `switch_node`, abs-max limits read from the
  profile (not hard-coded), evidence tokens attached.
- Guidelines doc corrected: Source is `switch_node`, with the Vgs rule spelled
  out so the next three-terminal family inherits the right reference.

**Verification**

- `uv run pytest tests/validation/test_mosfet.py -v` → 6 passed. The decisive
  case (`test_highside_vgs_uses_source_reference`) sets SW=48 V, gate=58 V and
  asserts Vgs=10 V PASS — it would ERROR under the old gate-to-ground logic, so
  the test has teeth.
- `uv run pytest -q` → 373 passed, 7 deselected. `uv run ruff check .` → clean.

**Takeaway**

For any three-terminal active device, the control voltage is referenced to a
device pin, not to the board ground. Encode the reference node in both the
arithmetic and the summary string, and WARN instead of assuming a default when
the reference floats. A wrong default in a *spec doc* propagates to every future
family — fix the doc, not just the code.

## 2026-05-29 — Agent and validators were two demos that never met

**Symptom**

A codebase audit found `agent/` has zero references to `validation/`. The
review agent exposed four tools (list/get component, NC pins, datasheet search)
and none of them called a family validator. The deterministic validators
(buck, gate_driver, mcu, i2c_mux, diode, connector, mosfet) — the strongest,
most trustworthy work in the repo — were unreachable from the agent that the
DJI pitch calls an "AI hardware review agent". Two parallel pipelines, one
product story.

**Root cause**

The two halves grew on different data shapes. Agent tools run on the relational
`Session` + `BoardRegistry` + vector `collection` (KiCad intake). Validators run
on the IR `Design` + `Component` + `DatasheetProfile` (Allegro intake). Nothing
bridged the seam, so the agent could describe a component but never validate it.

**Fix**

Added `run_component_validation(refdes)` as the fifth agent tool:

- Runner gains optional `design` + `validation_targets` ({refdes -> profile})
  constructor params, defaulting empty so existing KiCad-only callers are
  unaffected.
- The tool is a pure lookup-and-validate: refdes not in design -> `not_found`
  + closest_matches (difflib 0.6 cutoff, same as `get_component`); refdes with
  no assigned profile -> `no_profile`; assigned -> `validated` with flattened
  PASS/WARN/ERROR rows + evidence tokens. Never auto-matches a profile, never
  fabricates a verdict — consistent with the tools-never-fabricate rule.
- When no design is loaded the dispatch returns a structured `not_configured`
  payload (same backoff pattern as `search_datasheet` with no collection).

**Verification**

- `uv run pytest -q` → 379 passed, 7 deselected (+12). New
  `tests/agent/test_validation_bridge.py` covers the pure tool function and the
  runner dispatch path (FakeAnthropic, no API), including
  `test_runner_dispatches_validation_and_returns_structured_payload` proving the
  loop reaches the validator and gets `overall=PASS` back.
- Two pre-existing tests rightly broke and were updated: the tool-manifest
  count (4→5) and a part-number false-positive assertion. `ruff` clean.

**Takeaway**

When two subsystems speak different data shapes, the integration tool belongs at
the shape boundary, not inside either half — inject both contexts into the
orchestrator and keep the tool a thin, non-fabricating lookup. The highest-value
change in a mature codebase is often not new capability but connecting capability
that already exists. (DR-011, Phase 1.)

## 2026-05-30 — Real datasheet provenance is two corroborating lines, not runtime RAG extraction

**Symptom**

DR-011 Phase 2 originally read like one pipeline: real PDF -> Chroma ingest ->
query -> DS001 finding token. That wording was misleading. DS001 does not
scrape Chroma text during `review`; it reads the reviewed static
`DatasheetProfile.evidence["abs_max.vin"]` token.

**Root cause**

The project had two valid evidence paths but the docs collapsed them into one.
Line A is deterministic profile validation: `l78.json` says `abs_max.vin=35.0`
with `datasheet:l78.pdf#p4`, and DS001 emits that token for U3. Line B is
independent PDF provenance: the public L78 datasheet can be extracted/indexed
with page metadata, and search should corroborate the same page. Treating Line B
as if it dynamically generated Line A would overclaim the agent's runtime
behavior.

**Fix**

- Trellis planning artifacts now state the two-line evidence model explicitly.
- Fast tests now generate a tiny PDF and verify `extract_chunks()` preserves
  page numbers and `datasheet:<file>#pN` tokens, then capture the exact metadata
  handed to `ingest_chunks()` without invoking Chroma semantic ranking.
- Chroma semantic query coverage remains slow-only, consistent with
  `tests/store/test_vector.py`, because the default ONNX MiniLM embedder can
  download model data on first run.
- README, architecture notes, and interview answers now use `part_ref=L7805`
  for datasheet identity instead of `part_ref=U3`.

**Verification**

- Official ST PDF web verification: `CD00000444.pdf` / L78 DS0422 Rev 38
  (February 2025) still has "Absolute maximum ratings" on page 4, with VI =
  35 V for VO = 5 to 18 V.
- `uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003,DS001 --report-style component --no-consolidate --output /tmp/hardwise-phase2-ds001.md`
  produced 29 findings and U3 / DS001 cites `datasheet:l78.pdf#p4`.
- `uv run pytest tests/ingest/test_pdf.py tests/checklist/test_ds001.py tests/ir/test_profile.py -q`
  -> 17 passed.
- `uv run pytest tests/store/test_vector.py -q -m slow` -> 4 passed, keeping
  Chroma semantic ranking in the slow lane.
- `uv run pytest -q` -> 380 passed, 7 deselected. `uv run ruff check .` ->
  clean.
- After the official PDF was staged locally from
  `/Users/liwenjin/Downloads/CD00000444.pdf` to gitignored
  `data/datasheets/l78.pdf`, real ingest/query succeeded:
  `ingest-datasheet` wrote 157 chunks with `part_ref=L7805`, and
  `query-datasheet "absolute maximum input voltage"` returned top-1
  `[l78.pdf p4 part=L7805]`.

**Takeaway**

For provenance demos, be precise about which layer owns the fact. A profile
token can be independently corroborated by PDF search without being generated
by PDF search at review time. Fast tests should lock deterministic contracts
(page/token/metadata); embedding-backed semantic ranking belongs in slow tests.

## 2026-05-30 — BJT Vbe checks must model reverse VEBO, not positive forward overvoltage

**Symptom**

The first Phase 3 plan almost copied the MOSFET pattern too literally and talked
about a "base-emitter overvoltage" fixture. That wording implied comparing
`abs(Vbe)` or positive forward Vbe against an abs-max number, which would make
the validator look electrically naive in a hardware review.

**Root cause**

MOSFET `Vgs` is a symmetric oxide limit, so `abs(Vgs) > limit` is reasonable.
BJT base-emitter behavior is a diode junction: positive `Vbe ~= 0.6-0.7 V` is
normal operation, and forward abuse is primarily a current / base-resistor
problem. The voltage abs-max to catch deterministically is reverse emitter-base
breakdown (`VEBO`), where the emitter is driven above the base.

**Fix**

- Added `data/datasheet_profiles/2n3904.json` from onsemi `2n3904-d.pdf#p1`
  with top-level `abs_max.vceo=40.0`, `abs_max.vebo=6.0`, and pinout evidence.
- Added `src/hardwise/validation/bjt.py` with connectivity checks plus
  `bjt_vebo_rating` and `bjt_vceo_rating`.
- `bjt_vebo_rating` computes `reverse_be_voltage = emitter - base`; it never
  compares positive forward Vbe against VEBO.
- Numeric tests inject `Net.voltage_hint` for base/emitter/collector voltages.
  This avoids pretending the net-name parser understands realistic 0.7 V nodes.

**Verification**

- `uv run pytest tests/validation/test_bjt.py -q` -> 6 passed.
- The key failure case sets emitter=12 V and base=0 V. A base-to-ground check
  would see 0 V and miss it; the emitter-referenced check reports reverse B-E
  voltage 12 V above VEBO 6 V.
- `uv run pytest -q` -> 386 passed, 7 deselected. `uv run ruff check .` ->
  clean.

**Takeaway**

Three-terminal validators share the reference-node discipline, not the same
math. MOSFET `Vgs` is symmetric; BJT `VEBO` is directional. When adding a new
family, copy the test philosophy from a nearby validator, but re-derive the
device physics before copying the inequality.

## 2026-05-30 — Phase 4 demo needs two public input tracks, not one fake board

**Symptom**

The first Phase 4 PRD said "a single documented demo sequence" that produced an
agent-validation trace, datasheet-cited finding, and HTML workbench. That was
too neat. The current repository has no public board that is both a KiCad
project for `review` / `ask` and an Allegro netlist+BOM project for
`design-validator-ui`.

**Root cause**

The two strongest surfaces intentionally consume different shapes:

- KiCad `pic_programmer` powers the agent/review track and carries U3 / L78 /
  DS001 with `datasheet:l78.pdf#p4`.
- Allegro `mixed_controller_power_stage` powers the static project workbench
  and shows multi-family validation (`U1` PASS, `U12`/`U3`/`U8` ERROR).

Forcing them into one linear board story would overclaim the artifact and make
the demo brittle under interview questioning.

**Fix**

- Reframed Phase 4 as "one trust backbone across two public input tracks":
  registry object -> deterministic validator/rule -> evidence token -> guarded
  agent/report explanation.
- Rewrote `docs/demo.md` and `docs/demo.html` around that framing.
- Refreshed README, docs index, JD alignment, and interview Q&A so the current
  submission story no longer points first at the older V1.3 MPQ8626/PCA9548A
  / 4010-component narrative.
- Kept `hardware-demo.html`, `midpoint_review.*`, and
  `interview_narrative.*` as historical/supporting pages instead of blanket
  rewriting every HTML file.

**Verification**

- `uv run pytest tests/agent/test_validation_bridge.py -q` -> 6 passed.
- `uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003,DS001 --report-style component --output /tmp/hardwise-phase4-review.md`
  -> 29 findings, 121 components reviewed; U3 / DS001 cites
  `datasheet:l78.pdf#p4`.
- `uv run hardwise design-validator-ui tests/fixtures/allegro/mixed_controller_power_stage.net tests/fixtures/allegro/mixed_controller_power_stage_bom.csv --output /tmp/hardwise-phase4-workbench.html --index-output /tmp/hardwise-phase4-index.md --index-json /tmp/hardwise-phase4-index.json`
  -> 25 components, 4 validated, BOM matched 25, PASS/WARN/ERROR = 1/0/3,
  manual = 21.

**Takeaway**

Submission closeout is not just making the demo look polished. It is where
overclaims get removed. A two-track story is stronger than a fake single-track
story because it names the actual data boundary and still shows the same trust
contract on both sides.

## 2026-05-30 — README review smoke commands should run sequentially or isolate DB output

**Symptom**

During submission self-check, running the two README `hardwise review`
quickstart commands in parallel made the HTML review process fail with
`sqlite3.OperationalError: table components already exists`.

**Root cause**

Both commands use the default relational store path
`reports/pic_programmer.db`. The CLI removes and recreates that SQLite file for
each run. Two concurrent review processes can interleave unlink/create/table
creation against the same path, so one process observes a half-recreated store.

**Fix**

Reran the README quickstart commands sequentially; both succeeded:

- `uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003,DS001 --report-style component`
  -> 29 findings, 121 components reviewed.
- `uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003 --format html`
  -> 28 findings, 121 components reviewed.

Also refreshed README's quickstart output text to match the current CLI
`consolidator: 3 candidate rule(s)` line.

**Takeaway**

Default report artifacts are convenient for human sequential demos, not
parallel smoke tests. When automating multiple `review` commands at once, give
each run an isolated report/store output path or run them sequentially.
