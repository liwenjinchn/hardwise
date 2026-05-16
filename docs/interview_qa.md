# Interview Q&A — Hardwise

> Start with `docs/interview_narrative.md` for the concise interview story.
> Use `docs/interview_narrative.html` when you want the paper-style reading view.
> This file is the longer evidence bank behind that story.

## 主叙事

Hardwise 不是在证明“大模型可以独立评审完整硬件设计”。它证明的是一个更窄但更可信的闭环：在 pre-layout 原理图评审节点，Agent 只能通过工具查询 EDA registry 和 evidence store；所有用户可见 refdes 必须 registry-verified，所有 finding 必须有 evidence token。模型负责解释和组织证据，不能自由发明元件、pin 或 datasheet 结论。

面试时优先讲这条主线：`review` 一行命令跑公开 KiCad 项目，输出带证据 token 的 report；`ask` 通过 structured tools 回答问题；`get_component("U999")` 这类 unknown path 会返回 `found=false`，而不是让模型编造。Eval Pack 只作为 regression / guardrail smoke，不包装成专家准确率 benchmark。

---

## Q1. 这个工具帮硬件工程师省了哪一步？

**v0.1**: 省原理图检视时在 SCH、BOM、datasheet、pin 定义和需求之间反复查证、对位号、整理意见的搬运链。AI 先生成带证据的检视意见，工程师集中判断是否接受和修改。

**v0.2 process calibration**: 真实流程里，原理图检视发生在画 PCB 之前；评审输入以 SCH 为主，评审人会同时查 BOM、datasheet、pin 定义和需求。输出是检视意见，开会 review 是否接受并更改，最终形成评审记录。

**v0.5 (Slice 1 evidence)**: 真实评审输入瘦到 2 类——sch + 通用 checklist（其它"软硬件接口/Connector_pin_define/FMEA/仿真建议"都是评审之后才出的下游产物）。Slice 1 跑通的最小闭环：CLI `hardwise review pic_programmer --rules R001` → 解析 121 个 component → 跑 R001 (新建器件候选识别) → 经 Refdes Guard + Evidence Ledger → 输出对齐《SCH_review_feedback_list 汇总表》的 markdown 报告。在已完成的公开样例 `pic_programmer` 上结果是"0 candidate findings, 121 components reviewed"——这是**诚实输出**，因为 KiCad 公开 demo 的所有真实器件都已 layout 完成、footprint 字段都填好。

**v3.0 (Slice 3 evidence)**: R003 NC pin handling 接入后，注意力分配清单从单字段变成跨字段+跨 unit 的 pin 级别。第一版 `hardwise review ... --rules R001,R002,R003` 在 pic_programmer 上产 84 条 finding（7 R002 + 77 R003），R003 覆盖 6 个主表 NC pin（J1 DB9 上 4 个 + LT1373 上 2 个）+ 71 个 PIC 插座 NC pin。后续按 review 视角收敛噪音：连接器/插座类 NC pin 聚合成低风险摘要，IC 类 NC pin 继续逐 pin 保留；R002 对已声明 `/V` 的电容不再生成提醒行。当前同一 demo 输出 28 条有效 finding，且 sanitizer 为 0 个未验证 refdes 包裹。所有 NC pin 用"坐标匹配"从 `no_connect` 标记反查到具体 refdes/pin_number，不依赖 model 输出 pin 信息，从结构上杜绝 pin 级幻觉。

**v3.2 eval harness evidence**: 为了避免只靠单 demo 自证，新增 `hardwise eval`：从 public KiCad corpus manifest 跑 R001/R002/R003，写 `eval-summary.json/html`；再用 `--baseline ... --accept-baseline` 接受一个已检查结果，后续运行自动生成 `eval-comparison.json`。MVP gate 只挡明显工程回归：project parse failure、新增 unverified refdes wrapping、新增 evidence dropped；finding 数量变化先作为观察项，因为有用规则也可能合法增加/减少 finding。当前完整 public smoke 是 5 个 repo / 16 个 KiCad project / 1707 components，全部解析通过；输出 437 条 finding，其中 decision split 是 298 likely_issue / 99 reviewer_to_confirm / 40 likely_ok / 0 undecided，guard/evidence 两个硬指标都是 0（`unverified_refdes_wrapped=0`, `findings_dropped_no_evidence=0`）。这不是专家 gold-label 正确率，而是“真实公开工程上可重复跑、可定位注意力分配回归”的工程可用性证据。

**v3.3 synthetic safety floor**: Eval Pack v0 现在是两层：public corpus 负责真实项目上的 parser/guardrail/noise regression，`tests/harness/test_must_catch.py` 负责 synthetic must-catch safety floor。后者手工构造 5 个已知关键场景（新器件无 footprint、电容缺 `/V`、电容已有 `/V` 不应报、IC NC 无 datasheet、connector 批量 NC），用 pytest 锁住“这些已知重大边界不能漏/不能回流噪音”。人工标注的 20-30 条 calibration set 是下一步，用来量化 decision precision/recall。

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

---

## Q3. 哪些进向量库，哪些进结构化库？为什么这样分？

**v0.1**: datasheet 长文本无 schema、需语义检索 → 向量库；元件/网络/BOM/DRC 结果是强 schema 关系数据、要 join 和位号校验 → 结构化库。混存会让位号查询和参数引用都失去可信度。

**v1.0 (Slice 3 shipped)**: 双库都已 live，refdes 是 join key。

- **关系库（SQLite + SQLAlchemy）**：`src/hardwise/store/relational.py`，两张表 `components`（refdes 唯一索引，value/footprint/datasheet/source_file/source_kind）+ `nc_pins`（refdes/pin_number/pin_name/pin_electrical_type）。在 `pic_programmer` 上跑 `uv run hardwise review ... --rules R001,R002,R003` 后写入 121 个 components + 77 个 NC pins。
- **向量库（Chroma local persistent + ONNX MiniLM）**：`src/hardwise/store/vector.py`，每个 chunk 的 metadata 至少 `{part_ref, source_pdf, page, chunk_index}`。`hardwise ingest-datasheet data/datasheets/l78.pdf --part-ref U3` 切页 → chunks → upsert，`hardwise query-datasheet "absolute maximum input voltage"` 返回 top-k 带 `[l78.pdf p7 part=U3]` 的 provenance 行。
- **Join key = refdes**：U3 在关系库 `components` 表里有 `value=7805, datasheet=www.st.com/.../l78.pdf` 一行，在向量库里有 `part_ref=U3` 的 N 个 chunks。一条评审意见想"对位号 U3 引用 datasheet 第 7 页"，就要同时给 `sch:pic_programmer.kicad_sch#U3` 和 `datasheet:l78.pdf#p7` 两个 evidence token——两条都验得过才会被 Evidence Ledger 放行。混存会破坏这种 token 三段式定位。

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
