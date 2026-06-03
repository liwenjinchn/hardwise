# Interview Q&A — Hardwise

> Start with `docs/interview_narrative.md` for the concise interview story.
> Use `docs/interview_narrative.html` when you want the paper-style reading view.
> This file is the longer evidence bank behind that story.

## 主叙事

Hardwise 不是在证明“大模型可以独立评审完整硬件设计”。它证明的是一个更窄但更可信的闭环：在 pre-layout 原理图评审节点，Agent 只能通过工具查询 EDA registry 和 evidence store；所有用户可见 refdes 必须 registry-verified，所有 finding 必须有 evidence token。模型负责解释和组织证据，不能自由发明元件、pin 或 datasheet 结论。

面试时优先讲这条主线：Phase 4 是“一条 trust architecture，两条 public input tracks”。KiCad `pic_programmer` 轨用 `review --rules R001,R002,R003,DS001 --report-style component` 证明 registry object -> DS001/L78 reviewed profile token -> guarded report；同一条 L78 路径又用 `ingest-datasheet -> query-datasheet -> ask --vector` 证明 live retrieval 和 agent citation 能跑通。Allegro 轨用真实公开 PST+BOM 证明同一套 deterministic validation truth 能生成项目级 HTML workbench：早期 4010 颗样本全部 BOM matched，其中 3738 颗已有 L1 deterministic 或 generic passive coverage；最新 D1 mainboard 输入是中文 `.xlsx` BOM + PST 文件夹，8180 schematic components 中 7248 个 BOM matched，6573 个进入 light deterministic coverage，剩余 1607 个保持 manual/profile-gap rows，并生成 195 个 component groups / 75 个 document-index candidates。C3/C4 coverage loop 是支撑材料：它证明 ranking 可以持续把 manual rows 推进 L1 deterministic，但不要把它讲成主角。最新收口补了两点可交付性：Windows/PowerShell recipe 和 `windows-latest` CI workflow 已加入，但 Windows 只能在 Actions 通过后说“已验证”；`74x165_piso_16pin` profile archetype 可以批量生成 `needs_review` 器件档案骨架，但不会自动进入验证，直到人工用公开 datasheet 改成 `ready`。`ask` / `Runner` 通过 structured tools 回答问题；`get_component("U999")` 这类 unknown path 会返回 `found=false`，而不是让模型编造。Eval Pack 只作为 regression / guardrail smoke，不包装成专家准确率 benchmark。

---

## Q1. 这个工具帮硬件工程师省了哪一步？

**v0.1**: 省原理图检视时在 SCH、BOM、datasheet、pin 定义和需求之间反复查证、对位号、整理意见的搬运链。AI 先生成带证据的检视意见，工程师集中判断是否接受和修改。

**v0.2 process calibration**: 真实流程里，原理图检视发生在画 PCB 之前；评审输入以 SCH 为主，评审人会同时查 BOM、datasheet、pin 定义和需求。输出是检视意见，开会 review 是否接受并更改，最终形成评审记录。

**v0.5 (Slice 1 evidence)**: 真实评审输入瘦到 2 类——sch + 通用 checklist（其它"软硬件接口/Connector_pin_define/FMEA/仿真建议"都是评审之后才出的下游产物）。Slice 1 跑通的最小闭环：CLI `hardwise review pic_programmer --rules R001` → 解析 121 个 component → 跑 R001 (新建器件候选识别) → 经 Refdes Guard + Evidence Ledger → 输出对齐《SCH_review_feedback_list 汇总表》的 markdown 报告。在已完成的公开样例 `pic_programmer` 上结果是"0 candidate findings, 121 components reviewed"——这是**诚实输出**，因为 KiCad 公开 demo 的所有真实器件都已 layout 完成、footprint 字段都填好。

**v3.0 (Slice 3 evidence)**: R003 NC pin handling 接入后，注意力分配清单从单字段变成跨字段+跨 unit 的 pin 级别。第一版 `hardwise review ... --rules R001,R002,R003` 在 pic_programmer 上产 84 条 finding（7 R002 + 77 R003），R003 覆盖 6 个主表 NC pin（J1 DB9 上 4 个 + LT1373 上 2 个）+ 71 个 PIC 插座 NC pin。后续按 review 视角收敛噪音：连接器/插座类 NC pin 聚合成低风险摘要，IC 类 NC pin 继续逐 pin 保留；R002 对已声明 `/V` 的电容不再生成提醒行。当前同一 demo 输出 28 条有效 finding，且 sanitizer 为 0 个未验证 refdes 包裹。所有 NC pin 用"坐标匹配"从 `no_connect` 标记反查到具体 refdes/pin_number，不依赖 model 输出 pin 信息，从结构上杜绝 pin 级幻觉。

**v3.2 eval harness evidence**: 为了避免只靠单 demo 自证，新增 `hardwise eval`：从 public KiCad corpus manifest 跑 R001/R002/R003，写 `eval-summary.json/html`；再用 `--baseline ... --accept-baseline` 接受一个已检查结果，后续运行自动生成 `eval-comparison.json`。MVP gate 只挡明显工程回归：project parse failure、新增 unverified refdes wrapping、新增 evidence dropped；finding 数量变化先作为观察项，因为有用规则也可能合法增加/减少 finding。当前完整 public smoke 是 5 个 repo / 6 个有 components 的 KiCad project / 1707 components，另有 10 个空 KiCad directory 被明确标成 skipped；输出 437 条 finding，其中 decision split 是 298 likely_issue / 99 reviewer_to_confirm / 40 likely_ok / 0 undecided，guard/evidence 两个硬指标都是 0（`unverified_refdes_wrapped=0`, `findings_dropped_no_evidence=0`）。这不是专家 gold-label 正确率，而是“真实公开工程上可重复跑、可定位注意力分配回归”的工程可用性证据。

**v3.3 synthetic safety floor**: Eval Pack v0 现在是两层：public corpus 负责真实项目上的 parser/guardrail/noise regression，`tests/harness/test_must_catch.py` 负责 synthetic must-catch safety floor。后者手工构造 5 个已知关键场景（新器件无 footprint、电容缺 `/V`、电容已有 `/V` 不应报、IC NC 无 datasheet、connector 批量 NC），用 pytest 锁住“这些已知重大边界不能漏/不能回流噪音”。人工标注的 20-30 条 calibration set 是下一步，用来量化 decision precision/recall。

**v4.2 (V2.2 component dispatch)**: Review runner 已从“每条规则扫描整张 registry”改成“遍历 `Design.components`，对每个 `Component` 调用适用的 `CheckSpec`”。用户可见行为保持不变：`pic_programmer --rules R001,R002,R003` 仍是 28 findings / 121 components，guard/evidence 不退化；内部收益是每条 finding 会回挂到 `Component.findings`，R003 pin-scoped finding 还会通过 `Finding.pin_number` 回挂到对应 `Pin.findings`。这为下一步 component-centric report 铺路，同时不牺牲 `sch:...#refdes` evidence token。

**v4.3 (V2.3 component report)**: 新增可选 `--report-style component` markdown 报告。classic report 仍是默认，保证老的交付格式和 28-finding baseline 不变；component report 会先列 121 个 component summary（每个 `pass|warn|fail` rollup），再只展开有 finding 的元件。例如 `U4 - LT1373` 下直接看到 R003 pin 3 / pin 4 的 NC finding、pin number、decision 和 `sch:pic_programmer.kicad_sch#U4` evidence token。这让面试演示从“表格里找 28 行”变成“按元件看证据链”。

**v4.4 (V2.4 datasheet-driven check)**: 新增 `DatasheetProfile` JSON 和示例规则 `DS001`，把 datasheet 数值从 RAG 文本提升成可验证结构化 profile。`data/datasheet_profiles/l78.json` 记录 L7805 的 `abs_max.vin=35.0V`，evidence token 是实际 PDF 页码 `datasheet:l78.pdf#p4`。`hardwise review pic_programmer --rules R001,R002,R003` 仍保持 28 findings；显式加 `DS001` 后变成 29 findings，新增 U3 的 `reviewer_to_confirm`：Hardwise 知道 datasheet 上 Vin abs max 是 35V，但当前 schematic net parser 还不能推断 U3 输入电压，所以它要求人工确认而不是猜。

**v4.5 (V2.5 Allegro schematic netlist adapters)**: 新增第二个 EDA 输入路径：`parse_allegro_netlist()` 读取 Allegro/Telesis 第三方 ASCII 网表（`$PACKAGES` / optional `$A_PROPERTIES` / `$NETS`）；`parse_allegro_pst()` 读取 Capture/Allegro PST 三件套（`pstxprt.dat` + `pstxnet.dat` + optional `pstchip.dat`）。两条路径都聚合成 `Design(source_eda="allegro_netlist")`，包含 components、nets 和每个 connected pin 的 `Pin.net`。公开 PST 样本烟测输出 4010 components / 3422 nets，证明它不是只跑 synthetic fixture；但这仍不是 Allegro PCB 集成，不解析 `.brd`、boardview、placement、routing 或 PCB geometry。对标 EDA.cn / CADY 后，Hardwise 把“网表+BOM”拆成两层：V2.5 netlist adapter 只负责 topology；后续 BOM matcher 再用 CSV/XLSX 的 refdes/MPN join 到 `Design.components`，提升 datasheet 匹配准确率。

**v4.6 (V2.6 BOM matcher)**: V2.6 把后续 BOM matcher 落成 `src/hardwise/bom/`：`parse_bom()` 读取 Cadence `.BOM` 报表和简单 CSV/TSV，展开跨行 grouped Reference；`match_bom_to_design()` 只用 refdes join 到 `Design.components`，输出 matched / BOM-only / design-only / duplicate / quantity mismatch，不改 nets/pins。公开样本 `inspect-bom-match <public allegro PST dir> <public .BOM>` 输出 4010 design refdes / 4010 BOM rows / 4010 matched / 0 mismatch。这个数字证明“netlist + BOM”方案在真实导出上闭环，但仍只是 schematic-review 的 component identity matching，不是 PLM BOM、生命周期、价格或供应链审核。

**v4.7 (V2.7 component-centric Allegro+BOM report)**: V2.7 把 V2.5/V2.6 的结构化事实变成可交付 markdown：`hardwise report-allegro-bom <PST-or-netlist> <BOM>` 输出一份按器件组织的 intake report。报告头显示 netlist/BOM/counts/status，mismatch 章节列 BOM-only / design-only / duplicate / quantity mismatch，主体表每行一个 design component：refdes、match status、value、MPN、manufacturer、package、connected pins、bounded nets、BOM source line 和 design source token。公开样本 smoke 生成 `4010/4010 matched, 0 mismatches` 的 4042 行报告。它仍不叫 review：没有 electrical-rule finding，不解析 `.brd`/boardview/PCB geometry，也不做 PLM/价格/生命周期判断。

**v4.8 (V2.8 report index)**: V2.8 没急着做“AI 判断”，而是先把 V2.7 的 4000 行 flat component table 加上 reviewer 能扫读的入口：`Component Prefix Summary` 按 R/C/U/J 等前缀统计 design/matched/design-only/BOM-only/duplicate；`BOM Item Groups` 按 BOM item 聚合 quantity、MPN、manufacturer、refdes sample 和短 source token；CLI 增加 `--summary-only` 与 `--mismatch-only`。同一个公开 Allegro+BOM 样本现在能生成三种交付：完整 4209 行、summary 194 行、mismatch triage 27 行，三者都是 `4010/4010 matched, 0 mismatches`。这一步仍是 intake/index layer，不输出电气 PASS/FAIL，但它是以后 datasheet match、pin profile、单器件验证报告和 Web UI 的底座。

**v4.9 (V2.9 document match)**: V2.9 在 V2.8 的 BOM item index 上加了一层本地 datasheet/document match：用户给一个 CSV/TSV document index，里面可以有 MPN、manufacturer、value、title、URL/path；Hardwise 按 BOM item 的 MPN 优先匹配，必要时用“看起来像料号”的 value 兜底，再按 manufacturer 收窄。输出不是 PASS/FAIL，而是四种证据状态：`matched`（唯一匹配）、`no_result`（索引里没有）、`ambiguous`（多份文档候选）、`manual_needed`（缺少可用 identity 或 manufacturer 冲突）。CLI 是 `report-allegro-bom --document-index docs.csv`，报告新增 `Datasheet / Document Match Summary` 和 per-item rows，所有文档链接有 `doc:<file>#line<N>` source token。它刻意不做 live supplier search、生命周期/价格/库存、PLM BOM，也不判断电路设计是否正确。

**v5.0 (V3.0 pin profile)**: V3.0 没直接生成单器件 PASS/WARN/ERROR，而是先把 datasheet profile 从“几个散字段”升级成 per-pin 结构化 facts。`DatasheetProfile` 保留 `abs_max/recommended/pin_function` 给 DS001 兼容使用，同时新增 `pins[]`：每个 pin 有 number、name、category、function、limits、recommended_topology 和 evidence tokens。公开 L78 profile 现在能输出 3 个 pin：VI/GND/VO；`hardwise report-pin-profile data/datasheet_profiles/l78.json` 会生成一份只含 datasheet pin facts 的 markdown，明确不做 schematic validation、电气 PASS/FAIL、供应商/PLM/PCB。这个层是 V3.1 单器件验证报告的输入底座。

**final answer shape**: 它不替代硬件工程师下判断，而是把“原理图里哪些对象需要看、这些对象来自哪里、每条意见有没有证据”先整理成可审计清单。工程师省掉的是查位号、对 pin、整理证据和排除模型胡编对象的搬运时间；最终是否接受 finding 仍由人审。

---

## Q2. 输入数据是什么，输出报告是什么？

**v0.1**: 输入：原理图工程、BOM、datasheet、pin 定义/接口表、需求和通用 checklist。输出：markdown 检视意见清单，每条意见包含对象、问题描述、证据来源、建议动作和待人工确认状态。

**v0.2 evidence**: 当前样例是 KiCad 官方 `pic_programmer`，已能从 `.kicad_sch/.kicad_pcb` 抽出 121 个 registry 项。还没接 BOM/DRC/datasheet。

**v1.0 (Slice 2 closed)**: 输入 = KiCad 工程目录（`.kicad_sch` + `.kicad_pcb`）+ `data/checklists/sch_review.yaml`。输出 = 一份 markdown report + 一份 `memory/rules.md` 候选规则池。

具体在 `pic_programmer` 上跑 `uv run hardwise review data/projects/pic_programmer --rules R001,R002`，得到的真实输出：

- Report header："Components reviewed | 121, Rules run | R001, R002, Findings | 6, Sanitizer | 0 unverified refdes wrapped, 0 findings dropped (no evidence)"
- 6 条 finding 全部由 R002 产生：C1/C2/C5/C6/C7/C9 的 value 字段缺 `/V` 耐压后缀，全部是 `decision=likely_issue`；C3=`22uF/25V` 已声明耐压，不再生成低价值提醒行
- R001 出 0 条——`pic_programmer` 是已完成的 KiCad 公开样例，所有真实器件都已 layout，footprint 都填好。这是**诚实输出**，不是 R001 漏判。
- 每条 finding 都带 `evidence_tokens=["sch:pic_programmer.kicad_sch#C2"]` 这种位号+源文件+refdes 三段式定位
- `memory/rules.md` 因为 R002 medium 触发了 ≥3 的阈值，写出一条 `STATUS: candidate`，建议人工把"系统性 value 字段缺耐压标注"反馈给器件库维护者

**final answer shape**: 输入是公开 KiCad 工程、公开 datasheet 和 checklist；输出是 markdown/HTML review report、SQLite/PG 结构化 store、可选 trace ledger。面试时只展示主 report 和一条 `ask` 问答，不把 memory/trace/store 都讲成主产品。

**v3.1 report polish**: 报告现在有两种并存输出：默认 markdown 适合 git diff / 纯文本归档；`--format html` 生成中文单文件 HTML，按 rule 折叠、风险等级色码、位号/网络 chip、证据定位 token 等宽展示，并把 R001/R002/R003 的英文工程字段转成硬件工程师更容易扫读的中文检视意见。两者复用同一个 `Finding` schema，没有引入第二套 finding 形状。

**v5.0 input/output boundary**: V3.0 之后输入模型可以这样讲：native KiCad project 是最高保真入口，有位号、symbol 字段、datasheet path 和可视定位；Allegro schematic netlist 是跨 EDA 的 topology 入口，覆盖 Telesis 单文件和 Capture/Allegro PST 三件套，有 refdes/pin/net；schematic-exported BOM 是 netlist-only 场景的 component identity aid，用 refdes 补 value/MPN/manufacturer，不是 PLM BOM；本地 document index 是 datasheet/document link aid，用 BOM identity 匹配公开文档，不是 live supplier database；structured pin profile 是 datasheet facts aid，用 source-tokened JSON 描述 pin function/limits/topology。输出上，KiCad `review` 产 checklist finding report；Allegro `report-allegro-bom` 产 component-centric intake/index report；`report-pin-profile` 产 datasheet pin facts report。Hardwise 当前 shipped 的是 KiCad review、Allegro topology、BOM refdes matching、Allegro+BOM intake/index report、local datasheet/document match、structured pin profile 六块，仍不碰 `.brd`、boardview、placement、routing、PCB geometry、PLM/lifecycle/pricing/availability 或供应商风险。

**v5.1 (V3.1 single-component validation report)**: V3.1 把 V2.5/V2.6 的 Allegro topology+BOM identity 和 V3.0 的 structured pin profile 接起来，新增 `report-component-validation <netlist_or_pst> <refdes> <profile.json> --bom <bom>`。现在可以对一个选中的器件生成 component validation markdown：报告头显示 refdes/value/MPN/profile part/overall status，pin 表显示 pin no/name/category/net/status/summary/evidence。第一片落地的是 L78 regulator：VI 接 `+12V`、GND 接 `GND`、VO 接 `+5V` 时输出 `PASS/WARN/ERROR=3/0/0`。这仍然是 deterministic schematic-side validation，不是模型自由写报告，也不是 PCB/boardview/PLM/supplier/lifecycle/pricing 工具。

**v5.2 (V3.2 local validator UI)**: V3.2 新增 `report-validator-ui <netlist_or_pst> <bom> <refdes> <profile.json>`，生成一个单文件 HTML：左侧是 component index，右侧是选中器件的 validation detail、schematic nets、scope boundary 和 download report。它复用 V3.1 的同一个 `ValidationReport`，不是第二套判断逻辑。这个阶段的意义是把目标产品截图里的“器件列表 + 验证详情”工作流先变成本地可打开 artifact；它没有引入 hosted Web app、WebSocket、boardview canvas、PCB parser 或供应链/PLM 状态。

**v5.3 (V3.3 XL1509 DCDC validation)**: V3.3 把单器件验证从 L78 三脚线性稳压器推进到 XL1509 buck converter。输入仍是 Allegro schematic netlist + schematic BOM + structured profile；`xl1509_buck` synthetic fixture 里 `U12=XL1509-12E1`、VIN 接 `+24V`、FB 接 `+12V`、OUTPUT 接 `D5 + L1`。结果里 8 个 profile pins 都 PASS，但 overall status 是 `ERROR`，因为 component-level checks 抓到两条确定错误：`D5=1N4007W` 不是 Schottky-style freewheel diode，`L1=6.8uH` 低于 profile 里的 68uH minimum。这个例子很适合面试讲“Hardwise 不是用模型写一篇像样的报告，而是把能从 BOM+netlist+profile 稳定判断的事实先 deterministic 化”。它仍不做 MCU/gate-driver/LED/三极管泛化，也不碰 `.brd`、boardview、placement/routing、PCB geometry、live supplier、PLM、生命周期或价格库存。

**v5.4 (V3.4 multi-validation UI)**: V3.4 把 V3.2 的单器件 UI 扩成 batch artifact：`report-validator-ui-batch <netlist_or_pst> <bom> U1=l78.json U12=xl1509.json`。它不会自动猜每个器件该用哪份 profile，而是要求显式 target；然后对每个 target 复用同一个 `validate_component_against_profile()`，在一个 HTML 里显示多个 validated devices。mixed fixture 里 U1 是 L78 PASS，U12 是 XL1509 ERROR，所以可以一眼看到目标产品截图里“多个器件状态 + 点击/切换详情”的雏形。这个阶段仍是静态 artifact：没有 hosted app、WebSocket、boardview canvas、PCB parser、供应链或 PLM。

**v5.5 (V3.5 validation targets manifest)**: V3.5 把 V3.4 命令行里手写的 `U1=... U12=...` 变成可提交的 YAML manifest：`report-validator-ui-batch ... --targets-manifest mixed_regulators_targets.yaml`。这一步解决的是复现性和维护性：reviewer 可以看到这个 demo 明确验证哪些 refdes、每个 refdes 用哪份 structured profile。它仍然不做自动 profile matching，因为从 BOM MPN 到正确 datasheet/profile 需要 normalization、封装区分和人工确认；V3.5 只是把显式选择固化下来，继续复用同一个 `ValidationReport` 和同一个静态 UI。

**v5.6 (V3.6 profile candidate manifest)**: V3.6 没有直接“自动验证全 BOM”，而是加了 `suggest-validation-targets <bom> --profiles data/datasheet_profiles`。它用 BOM 的 MPN 优先、part-like value 兜底，和本地 profile 的 `part_number` 做 normalized exact match，然后输出候选 YAML：matched 的 U1/U12 可以变成 V3.5 targets，D5/L1 这类没有 profile 的器件会留在 `no_result`。这一步的面试价值是边界感：Hardwise 开始自动化 profile assignment 的前半步，但所有候选仍然可审查，且不碰 live supplier、PLM、PCB 或模型自由猜测。

**v5.7 (V3.7 product-like validator UI)**: V3.7 没有扩大验证覆盖，而是把 batch artifact 打磨得更接近真实设计验证器：顶部是项目和 PASS/WARN/ERROR 汇总，左侧是可过滤器件索引，中间是验证卡片，右侧默认打开最严重的问题器件。mixed fixture 里会优先展示 `U12 ERROR`，并把 pin 摘要、`D5=1N4007W` 续流二极管错误、`L1=6.8 uH` 电感错误、原理图连接和 scope boundary 放进同一个静态 HTML。这个阶段仍复用同一个 `ValidationReport`，没有第二套 UI 判断逻辑，也没有 hosted app、boardview、PCB geometry、supplier 或 PLM。

**v5.8 (V3.8 EG2132 gate-driver validation)**: V3.8 把 deterministic validation 从 regulator/DCDC 扩到半桥 gate driver。`eg2132_gate_driver` synthetic fixture 里 `U3=EG2132`，VCC 接 `+12V`，HIN/LIN 接 PWM nets，HO/LO 通过栅极电阻到 Q 器件，VS 接半桥开关节点，VB/VS 有 bootstrap 电容；故意放了 `D1=MBRA210LT3G` 作为低耐压 bootstrap diode。输出仍是同一个 `ValidationReport`：pin rows 多数是 generic WARN/PASS，真正的 family 判断在 `component_checks`，最终 overall `ERROR` 来自 bootstrap diode rating below required 24 V。这个例子展示 Hardwise 可以做“拓扑事实 + BOM identity”的稳定检查，但仍不碰死区时序、MOSFET 损耗、PCB 回路、供应链或 PLM。

**v5.9 (V3.9 design-validator workbench entry)**: V3.9 把目标截图里的“打开项目就看到设计验证器”做成一个静态本地入口：`design-validator-ui <netlist_or_pst> <bom>`。它先用 `suggest_profile_candidates()` 从 BOM identity 自动匹配本地 structured profiles，再对 matched refdes 复用同一个 `validate_component_against_profile()`，最后渲染一个单文件静态工作台：顶部是项目摘要，下方是器件列表、验证区和报告详情。V3.9 的 `mixed_power_stage` smoke 当时输出 18 components / 3 validated / PASS-WARN-ERROR=1-0-2 / 15 manual；U12 和 U3 是 ERROR，U1 是 PASS。未匹配器件不会被假装验证，而是在 project index 里作为 manual/no-profile 暴露出来。它仍不做真实上传、账号次数、hosted app、`.brd`/boardview/PCB geometry、live supplier、PLM、生命周期或价格库存。

**v5.10 (V3.10 STM32G030 MCU/SWD validation)**: V3.10 把验证覆盖从 power/regulator/gate-driver 扩到 MCU debug/startup basic。`stm32g030_mcu` synthetic fixture 里 `U8=STM32G030C8T6`，VDD/VDDA/VBAT 接 `+3V3`，NRST 有上拉/RC，BOOT0 下拉，但故意把 PA13/SWDIO 接到 `SWCLK`、PA14/SWCLK 接到 `SWDIO`。输出仍然是同一个 `ValidationReport`：pin rows 只确认 profile pins 存在和基础电源/地，真正的 MCU 判断在 `component_checks`，最终 overall `ERROR` 来自 SWDIO/SWCLK swap。`design-validator-ui` 在 mixed controller power-stage fixture 中自动匹配 U8 profile，所以当前公开 demo 是 25 components / 4 validated / PASS-WARN-ERROR=1-0-3 / 21 manual，并展示 U1 PASS、U12/U3/U8 ERROR。它仍不做 firmware、clock tree、完整 alternate-function matrix、调试器枚举、PCB layout、supplier 或 PLM。

**v5.11 (V3.11 zero-profile coverage workbench)**: V3.11 解决真实项目最常见的第一步：BOM 和 netlist 已经能导入，但本地 structured profiles 覆盖为 0。`design-validator-ui` 现在不再因为 `validated=0` 退出失败，而是生成 coverage/gap workbench：顶部显示器件数、BOM matched、已验证 0、待 profile 数；左侧 component table 标出 `no_result / ambiguous / manual_needed`；中间列列出 profile coverage counts；右侧说明这是 coverage artifact，不把 no-profile rows 转成 PASS/WARN/ERROR。这个变化没有新增任何 profile、规则或 parser，只是让真实公开项目能先进入“缺口可审计”的评审状态。

**v5.12 (V3.12 grouped coverage + local docs column)**: V3.12 把 zero-profile workbench 从“4010 个逐位号缺口”推进到“按 BOM/device group 扫读”。真实公开 Allegro 文件夹现在可以直接跑 `design-validator-ui <allegro-folder>`：CLI 自动选 PST 三件套和最佳 `.BOM`，输出 4010 components / BOM matched=4010 / validated=0 / manual=4010；HTML/Markdown/JSON 同时新增 132 个 `component_groups`。每个 group 有 refdes sample/count、normalized identity、identity kind、suggested family、profile status 和 Docs 状态。`--document-index docs.csv` 复用本地 document index 匹配，能把某个 BOM group 标成 `matched / no_result / ambiguous / manual_needed`，但不做 live datasheet download、事实抽取或新的 PASS/WARN/ERROR 判断。这一步回答“新项目有新器件怎么办”：先通用地分组和找文档，再由后续 family validator 消费结构化 datasheet facts。

**v5.13 (V1 power-family cut)**: V1 收束成一个可验证闭环，而不是继续无限补器件库：真实公开 Allegro 文件夹仍是一键导入，JSON 保留 4010 rows 和 132 个 component groups；`--document-index data/document_indexes/power_v1_docs.csv` 把 MPQ8626 两个 BOM groups 标成公开文档 `matched`；`mpq8626.json` 用 `part_number_aliases` 覆盖 `MPQ8626GD` / `MPQ8626GD-Z`，并声明 `topology_family=buck`、`buck_topology=synchronous`。同一个 buck family validator 现在支持 switch-output category、`PL`/`L` 电感前缀和同步 buck 不需要外部续流二极管的规则。真实项目 smoke 输出 4010 components / 132 groups / document matched=2 BOM groups / validated=4 / PASS-WARN-ERROR=4-0-0 / manual=4006；四个真实 refdes 是 U13/U20/U23/U26。边界也很清楚：这不是自动下载 datasheet、不是自动抽取所有 profile、也不是验证整张板；它证明的是“全项目 coverage + 公开 docs 匹配 + 一个真实 power family validator”这条链路成立。

**v5.14 (V1.1-V1.3 grouped profile loop)**: V1.1-V1.3 没有继续盲目堆器件 profile，而是把“新项目有新器件怎么办”收成一个可审查流程。V1.1 新增 `build-document-index-candidates <validation-index.json>`：从 132 个 component groups 里生成 document-index candidate CSV，默认排除阻容值、连接器/机械件和已匹配 docs 的 group；真实项目 smoke 生成 25 个候选，适合人工补公开 datasheet URL。V1.2 新增 `draft-datasheet-profile ... --identity ...`，输出 `review_status=needs_review` 的 profile 草稿，profile matcher 会跳过非 `ready` 草稿，避免半成品进入验证。V1.3 增加 PCA9548A/I2C mux 作为第二个真实 family validator：检查 VDD、上游 SDA/SCL、RESET/A0/A1/A2、SCn/SDn channel pair。真实 Allegro 项目用 `data/document_indexes/family_v1_3_docs.csv` smoke 输出 4010 components / 132 groups / docs matched=3 groups / validated=9 / PASS-WARN-ERROR=9-0-0 / manual=4001；validated refdes 是 U13/U20/U23/U26（MPQ8626）和 U8/U9/U10/U11/U130（PCA9548A）。边界仍然是本地公开 document index + 人审 profile，不做联网下载、PDF 自动抽取、PCB/layout、PLM 或供应链。

**v5.19 (Evidence-first UI)**: C2 没扩大 validator 覆盖，而是把“可信度”直接放到 UI 里：deterministic `ValidationReport` rows/checks 显示 `L1 deterministic`，no-profile/manual coverage rows 显示 `L3 manual`，datasheet/profile evidence token 以可复制、可搜索的 chip 显示，Copilot `Evidence / Tool trace` 从一行 raw `input=... evidence=... wrapped=...` 改成 tool/status、summary、evidence、Guard wraps、Input 分区。`design-validator-ui ... --ai-snapshot` 在 `mixed_controller_power_stage` 上 smoke 仍是 25 components / validated=4 / PASS-WARN-ERROR=1-0-3 / manual=21。关键边界：这里还没有输出 `L2 grounded` 结论；它只是先把未来 constrained-LLM 的 trust slot 预留出来，同时不改变任何 validation truth。

**v5.20 (C3 coverage analytics loop)**: C3 没把 no-profile 器件偷偷变成验证结论，而是把 coverage loop 变成可排序的工程队列。`build-document-index-candidates` 现在给候选追加 `Priority`，按 profile gap 优先、再按 family safety weight / refdes count / validator-likelihood 排序；已有 ready profile 但缺 docs index 的 backfill 不会盖过真正缺 profile 的器件。新增 `recommend-next-family <validation-index.json>` 输出 Markdown advisory ranking，不出现 PASS/WARN/ERROR：C3-era 65-component `motor_sensor_controller` public-safe synthetic Allegro fixture smoke 是 8 validated / 57 manual，推荐里 diode 11 refdes、transistor 6、ic 4、inductor 5、ferrite 3、unknown 2，并只给 `try_existing_validator_profile` / `triage_for_new_validator` 两类人审动作。边界：这仍是 L3 coverage artifact，不做自动 profile promotion、datasheet fact extraction、supplier/PLM、PCB/layout，也不改任何 deterministic validator dispatch。

**v5.21 (C4 LED indicator L3→L1 slice)**: C4 按 C3 ranking 选 diode 里的 LED indicator group，而不是继续凭感觉扩 coverage。`LTST-C190KGKT` 新增 reviewed ready profile，仍走 `recommended.topology_family="diode"` dispatch，只用 `recommended.diode_role="led_indicator"` 触发两条额外 L1 checks：anode/cathode polarity 和一跳串联分支限流电阻。follow-up 修正了公开 pinout：pin 1 = Cathode、pin 2 = Anode，并把限流规则从“任意 resistor neighbor”收紧为“非全局 rail 的 LED branch 上有 series resistor”；D10-D17 共用 R32 时报告明确说 shared current-limit resistor。当前 `motor_sensor_controller` public-safe synthetic Allegro fixture 是 66 components；D10-D17 从 no-profile/manual 变成 deterministic PASS rows，smoke 输出 validated=16 / manual=50 / PASS-WARN-ERROR=12-1-3，`recommend-next-family` 里的 diode uncovered 从 11 降到 3（剩 TVS/signal diode groups）。另有 focused fixture 覆盖 missing current limit、reversed polarity、unrelated rail resistor false PASS 和 shared resistor wording。边界：这不是 generic LED/TVS/Schottky expansion，不算电流大小、不做光学/热设计、不用 LLM，也不按 MPN 文本分支。

**v5.22 (C4b MMBT3904 transistor L3→L1 slice)**: C4b 继续按 C3/C4 的 ranking-driven 路线，而不是跳到 L2。C4 后最高缺口是 transistor：`MMBT3904` 6 个 refdes。新增 `mmbt3904.json` reviewed ready profile，复用已有 `recommended.topology_family="bjt"` validator；关键修正是不要把 TO-92 `2N3904` pinout 套到 SOT-23 `MMBT3904` 上，onsemi 公共 datasheet 显示 SOT-23 pin 1 = Base、pin 2 = Emitter、pin 3 = Collector。`motor_sensor_controller` public-safe synthetic Allegro fixture 同步把 Q10-Q15 改成 base=DRV10-DRV15、emitter=GND、collector=OUT10-OUT15。smoke 输出变成 validated=22 / manual=44 / PASS-WARN-ERROR=12-7-3；Q10-Q15 是 L1 deterministic WARN，因为 base/collector 网名无法静态推断电压，validator 明确不假设 emitter 外的节点电压。`recommend-next-family` 里 transistor group 被吃掉，下一名变成 IC。边界：不是 generic transistor expansion，不做 beta/current gain、base resistor sizing、thermal、simulation、PCB/layout，也不引入 L2/LLM。

**v5.23 (C4c analog IC basic pin-profile slice)**: C4c 没跳到 generic IC validator，而是把 C4b 后 ranking 第一的 IC group 收窄成 basic pin-profile coverage。新增 `lmv358.json`、`lm393.json`、`ina180a1.json`、`tlv9062.json` 四个 reviewed public TI profile，使用 `recommended.validation_scope="basic_pin_profile"`，不新增 `topology_family` dispatch。generic pin validator 只补了两个连接性类别：`analog_output` 和 `open_collector_output`；它们只证明 pin 存在且连到网，不判断 op-amp 增益、比较器阈值、电流采样精度、输出摆幅、稳定性、shunt sizing 或 layout。`motor_sensor_controller` public-safe synthetic Allegro fixture 把 U20/U21/U23 的第二通道缺失 pin 补成完整连接，用来证明 nominal basic coverage。smoke 输出变成 validated=26 / manual=40 / PASS-WARN-ERROR=16-7-3；`recommend-next-family` 里 IC group 消失，下一名变成 inductor。边界：这仍是 L1 pin-level deterministic coverage，不是模拟行为审查，也不是 L2/LLM。

**v5.24 (C4d SMBJ24CA bidirectional TVS slice)**: C4d 没硬吃 ranking 第一的 inductor，因为 fixture 里的 `IND-6R8` / `IND-10UH` 没有公开 datasheet 证据，强行做会变成 fixture-only profile。C4d 选择 ranking 第二但有现成 diode validator 的 `SMBJ24CA`，新增 Littelfuse public-reviewed profile，并在既有 `topology_family="diode"` 下加 `diode_role="bidirectional_tvs"` 子角色。TVS 不是 cathode/anode 方向器件，profile 用 `Terminal 1/2`；validator 只检查两端连接、一端到 GND、保护 rail 和 GND 的工作电压不超过 24 V standoff。`motor_sensor_controller` 里 D20 是 `+24V` 到 `GND`，所以 smoke 变成 validated=27 / manual=39 / PASS-WARN-ERROR=17-7-3；`recommend-next-family` 的 diode 剩 `BAS316, BAV99`。边界：不做 surge sizing、ESD 等级、clamp waveform、capacitance、热、connector completeness、PCB/layout，也不引入 L2/LLM。

**v5.25 (C4e BAS316 small-signal diode profile slice)**: C4e 继续吃剩余 diode，但只做两端 `BAS316`，明确不碰 `BAV99` 三脚双二极管。新增 Nexperia public-reviewed `bas316.json`，复用既有 `topology_family="diode"` 的 cathode/anode connectivity 和 reverse-voltage check；profile pinout 是 SOD323 pin 1 = Cathode、pin 2 = Anode，`reverse_voltage=100 V`。`motor_sensor_controller` 里 D21 是 `CANH` 到 `GND`，所以连接性 PASS，但 reverse voltage 因 `CANH` 无法从网名静态推断而 WARN；smoke 输出 validated=28 / manual=38 / PASS-WARN-ERROR=17-8-3。`recommend-next-family` 的 diode 只剩 `BAV99`。边界：这是 profile-only L1 row，不做 CAN protection suitability、反向恢复时间适配、ESD/surge、capacitance、PCB/layout，也不做 BAV99 dual-diode modeling。

**v5.28 (real Allegro breadth + topology depth slice)**: 真实公开 Allegro 样本现在不再是“只精检 9 颗”。`design-validator-ui <public Allegro folder> --ai-snapshot --index-json ...` 输出 4010 components / BOM matched=4010 / validated=3738 / manual=272 / PASS-WARN-ERROR=3653-79-6。关键不是把 3738 都包装成深度 datasheet review，而是分两层讲：`GENERIC_CAPACITOR` 2018 + `GENERIC_RESISTOR` 1624 是全板 light deterministic coverage，解析 BOM value/package 并在能推断 rail voltage 时做耐压/功耗类检查；profile-backed deep checks 包括 `LN2312LT1G` 56、`74LV165` 10、`PCA9617A` 8、`PCA9548A` 5、`MPQ8626` 4 和二极管包 13。面试最值得讲的是 `74LV165`：它证明 Hardwise 能检查串行链拓扑（load/clock fanout、Q7->DS cascade），不是只会看“电源电压对不对”。二极管包也刻意保守：`1.5SMC15A` 5 和 `SM340AF` 5 都 PASS，`SD103AWS-7-F` 3 因控制网名无法静态推电压而 WARN；`RF-GTB191TS-BC` 6 颗 LED 虽然路径像“3V3->330R->LED->NMOS”，但公开极性图和本地符号命名不一致，先留 manual，不为覆盖率硬给 PASS。边界仍然是不做 PCB/layout、供应链/PLM、自动 PDF 抽取或 LLM verdict。

**v5.29 (demo readiness closeout: Windows CI + profile archetype)**: 这一步没有继续堆 MPN，而是把“可复现”和“可规模化”两条面试追问补上。Windows 侧新增 `docs/windows.md` 和 GitHub Actions `macos-latest` / `windows-latest` matrix；口径保持保守：主 CLI 和本地原理图检验工具路径预计可在原生 Windows 跑，WSL 是低摩擦兜底，只有目标 commit 的 `windows-latest` 通过后才说 Windows 已验证。profile 侧新增 `draft-datasheet-profile --archetype 74x165_piso_16pin`：从 project index 的 BOM/component group 生成 16-pin PISO shift-register `needs_review` 骨架，带 aliases、`recommended.topology_family="shift_register_piso"`、load/clock/Q7/DS/CE pin metadata 和 `reviewer_to_confirm:*` evidence placeholders。关键安全点：生成物仍是 `needs_review`，`suggest-validation-targets` / `design-validator-ui` 会跳过它；只有人工核对公开 datasheet pinout、封装映射、电压限制、aliases 和 evidence tokens 后，才能改成 `ready` 进入自动验证。这个回答“其他同类型器件怎么办”：不是复制 validator，而是 family validator 泛化规则，profile archetype 降低人审 profile 的起步成本。

**v5.30 (D1 mainboard profile-gap analysis)**: D1 把真实公开 mainboard 的输入问题拆清楚：PST topology 早就能解析，`inspect-allegro-netlist <folder>` 是 8180 components / 6918 nets / 24563 properties；卡点在 BOM，`RFMS5H2TABom(13).xlsx` 是中文表头，现有 parser 只认 Cadence text BOM 和 CSV/TSV。新增窄 `.xlsx` BOM intake 后，`位号` 按 refdes join、`数量` 按 quantity、`名称` 作为 conservative display identity，`编号` 只作为 source item number，不冒充公开 MPN。真实 smoke：`design-validator-ui <folder>` 自动选择这个 `.xlsx`，输出 8180 rows / BOM matched=7248 / validated=6573 / PASS-WARN-ERROR=3867-2706-0 / manual=1607；JSON 里有 195 个 component groups。后续 `build-document-index-candidates` 生成 75 个候选，`recommend-next-family` 排出 6 个 family，其中 IC/transistor/diode 可以先尝试既有 validator/profile 路线。重点讲法：这不是“整板都验证了”，而是把大板先变成可审计 coverage queue；BOM join 的 932 个 design-only 和 9 个 duplicate BOM refdes 保留为 intake 事实，不被掩盖。

---

## Q3. 哪些进向量库，哪些进结构化库？为什么这样分？

**v0.1**: datasheet 长文本无 schema、需语义检索 → 向量库；元件/网络/BOM/DRC 结果是强 schema 关系数据、要 join 和位号校验 → 结构化库。混存会让位号查询和参数引用都失去可信度。

**v1.0 (Slice 3 shipped)**: 双库都已 live，refdes 是 join key。

- **关系库（SQLite + SQLAlchemy）**：`src/hardwise/store/relational.py`，两张表 `components`（refdes 唯一索引，value/footprint/datasheet/source_file/source_kind）+ `nc_pins`（refdes/pin_number/pin_name/pin_electrical_type）。在 `pic_programmer` 上跑 `uv run hardwise review ... --rules R001,R002,R003` 后写入 121 个 components + 77 个 NC pins。
- **向量库（Chroma local persistent + ONNX MiniLM）**：`src/hardwise/store/vector.py`，每个 chunk 的 metadata 至少 `{part_ref, source_pdf, page, chunk_index}`。`part_ref` 现在按 datasheet identity 讲清楚，例如 `hardwise ingest-datasheet data/datasheets/l78.pdf --part-ref L7805` 切页 → chunks → upsert，`hardwise query-datasheet "absolute maximum input voltage"` 返回 top-k 带 `[l78.pdf p4 part=L7805]` 的 provenance 行。
- **Join key = refdes，datasheet filter key = identity**：U3 在关系库 `components` 表里有 `value=7805, datasheet=www.st.com/.../l78.pdf` 一行；L78 datasheet chunks 在向量库里用 `part_ref=L7805` 标注。DS001 的 finding 仍挂在 registry-verified `U3` 上，引用 `sch:pic_programmer.kicad_sch#U3` 与 reviewed profile token `datasheet:l78.pdf#p4`；Chroma query 是独立佐证同一页，不是在 `review` 时动态抽 token。混存会破坏这种 refdes 与 datasheet identity 分层。

**v5.15 (DR-011 Phase 2 evidence-chain hardening)**: Phase 2 的关键口径收紧为"两条证据线在同一页码 token 汇合"：Line A 是静态 `data/datasheet_profiles/l78.json` 里的 reviewed fact（`abs_max.vin=35.0`，`datasheet:l78.pdf#p4`），DS001 因此在 `pic_programmer` 上给 U3 产 1 条 `reviewer_to_confirm` finding；Line B 是官方 ST L78 PDF 的独立页面核验，当前 DS0422 Rev 38（February 2025）第 4 页仍是 "Absolute maximum ratings"，VI 对 VO=5-18 V 为 35 V。新增 fast 测试用合成 PDF 锁住 `extract_chunks()` 的 page/token/metadata 合约，不把 Chroma semantic ranking 塞进默认 pytest；真正 `query_chunks()` 排序仍归 `@pytest.mark.slow`，因为 Chroma 默认 ONNX embedder 首次运行可能下载模型。

**v5.16 (DR-011 Phase 3 BJT family)**: Phase 3 补的是器件物理正确性，不是简单再加一个 family。`validation/bjt.py` 选择 2N3904 NPN profile，依据 onsemi `2n3904-d.pdf#p1` 的 pinout（1 Emitter / 2 Base / 3 Collector）和 abs max（`VCEO=40 V`、`VEBO=6 V`）。核心检查不是“正向 Vbe 过压”，而是反向 B-E 击穿：`reverse_be_voltage = V_emitter - V_base`，超过 `abs_max.vebo` 才 ERROR。测试里高边/射极跟随场景把 emitter hint 设成 12 V、base hint 设成 0 V，base-to-ground 逻辑会误以为安全，emitter-referenced 检查正确报 `VEBO` ERROR；另有 `base=12.7 V / emitter=12 V` PASS 用例证明不是把 base 直接对地比较。dispatch 仍只看 `recommended.topology_family="bjt"`，agent bridge 不需要新工具。

**v5.26 (evidence-chain audit before narrative rewrite)**: 重新梳理后，必须把三类证据分开讲。第一类是真实检索证据：`data/datasheets/l78.pdf` 现在可以被 `ingest-datasheet --part-ref L7805 --persist-dir /tmp/hardwise-evidence-audit` 切成 157 chunks，`query-datasheet "absolute maximum input voltage"` top-1 返回 `[l78.pdf p4 part=L7805]`，`ask --vector` 会调用 `search_datasheet` 和 `get_component(U3)`，最终引用 `l78.pdf` 第 4 页 / 35 V。第二类是 reviewed profile token：例如 `datasheet:bas316.pdf#p2`、`datasheet:smbj24ca...#pN`、`datasheet:mmbt3904...#p1`，这些是人工 reviewed structured profile evidence，不等于对应 PDF 都已本地 ingest/retrieve。第三类是 coverage/ranking artifact：C3/C4 证明 queue 和 L3→L1 闭环，但它服务于 trust architecture 叙事，不替代证据链。另一个细节：`ask --vector` 的用户可见输出会把 `L78/L7805` 这种 part-number-like token 保守 wrap 成疑似 refdes，这是 Refdes Guard 的安全取舍；`U3` 这类真实 board object 仍 registry-verified。

**v4.0 (R003 datasheet closure shipped — DR-009)**: R003 现在按 DR-009 写两个新字段——结构化 `evidence_chain: list[EvidenceStep]` + 机器判断 `decision`，跟流程状态 `status` 严格分离。`hardwise review pic_programmer --rules R003 --vector` 在 77 个 NC pin 上跑 R003 闭环：每条 finding 都先按 refdes → `component.value` 推 part_ref，按 `pin {N} {name}` 做向量检索，得到 hits 后用 `\bpin\s*N\b` + `\b(NC|no.connect|not connected)\b` 两个正则在 hit 文本里筛 → 命中 NC 关键词 = `likely_ok`；命中 pin 但无 NC 关键词 = `likely_issue`；无相关命中 = `reviewer_to_confirm`。

`pic_programmer` 当前 Chroma 只有 L78 datasheet (part_ref="U3", 157 chunks)，而 U3 是 3 pin 稳压器无 NC pin；77 条真实 NC pin 都在 U4/J1 等没 ingest datasheet 的器件上 → R003 全部输出 `decision=reviewer_to_confirm` + evidence_chain 只含 EDA step。这是**结构上正确的诚实输出**：没有可用证据时不瞎判，等 reviewer 上手。**单元测试**里有人造的 likely_ok / likely_issue / reviewer_to_confirm 三条 path，证明启发式在三个分支都按预期分类（`tests/checklist/test_r003.py` 17 项）。

设计上两个关键决策写进 DR-009：(a) `decision` 与 `status` 分离——一个 finding 可以同时 `decision=likely_ok`（机器结论）+ `status=open`（人没看）+ 之后 `status=rejected`（人否决机器），三值都能并存；(b) `EvidenceStep.source: Literal['eda','datasheet','rule']` 用 Literal 把证据通道收敛到三个真实通道，杜绝后人加 `'intuition'` 类的非证据来源。

---

## Q4. Agent 有哪些工具？为什么不让模型自由回答？

**v0.1**: list_components / get_net / check_bom / search_datasheet / lookup_checklist 等工具。模型自由回答会编造位号、网络名和参数；强制走工具意味着每条检视意见都有 query 和返回值，可审计、可复现、可被 Refdes Guard 卡住。

**v0.2 evidence**: 第一版工具面是 `inspect-kicad`/registry parser，已证明 U3、C1、D11 存在而 U999 不存在。下一步把它封装成 `list_components` 和 `get_component`。

**v1.0 (Slice 4 prep — tool manifest shipped)**: 工具面落在 `src/hardwise/agent/tools.py`，4 条工具配 4 套 Pydantic input + output，外加一个 `TOOL_DEFINITIONS` 数组直接以 Anthropic SDK `tools=[...]` 形态喂给 `messages.create`：

| 工具 | 输入 | 输出 | 未命中分支 |
|---|---|---|---|
| `list_components` | `name_filter?` / `refdes_prefix?` | `ComponentSummary[]` + total | `found=false, components=[]` |
| `get_component` | `refdes` | `ComponentFound{component}` | `ComponentNotFound{refdes, closest_matches}` |
| `get_nc_pins` | `refdes_filter?` | `NcPinSummary[]` + total | `found=false, pins=[]` |
| `search_datasheet` | `query`, `part_ref?`, `top_k` | `DatasheetHit[]` 带 `page` + `source_pdf` + `part_ref` | `found=false, hits=[], query=...` |

**为什么不让模型自由回答** 的代码兑现就在 `get_component` 的 unknown 分支：当模型问 `U999`（registry 不存在的位号），工具不会编一个，而是返回：

```python
ComponentNotFound(
    status="not_found",
    refdes="U999",
    closest_matches=["U2", "U3", "U4"],   # 来自 BoardRegistry.refdes_set + difflib
)
```

模型只能从 `closest_matches` 里选，或者向人工确认。Refdes Guard 是事后兜底（sanitize 输出文本里漏出的不合法位号）；工具层是事前防御（结构上不给模型"自由回答"的机会）。两层 defense in depth，跟 Wrench Board 把校验放在工具返回值而非 system prompt 的思路一致。

测试覆盖 7 条 fast tests（含 unknown→closest_matches 路径），CLI 集成留给下一会话的 `runner.py`——manifest 已就位，loop 是下一步。

**v4.0 (Slice 4 closed — agent loop live on MiMo)**: `runner.py` + `prompts.py` + `cli.py ask` 命令落地，4 个工具在真 API 上跑通。在 `pic_programmer` 上的 3 次真实问答：

| 提问 | iterations | tool calls | tokens in/out | cache create/read |
|---|---|---|---|---|
| `U3 是什么器件？` | 2 | `get_component(refdes=U3) → found` | 1635/240 | 0/**1472** |
| `U999 是什么器件？` | 2 | `get_component(refdes=U999) → not_found` | 129/171 | 0/**2944** |
| `U4 这颗器件有几个 NC 脚？` | 2 | `get_nc_pins(refdes_filter=U4) → total=2` | 196/154 | 0/**2944** |

关键三件事被这 3 次同时证明：

1. **Tool-use loop 在 MiMo proxy 上 1:1 跑通**，不需要任何 proxy 特化代码——`messages.create(tools=TOOL_DEFINITIONS, ...)` 直接吃；
2. **Anti-fabrication 防线真起效**：U999 那次 model 拿到 `ComponentNotFound{closest_matches: []}` 后**没编**，反而回答"没找到 U999，请确认位号"。如果没有这个 unknown 分支，model 大概率会从训练数据里编一个 "U999 应该是某某" 出来；
3. **Prompt cache 真有数字**：`cache_read_input_tokens` ≠ 0 落地——mechanism #5 不是 wiring-only。1472 ≈ 一次 system prompt cache 命中；2944 ≈ 两次迭代各命中一次。

`hardwise ask data/projects/pic_programmer "..."` 是面试现场可演示的一条命令——比"我设计了 5 个机制" 强得多。8 条 fast tests 覆盖 `Runner` 用 fake Anthropic client 跑 text-only / 单工具 / 多工具 / unknown-refdes closest_matches / 无 collection / 未知工具 / iteration cap / token 累加路径，no API key needed。

**v4.1 (2026-05-16 cold-start probe)**: 追加做了一次真正的冷启动隔离验证：用唯一 system prompt 绕开已热缓存，连续两次调用 MiMo Anthropic-format proxy（`mimo-v2.5`）。raw `usage`：

| run | input/output | cache_creation_input_tokens | cache_read_input_tokens |
|---|---:|---:|---:|
| 1 | 5445/16 | `null` | `null` |
| 2 | 5/16 | `null` | **5440** |

结论要讲准：MiMo 证明了 prompt cache **read path** 确实生效，第二次几乎不再付长 prompt 的 input tokens；但它没有回传 creation 计数，`cache_creation_input_tokens` 是 `null` 而不是非零。因此当前证据不能说"creation 字段已验过非零"，只能说"cache_control 被执行、read hit 可观测；creation accounting 需要换官方 Anthropic 或另一个会暴露该字段的 endpoint 复验"。

**v5.17 (Phase 4 closeout — validator bridge becomes part of the agent story)**: 工具面现在是 5 个，不是早期 4 个：`run_component_validation(refdes)` 把 agent loop 接到 deterministic validators。它不自动猜 profile：Runner 只有在注入 IR `design` 和显式 `validation_targets` 时才会返回 `validated`，否则是 `not_configured` / `no_profile` / `not_found`。`tests/agent/test_validation_bridge.py` 用 FakeAnthropic 证明模型发起 tool call 后，Runner 能派发到 `validate_component_against_profile()` 并拿回结构化 PASS/WARN/ERROR payload（6 passed，无 API key）。这就是 DR-011 Phase 1 的核心：模型不是“自己会验证硬件”，而是能调用已经存在的确定性 validator 并解释它的 evidence-backed 结果。

**v5.18 (Allegro Copilot workbench — agent loop becomes a product surface)**: 这 5 个工具现在还驱动一个工作台 Copilot 面板。两个入口：`design-validator-ui --ai-snapshot` 把已审计的离线问答烘焙进单文件 HTML（无服务、无 key），`serve-workbench` 起本地 FastAPI（`POST /api/workbench/chat`）。关键设计：`--fake-ai` 不绕开 Runner——它用一个确定性的假 Anthropic client 只产 `tool_use`/文本，真实的 `_dispatch` / `run_component_validation` / Refdes Guard / tool trace 照常跑；Allegro 通过 `Design → BoardRegistry` shim + 内存关系 `Session` 接入，没有改 Runner 的 registry/session 契约，也没动 guard。真模型模式在本地对一个 Anthropic-format endpoint 实跑验证过：问选中器件 U3 时模型调 `run_component_validation` 给出落在确定性判定上的答案，问 `U999` 时返回 `not_found` 且答案里 `⟨?U999⟩` 被包裹。**面试诚实点**：这套只在真·`serve-workbench` 线程池下才暴露了一个 in-memory SQLite 跨线程 bug（单线程的 fake / 单测都抓不到）——“通过测试和 fake smoke”不等于“真服务器下能跑”，最后是一条真实 HTTP 调用才完成验证（见 `learning_log.md` 2026-05-30）。

**v5.27 (C5 grounded trace tier)**: C5 没让 LLM 生成新的硬件 verdict，而是把已有 `L1 deterministic / L2 grounded / L3 manual` tier 延伸到 datasheet 问答 trace。`search_datasheet` 如果返回带 `source_pdf + page` 的 hit，Runner 的 `ToolCallTrace` 会生成 `datasheet:<pdf>#p<N>` evidence，并把该 trace 标成 `L2 grounded`；没有 vector store 或没有 hit 时就是 `L3 manual`。`run_component_validation` trace 仍是 `L1 deterministic`，它的 PASS/WARN/ERROR 仍由 validator 决定，L2 只能解释或附证据，不能覆盖 L1。为了让 file:// 静态 demo 也看得到 L2，`design-validator-ui --ai-snapshot` 新增一个 hermetic L78 evidence-chain smoke：用 seeded fake collection 返回经过审计的 `l78.pdf` 第 4 页片段和 `datasheet:l78.pdf#p4` token，不提交 Chroma artifact，也不暗示 Allegro U12 的问题引用了 L78。测试锁住两条边界：有 hit → `L2 grounded` + evidence chip；无 vector → `L3 manual` + validation fallback。

**v5.28 (Workbench AI topology tools)**: Allegro Copilot 现在不需要单独“新人导览模式”，因为右下角 AI 已经能通过 4 个 structured tools 查询 parsed topology：`get_component_context(refdes)` 返回器件身份、profile/validation 状态、pin-to-net 和邻网成员；`get_net_context(net_name)` 返回精确网络成员；`search_nets(query)` 支持 RESET/NRST、BOOT、3V3、SWD 等常见词查真实 net 名；`summarize_project_topology()` 返回 component/net counts、validation coverage、power/interface/control-like net buckets 和 profile gaps。讲边界要非常明确：这是 Allegro/PST netlist fact level，不是视觉 schematic page 理解，不自动命名模块，不碰 `.brd`、placement/routing、PLM、价格、生命周期或 datasheet web search。公开 mixed controller fixture 的 fake chat 现在可复现三类问题：`U8 接了哪些关键网络?` → `get_component_context`，`RESET 相关网络有哪些?` → `search_nets` 命中真实 `NRST`，`这张板大概有哪些已验证风险和待补 profile?` → `summarize_project_topology` 给出 25 components / 21 nets / PASS-WARN-ERROR 4-9-3。

**v5.29 (D2b reusable public document index)**: D2b 把 document coverage 从“一次性手填链接”推进到可复用工作流。`build-document-index-candidates --family transistor` 可以从 grouped coverage 里只吐 transistor review queue；CSV 里真实 parsed MPN 进 `MPN`，中文 BOM `名称` 这种 part-like identity 进 `Value`，`编号` 仍然只是 source item number，不当 public MPN。reviewed document index 现在是跨项目资产：另一个项目只要 BOM 里有同一个 parsed MPN，或人工确认过的 exact `Value` alias，就能复用同一条 public datasheet coverage。真实 mainboard smoke：D1 的 195 groups 中 transistor family 生成 3 个候选；回灌 `data/document_indexes/mainboard_d2_transistor_docs.csv` 后，`L2N7002KLT1G` / `LN2312LT1G` / `PE537BA` 三组全部 `document_status=matched`，`doc:mainboard_d2_transistor_docs.csv#line2/3/4` 在 Markdown 和 Workbench HTML 可见；PASS/WARN/ERROR 仍是 3867/2706/0，没有因为有规格书而自动变成电气验证结论。

**v5.30 (D2c L2N7002KLT1G MOSFET profile)**: D2c 给 `L2N7002KLT1G` 加了 public-reviewed ready profile：LRC PDF 第 1 页支持 SOT-23 pinout `1=Gate / 2=Source / 3=Drain`、`VDSS=60 V`、`VGS=±20 V`、稳态 `ID=320 mA`，profile alias 只收同页公开 order variant `L2N7002KLT3G`。关键不是把中文 BOM `名称` 加进 alias，而是加了一条安全桥：当 D2b document row 已经 match，并且该 row 里有公开 MPN 时，profile candidate 可以用这个公开 MPN 查 ready profile；最后还要检查本地 EDA symbol pin ids 覆盖 profile pin numbers。真实 mainboard smoke 现在是 8180 components / BOM matched 7248 / validated 6679 / manual 1501 / PASS-WARN-ERROR 3868-2811-0，比 D2b 的 validated 6573 / manual 1607 正好移动 106 个 refdes；`L2N7002KLT1G` group 是 106 refdes、`profile_status=matched`、`document_source=doc:mainboard_d2_transistor_docs.csv#line2`，`LN2312LT1G` 因 `D/G/S` 本地 pin-id 仍 `no_result`，`PE537BA` 也不在 D2c 范围内。

**v5.31 (D2d mainboard smoke closeout)**: D2d 没新增 profile/validator，而是复跑真实 public-safe mainboard smoke 证明 D2c 只移动了目标组：D2d 仍是 8180 components / BOM matched 7248 / validated 6679 / manual 1501 / PASS-WARN-ERROR 3868-2811-0；per-row `match_status` 是 `generic_passive=6573`、`matched=106`、`manual_needed=932`、`no_result=569`，其中唯一 matched profile group 是 106 个 `L2N7002KLT1G`，`LN2312LT1G` 26 个和 `PE537BA` 11 个仍只有 document coverage、没有 profile verdict。`recommend-next-family` 从 D2d index 生成 advisory：跳过已覆盖的 106 个 refdes 后，`unknown` 仍最大但需要新 validator triage；可走 existing-validator/profile 路线的队列是 `ic` 141 refdes / 31 groups、`diode` 81 / 10、`transistor` 37 / 2。D2d 还生成了 IC document candidate CSV，最大候选是 `74LVC1G125GW` 24 个、`MP87000-MGMJTH` 22 个、`MP5991GLU` 12 个、`PCA9617ADP` 10 个；这只是下一轮 public-evidence review queue，不是自动验证。

---

## Q5. 怎么防止编造元件编号和 datasheet 参数？

**v0.1**: 两层 defense in depth。Refdes Guard：报告里出现的 U1/R3/J5 必须命中 EDA registry，否则打"未验证" tag。Evidence Ledger：每条结论必须挂一个 source token（EDA / BOM / datasheet 页码 / checklist 规则 ID），无 token 不输出。架构借鉴 Wrench Board 的两层 sanitizer + tool-discipline。

**v0.2 evidence**: EDA registry 已跑通，`registry.has_refdes("U3") == True`，`registry.has_refdes("U999") == False`。Refdes Guard 下一步直接吃这个 registry。

**v0.5 (Slice 1 shipped)**: 两层 guard 都已实现并 wire 进 CLI：
- `src/hardwise/guards/refdes.py` — regex `\b[A-Z]{1,3}\d{1,4}\b` 扫每条 finding 的 `message` / `suggested_action` / `refdes` 字段，未通过 `registry.has_refdes()` 校验的全部 wrap 成 `⟨?XXX⟩`。单测覆盖："U23 should be near C1, but U999 is hallucinated and J7 too" → "U23 should be near C1, but ⟨?U999⟩ is hallucinated and ⟨?J7⟩ too"，wrapped count = 2。
- `src/hardwise/guards/evidence.py` — `Finding.evidence_tokens == []` 的项在写报告前直接 strip。
- 报告头部一行 sanitizer note 公开数字："N unverified refdes wrapped, M findings dropped (no evidence)"。Slice 1 demo 跑 pic_programmer 是 `0 / 0`（合理：R001 deterministic check，所有 finding 的 refdes 都来自实解析的 `BoardRegistry`），但单测覆盖了真假混合的反例。
- 总测试 28 条全过（含 4 条 refdes guard + 3 条 evidence ledger + 2 条 e2e）。

**final answer shape**: 防线不是一句 prompt，而是三层合同：(1) 工具层 unknown refdes 返回 `found=false` 和 `closest_matches`；(2) 输出层 sanitizer 把未注册 refdes 包成 `⟨?...⟩`；(3) 报告层 Evidence Ledger 丢掉没有 source token 的 finding。例子是 `U999`：registry 查不到，工具返回 not_found，模型不能把它解释成真实器件。

---

## Q6. 再做一个月会补什么？

**v0.1**: Cadence 适配器（企业环境接入）、pin 定义/接口表结构化解析、检视意见闭环状态、通用 checklist 规则包、Sleep Consolidator 从人工 gate 升级到带 evaluation set 的半自动晋升。PCB/EMC 检查仍放到更后面。

**final answer shape**: 我不会先加更多规则。再做一个月，优先补“可信度”和“可交付性”：

1. **人工标注 calibration set**：从公开项目里抽 20-30 条 finding，请硬件工程师标成 true issue / needs review / noise，用来量化 precision/recall。现在的 eval pack 是 regression smoke，不是专家准确率。
2. **Schematic net parser**：只在 `.kicad_sch` 上解析 wire、label、power symbol 和 symbol pin endpoint；这之后才允许做 R004/R005。已经实现的 `parse_pcb_nets` 明确只是 post-Layout diagnostic，不能喂 pre-Layout review。
3. **Decision trace polish**：把每条 finding 的工具调用、EDA token、datasheet hit 固化到报告旁注，面试官问“为什么出现这条 finding”时能直接追溯。
4. **Cadence/Allegro adapter**：如果岗位现场需要企业 EDA 证明，再在 Windows + Cadence Skill 环境补一个 adapter；MVP 阶段不在 Mac 上假装能完成企业闭环。

**明确不做**：PCB review、仿真、测试结果回灌、BOM/PLM/FMEA、GitHub Action PR bot。这些会把作品从“窄而真”推回“广而浅”。

---

## Bonus talking points (优先级低，但可加分)

### Tiered model routing
"三档路由不是绑定某个供应商型号，而是把 fast/normal/deep 三个运行槽留在 `.env`。当前 MiMo 只有一个主力模型时三档可以指向同一个 id；以后有更小/更强模型时只改配置，不改 agent 代码。成本和延迟是 Agent 落地的现实约束，不是研究玩具。"

### Adapter pattern at EDA boundary
"`adapters/base.py` 定义接口，`kicad.py` 是 v0.1 实现。Cadence/Allegro 是一个新文件，不是重构。Wrench Board 的 13 个 boardview parser 走的就是这个模式——adding a format = one new file。"

### Why Sleep Consolidator has a human gate
"Wrench Board 的 microsolder-evolve 用 oracle benchmark 自动 gate；我没有 oracle benchmark，所以用人工 gate。等真实使用数据攒够，可以升级到带 eval set 的半自动晋升。先求不污染 memory，再求自动化。"
