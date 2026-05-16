# Hardwise 中期回顾

> 写于 2026-05-14，项目进入第 7 天，Slice 4 刚 close。
>
> 这份文档要回答三件事：
> 1. **对着 Wrench Board 这面镜子**，我搬过来什么、扔掉什么、各自为什么
> 2. **当前 Hardwise 有什么真证据**（代码、命令、数字、commit），不是 narrative
> 3. **剩下的工作怎么排**，为什么不是另一种排序
>
> 这份文档不是 sprint plan（那是 `docs/PLAN.md` 的事），不是面试稿（那是 `docs/interview_qa.md` 的事），也不是 changelog。它是"做到中段，回头一次"——硬件项目立项做完详设之后开一次中期评审，标记证据、识别欠债、定下半段动作。

---

## 0. 当前站位

- **日历**：14 天 MVP，今天 Day 7。
- **slice 进度**：Slice 0/1/2/3/4 全 closed（详见 `docs/PLAN.md` 末尾"Discharged plan items"），Slice 5/6 未动。R004（I2C 地址冲突）按计划留在 Slice 4 之后，R005（dangling-nets）排在 Slice 5。
- **代码体量**：`src/hardwise/` 约 30 个 Python 文件（含 `__init__.py`），当前验证为 144 条 tests passed + 7 条 slow/deselected；`ruff check` 全过。
- **关键节点**：Slice 3 close 已经压过 PLAN.md 中定义的 **Gate B**（投递时机）；Slice 4 把 agent tool-use loop 在真 API 上跑通，prompt cache 有真数字（不是只 wire）。也就是说**"可演示物"和"投递条件"已具备，剩下的是 mechanism 层补强、规则补全和投递包装**。

一句话：硬件类比就是——原理图过了 ERC、关键 IP 都已 bring-up、最小系统板已点亮；剩下是补外围、过 EMC、出文档。

---

## 1. Wrench Board 对标

Wrench Board 是 Anthropic *Build with Opus 4.7* 黑客松 2026-04 第二名作品（`https://github.com/Junkz3/wrench-board`，license `NOASSERTION`，source-available proprietary）。它做的是**板级电子维修诊断**（microsoldering technician 用），不是 EDA 设计；但架构思想可以小尺度移植到 EDA 评审。

**移植口径**：架构思想 only，no code copied。public attribution 已在 `README.md` 和 `CLAUDE.md`。下面这张表是中期最重要的一次盘点。

### 1.1 搬过来的

| Wrench Board 原型 | Hardwise 移植形态 | 当前实现位置 | 缩水程度 |
|---|---|---|---|
| **两层 anti-hallucination** (`api/agent/sanitize.py` + tool 返回 `{found:false, closest_matches}`) | 完全 1:1 移植——`get_component` 工具层返回 `ComponentNotFound{refdes, closest_matches}` + sanitizer 兜底 | `src/hardwise/agent/tools.py:get_component` + `src/hardwise/guards/refdes.py` | 0% 缩水，这是项目的核心机制 |
| **fast/normal/deep 三档模型路由** | 同形——`HARDWISE_MODEL_FAST/NORMAL/DEEP` 三个 env 槽，agent 代码不硬编码模型 id | `src/hardwise/agent/router.py` | 上游只有 `mimo-v2.5` 一个 model 时，三槽指向同一个；槽位结构保留 |
| **cache-warmed prefix**（Writers 共享长 system prompt） | 同形——`build_system_blocks()` 把 system 包成 `cache_control: ephemeral` | `src/hardwise/agent/prompts.py` + `runner.py` token accounting | 0% 缩水；已在 MiMo proxy 上验过 `cache_read_input_tokens` 非零 |
| **"adding a format = one new file" 适配器模式** (13 个 boardview parser) | `adapters/base.py` 接口 + `kicad.py` v0.1 实现 | `src/hardwise/adapters/` | 只实现 KiCad，Cadence 是一个新文件而非重构 |
| **microsolder-evolve overnight loop**（自动 patch + oracle gate + git commit） | Sleep Consolidator——纯统计阈值，候选规则进 `memory/rules.md`，人工 gate | `src/hardwise/memory/consolidator.py` | 大幅缩水——没有 oracle benchmark，所以不做自动 promote |
| **direct mode + Managed Agents 两可** | 只做 direct mode（`messages.create` + tool loop） | `src/hardwise/agent/runner.py` | 砍掉一半；Managed 留作 roadmap |
| **vertical slice 优于 horizontal**（每个 slice 端到端） | 同样思想，落在 `docs/PLAN.md` DR-006 | PLAN.md | 0% 缩水；这是过程层的最大收益 |

### 1.2 故意没搬

| Wrench Board 特性 | 拒掉原因 | 立项时记录在 |
|---|---|---|
| 4 personas (Scout / Registry / Writers / Auditor) 多智能体 | 2 周 + 一个人——多智能体编排会吃掉一半时间 | `CLAUDE.md` "Out of scope" |
| Vision-native PDF schematic 摄取（Opus 4.7 vision 编译 ElectricalGraph） | PDF 视觉解析是工程黑洞；datasheet 走 pdfplumber + 向量库够用 | `CLAUDE.md` "Out of scope" |
| Real-time boardview canvas + 12 个 `bv_*` 工具 | 前端工程量爆炸，与 demo 价值不匹配 | `CLAUDE.md` "Out of scope" |
| WebSocket 流式协议 | stdout 够 demo；流式是包装层不是机制层 | `CLAUDE.md` "Out of scope" |
| 13 种 boardview 格式 parser | KiCad 一种已经能讲清楚 adapter pattern | DR-002 |
| Anthropic Managed Agents 运行时 | direct mode 简单且无 bootstrap，MVP 不需要跨会话记忆 | DR-001 |
| Auto-evolve overnight loop + oracle benchmark + 自动 git commit | 没有 oracle benchmark，自动 promote 会污染 memory | `CLAUDE.md` "Out of scope" |
| Deterministic simulator + hypothesize 引擎（启动序列推进） | 领域不对——他们模拟 boot phase，我做 schematic review 不模拟 | `CLAUDE.md` "Out of scope" |
| Per-pack reliability score | 量化基础设施开销大、demo 加分小 | `CLAUDE.md` "Out of scope" |

### 1.3 这张对比表本身的价值

中期回顾不是炫"我搬了多少"，是确认**两条边界都守住了**：
- **下界**：5 个机制全部对应到 Wrench Board 同源的"架构思想"，每条都能在面试现场说出"它在 Wrench Board 长成什么样、我缩到什么形态、为什么这样缩"。
- **上界**：拒掉的 9 类都不是"我做不到"，是"做了也讲不深"——一个 2 周 MVP 不可能既窄又广。Wrench Board 那 9 条特性平均每条都要 1-2 周；移植 1 条就够本，移植 3 条就超额。

硬件类比：评估外包供应商参考设计时，"哪些可以照搬、哪些必须自己改、哪些不要碰"是三张分开的清单。三张都不能空。

---

## 2. Hardwise 当前证据

五个机制每个机制一段，**只列可复现的事实**——命令、文件:行、数字、commit。"我设计了五个机制"是 narrative；下面这些是证据。

### 2.1 机制 1 — Refdes Guard（反幻觉，两层防御）

**Layer 1 — 工具层 anti-fabrication**（事前）
- `src/hardwise/agent/tools.py:get_component(refdes)` — 命中返回 `ComponentFound{component}`，未命中返回 `ComponentNotFound{refdes, closest_matches}`。`closest_matches` 由 `difflib.get_close_matches` 在 `BoardRegistry.refdes_set` 上算，工具**永远不编**。
- 真验证（commit Slice 4 close，pic_programmer，model=mimo-v2.5）：

  ```
  ask "U999 是什么器件？"
  → get_component(refdes=U999) → ComponentNotFound{closest_matches=[]}
  → model 回答："未找到 U999，请确认位号"——不编
  ```

  如果没有这个 unknown 分支，model 大概率会从训练数据里编 "U999 是某某"。

**Layer 2 — 输出层 sanitizer**（事后）
- `src/hardwise/guards/refdes.py` — regex `\b[A-Z]{1,3}\d{1,4}\b` 扫输出文本，未通过 `registry.has_refdes()` 校验的全部 wrap 成 `⟨?XXX⟩`。
- **两条输出路径都接入**：(a) `hardwise review` 路径走 `sanitize_finding` 扫每条 finding 的 `message / suggested_action / refdes`，report 头部公开 `N unverified refdes wrapped`；(b) Slice 4 follow-up 已把 `cli.py:ask` 的最终 `result.text` 也接入 `sanitize_text`，并在 token 行打印 `unverified refdes wrapped: N`——agent loop 答复也走兜底。
- 单测覆盖 4 条（含真假混合反例）。

**对照 Wrench Board**：思路 1:1，文件位置 1:1（他们 `api/agent/sanitize.py`，我 `guards/refdes.py`）。

### 2.2 机制 2 — Evidence Ledger（provenance / 每条结论必带 source token）

- `src/hardwise/guards/evidence.py` — `Finding.evidence_tokens == []` 的项写报告前直接 strip；report 头部公开 dropped 计数。
- Finding 模型（`src/hardwise/checklist/finding.py`）的 `evidence_tokens: list[str]` 是所有规则、guard、report 的共享契约（DR-008），形态如 `["sch:pic_programmer.kicad_sch#U23", "datasheet:l78.pdf#p4"]`。
- pic_programmer 上 R001/R002/R003 跑出来的 84 条 finding 每条都带至少一个 token，sanitizer wrapped = 0，dropped = 0（合理：所有 refdes 都从实解析的 `BoardRegistry` 来）。
- **Slice 3 close 后双库 token 形态**：结构化 token (`sch:<file>#<refdes>`) 来自 `BoardRegistry.refdes_set`，文本 token (`datasheet:<pdf>#p<N>`) 来自 `ingest/pdf.py:ChunkRecord.evidence_token`。两类 token 共用一个 `refdes` 作 join key——这是 PLAN.md 双库设计的核心约束（"两个 store，一个 join key"）。

**还差一步**：跨双库的真 R003 finding（同一条意见同时挂 `sch:` 和 `datasheet:` 两个 token）还没自动生成，目前是分开演示。下半程 step 3 把 `search_datasheet` 拉进 R003 检查路径就闭环。

### 2.3 机制 3 — Sleep Consolidator（memory consolidation，人工 gate）

- `src/hardwise/memory/consolidator.py` — 纯统计聚合：按 `(rule_id, severity)` 分桶，桶 count ≥ 3 emit 一条 `CandidateRule`，追加到 `memory/rules.md` 一个 `STATUS: candidate` 块。无 LLM、无 embedding、固定 seed 可复现。
- 实测：`hardwise review pic_programmer --rules R001,R002,R003` 触发 2 条候选（R002 medium × 6 + R003 medium × 77，都跨过阈值 3）。
- **人工 gate**：candidates 永不自动晋升。要晋升必须手工编辑 `memory/rules.md`，迁到 `data/checklists/sch_review.yaml` 标 `status: active`。

**对照 Wrench Board**：他们的 microsolder-evolve 用 oracle benchmark 自动 gate + 自动 git commit；我没有 oracle benchmark，所以人工 gate。这是 mechanism #3 最大的"故意缩水"。

### 2.4 机制 4 — Tiered Model Routing（cost-aware orchestration）

- `src/hardwise/agent/router.py:ModelRouter(env).select(tier)` — 读 `HARDWISE_MODEL_FAST/NORMAL/DEEP`；缺槽 fallback 到 NORMAL，再 fallback 到硬编码 `mimo-v2.5`。**agent 代码从不出现具体 model 名**。
- 7 条单测覆盖三槽、fallback 链、env 缺失路径。
- CLI 兑现：`hardwise verify-api --tier {fast,normal,deep}` 和 `hardwise ask --tier ...` 都走 router。
- **现状诚实声明**：上游 MiMo 当前只有 `mimo-v2.5` 一个 model，所以三槽都指向同一个——**槽位结构对、但区分度为 0**。一旦 MiMo 出 `mimo-v2.5-pro` 或类似 fast 变体，零代码改动只改 `.env`。

### 2.5 机制 5 — Prompt Caching（cache-warmed long context）

- 实现：`agent/prompts.py:build_system_blocks()` 把 system 包成 `[{"type":"text", "text":..., "cache_control":{"type":"ephemeral"}}]`；`agent/runner.py` 每轮累加 `response.usage.{cache_creation_input_tokens, cache_read_input_tokens}`。
- **真数字**（pic_programmer，tier=normal，三次 ask 命令，commit Slice 4 close）：

  | 提问 | iter | in/out | cache create/read |
  |---|---|---|---|
  | `U3 是什么器件？` | 2 | 1635/240 | 0 / **1472** |
  | `U999 是什么器件？` | 2 | 129/171 | 0 / **2944** |
  | `U4 这颗器件有几个 NC 脚？` | 2 | 196/154 | 0 / **2944** |

- `cache_read_input_tokens ≠ 0` 证明 mechanism 不是 wiring-only，是 server-side 真触发了。**这一条是 Slice 4 close 的核心证据，没有它整个 #5 都站不住**（见 `docs/learning_log.md` 2026-05-13 entry）。

### 2.6 五机制之外的两块意外资产

中期回顾里值得专门点名的两块，不在原 5 机制清单里，但已沉淀成可叙述的工程价值：

1. **KiCad pin 坐标解析**（`adapters/kicad_pins.py`）。Slice 3 写 R003 时撞到的 EDA 工具方言——`pin.at` 是引脚**尖端**（连接点），不是引脚根部。坐标变换 `symbol_at + rotate(pin.at, rotation_deg)` 在 pic_programmer 上 77 个 NC pin 全部精确匹配（与 `grep -c no_connect` 计数完全吻合）。`docs/learning_log.md` 2026-05-12 entry 是这块的 narrative；以后接 Cadence/Altium 同样套路。

2. **PostgreSQL 物理验证**（`docs/learning_log.md` 2026-05-13 entry）。Slice 3 close 后追加的 1 小时工作：`HARDWISE_DB_URL` env override + `_resolve_url()` dispatch + `psycopg2-binary` optional dep group。结果——`hardwise review` 在 SQLite 和 PostgreSQL 上都能跑出 121 components + 77 NC pins，数字精确一致。简历叙事从"可平滑切换"升级到"双后端实跑"——这是 DJI JD 第 4 条明确点名 PostgreSQL/MySQL 的直接交底。

---

## 3. 弱点（诚实清单）

这一节的标准：**对面试官/对未来的我有用**。不写"如果再有一周就好了"这种废话，写"这个东西现在不在位、影响是什么、按什么顺序补"。

### 3.1 规则覆盖未达 5/5

- **现状**：R001/R002/R003 active，R004/R005 还在 yaml 里 `status: planned`。
- **影响**：CLI demo 只覆盖"新建器件 / 电容耐压 / NC pin"三类，"I2C 地址冲突 / 单端 + 空网络"两类还讲不出。
- **不算硬伤**：5 个 mechanism 早在 Slice 4 就全部 ship 了；规则只是 mechanism 的应用面。投递阶段（Gate B）的 demo 不强求 5/5。
- **拆解顺序**：**不为凑 4/5 抢做 heuristic R004**——R004 在没有 net parser 的前提下，只能按 `value` 字段字符串匹配 I2C 地址，会把"同地址但不同 bus"的合法器件误报为冲突，质感不如先把 R003 做成"EDA + datasheet 双证据链"+ 沉淀 DecisionTrace。net parser 上线后 R004/R005/R006/R007 一组规则连环可上。下文 §4 详。

### 3.2 R003 跨双库闭环的诚实边界

- **现状**：R003 datasheet closure 已上线（DR-009）：每条 NC pin finding 都有结构化 `evidence_chain` + 机器判断 `decision`，并且 `decision` 与人工流程 `status` 分离。检查路径会按 refdes → component.value 推 part_ref，再查向量库 datasheet chunk；命中 pin 且命中 NC/not connected 关键词则 `likely_ok`，命中 pin 但无 NC 关键词则 `likely_issue`，无相关命中则 `reviewer_to_confirm`。
- **当前样例结果**：`pic_programmer` 的 Chroma 里只有 L78/U3 datasheet，而真实 77 个 NC pin 在 U4/J1 等没有 ingest datasheet 的器件上，所以 77 条 finding 全部是 `decision=reviewer_to_confirm`，evidence_chain 只含 EDA step。这是正确的诚实输出：没有可用 datasheet 证据时不瞎判。
- **剩余边界**：还没有一个公开样例自然产出“同一条真实 finding 同时挂 `sch:` + `datasheet:` 两 token”的漂亮展示；单测已经覆盖 likely_ok / likely_issue / reviewer_to_confirm 三条路径，后续更适合补的是 DecisionTrace，把这条决策链沉淀成可审计 artifact。

### 3.3 `cache_creation_input_tokens` 在 MiMo 上不可观测

- **旧现状**：三次 ask 命令的 cache_create 列都是 0；cache_read 都非 0。
- **2026-05-16 复验**：用唯一 system prompt 做 cold-start probe，连续两次请求 MiMo proxy。raw usage 为：run 1 `input_tokens=5445, cache_creation_input_tokens=null, cache_read_input_tokens=null`；run 2 `input_tokens=5, cache_creation_input_tokens=null, cache_read_input_tokens=5440`。
- **解释**：MiMo 的 read path 确认生效，但 creation accounting 没暴露。第一轮 cold prompt 被计入普通 input tokens，不会像官方 Anthropic usage 那样给出非零 `cache_creation_input_tokens`。
- **怎么补**：需要换一个会回传 creation 字段的 endpoint（官方 Anthropic API 或另一个 Anthropic-format provider）复验。当前 `.env` 的 MiMo proxy key 直连 `https://api.anthropic.com` 会返回 `401 invalid x-api-key`，所以在这台环境上无法补出"creation 非零"证据。面试说法应收敛为：`cache_read` 命中已实测，`cache_creation` 是 provider observability gap。

### 3.4 三档路由当前区分度为 0

- **现状**：上游 `mimo-v2.5` 只有一个 model，三槽都指向同一个。
- **影响**：mechanism #4 槽位是对的，但**"用了便宜模型省钱"这种现场效果**没有数字。
- **怎么补**：要么等 MiMo 出 fast 变体（不可控），要么换上游做一次对照演示——把 `HARDWISE_MODEL_FAST` 换成另一个 Anthropic-format endpoint（比如 Claude Haiku via 官方 API），用 `verify-api --tier fast` 各跑一次比 tokens/latency。这是 2 小时的事，但不在 Gate B 必须项。

### 3.5 Sleep Consolidator 仍是纯阈值统计

- **现状**：`consolidator.py` 不用 LLM、不用 embedding，纯 `(rule_id, severity)` 桶 + count ≥ 3。
- **影响**："memory consolidation / dream mode"作为面试 talking point 看起来单薄。
- **辩护**：Sleep Consolidator 的真正卖点不是"统计 vs LLM"，是**人工 gate**（mem pollution 防护）。在没有 oracle benchmark 的前提下，统计阈值是**正确的最小实现**——多加 LLM 反而会让"为什么不自动 promote"这条规矩变模糊。
- **怎么升级**：等真有评审使用数据（n ≥ 50 条 finding），可以加一层 LLM 模式提取（"为什么这些 finding 看起来像同一类"），但仍然落到候选池，仍然人工 gate。**不是 MVP 范围**。

### 3.6 无 oracle benchmark，无法报准确率

- **现状**：没有真值集（哪些 finding 是真问题 / 哪些是误报），所以"准确率 N%"这种话**没法说**。
- **辩护**：MVP 阶段没有这个口子是合理的——硬件评审本身就是"人审"的领域，oracle 集要靠 ≥10 个真实项目的人工标注，2 周做不出。
- **替代证据**：(a) 用 pic_programmer 这个**已完成**项目证明"不在假阳性这一头"（R001 跑出 0 finding 是诚实，不是 bug——`learning_log.md` 2026-05-10 entry）；(b) 单测对每条规则的正反例都有 fixture 覆盖。**两条够 Gate B/C 用**。

### 3.7 唯一 EDA adapter 是 KiCad

- **现状**：`adapters/base.py` 接口在，`adapters/kicad.py` 是 v0.1 实现；Cadence/Allegro 没动。
- **辩护**：DR-002 明确——Mac 上跑不了 Cadence（license + OS），公开 demo 项目都是 KiCad。adapter pattern 已经在结构上证明（接口分离 + 单实现 + 一个未来文件），**"多 1 个 adapter"对面试加分小、对 Gate B 不需要**。
- **怎么补**：真有 DJI 面试机会要求 Cadence 现场跑，工作机（Windows + Cadence + Skill 绑定）上一两天能加。**不在 Mac 上做这件事**——会被环境吃掉时间。

### 3.8 演示视频 + 简历最终版 + Q6 v1.0 还在路上

- **现状**：`docs/submission/` 已有 resume v3 PDF + 4 张 preview PNG（说明用户在迭代视觉），但 3-min screencast、interview Q6 v1.0、README quickstart 终稿都还没钉死。
- **影响**：这些是 Gate B 投递清单的最后几格，不补完会在投递前夕手忙脚乱。
- **不是技术债**：是包装债。screencast 与 §4 的 7 步并行——step 3（R003 双证据链）落地后可录初版，最终版等 step 6/7（net-aware R004 + R005）上线再定稿。简历 + README + Q6 v1.0 与 step 1 submission closeout 同步完成。

---

## 4. 下一步顺序及理由

剩下半程的工作量约 25-35 小时（按 PLAN.md 的 50-70h 总预算扣掉前半的真实消耗）。按"投递时机 vs 工程边际收益"两条轴排：

### 排序

1. **submission closeout**（resume final + README quickstart + GitHub repo hygiene + interview Q6 v1.0）— 6-8h
2. **cache creation 端点对照**（换官方 Anthropic 或另一个会回传 `cache_creation_input_tokens` 的 Anthropic-format endpoint，补 creation 非零证据）— 0.5-1h
3. **DecisionTrace / finding evidence chain**（per-finding 记录工具调用链 + datasheet hit + 命中片段；把 R003 已有的 `evidence_chain` 和 `Runner` 累计的 `ToolCallTrace[]` 沉淀成可审计 artifact 落到 report 旁注）— 4-6h
4. **Schematic net parser**（追 wire + label + 跨页 hierarchical label，产 `list[NetRecord(name, fanout, refdes_pin_list)]`，写进 SQLite 的 `schematic_nets` 表；不能复用 `.kicad_pcb` 里的 `pcb_nets`）— 6-8h
5. **R004 net-aware I2C 地址冲突**（依赖 step 4；同地址不同 bus 不算冲突）— 3-4h
6. **R005 dangling-nets**（依赖 step 4；R006/R007 net naming 跟着顺势可上，见 `docs/rolling_log.md`）— 3-4h

screencast 是包装层，与上面 6 步并行——DecisionTrace 之后即可录初版，net-aware 规则上线后定稿。

### 为什么是这个顺序

**为什么 submission closeout 排第 1**
- Gate B 条件已满足（PLAN.md 明确）；继续往后做的边际收益**不再投入投递**——投出去越早，反馈越早回来。
- "等更完美再投"是错误本能；硬件类比是"等所有 ECN 全清了才送样"——永远等不到。Slice 0 立项时就把 Gate B 写在 PLAN.md，现在就是兑现 Gate B 的时候。
- 6-8 小时是上限——resume v3 PDF 已经有了，主要是 README 内嵌 demo gif、GitHub topic/description、Q6 v1.0 这三块定稿。

**为什么 cache creation 端点对照排第 2**
- 2026-05-16 已做 cold-start probe，MiMo 给出了强 read-hit 证据（第二轮 `input_tokens=5, cache_read_input_tokens=5440`），但 creation 字段仍为 `null`。这不是 Hardwise wiring 问题，而是 provider usage accounting 不完整。
- 补它的价值仍然高：只要换到会暴露 creation 字段的 endpoint，就能把 mechanism #5 的故事从"read hit 可观测"补成"create + read 两段都可观测"。但它需要一个合适 key/endpoint，不再是单纯本 repo 内 0.5 小时能解决的问题。

**为什么 DecisionTrace 排在 net parser 和规则补全之前（step 3）**
- **mechanism 层 > 规则数量**。规则数量是可加可减的应用面，mechanism 层是项目叙事骨架——先骨架后填肉。
- R003 datasheet closure 已经把 `decision` / `status` / `evidence_chain` 的契约跑通；下一刀不是再堆一条规则，而是把“为什么这条 finding 是 reviewer_to_confirm / likely_ok / likely_issue”的过程沉淀成可审计 artifact。
- DecisionTrace 是 mechanism #2 的纵深扩展：Slice 4 `Runner` 已经累积 `ToolCallTrace[]`，但只用在 stdout 显示；把它沉淀成 per-finding 旁注（"这个 finding 因为调 `get_component(U4) → found` + `search_datasheet("pin 5 NC") → no relevant hit`"），整个 agent 决策路径变成可审计 artifact——面试官问"为什么这个 finding 会出现"时有现成答案，不靠口头复述。

**为什么不抢做 heuristic R004**
- 在没有 net parser 的前提下，R004 只能按 `value` 字段字符串匹配 I2C 地址（`0x..`）+ 元件类型过滤——能跑，但**同地址不同 bus 不冲突**这件事它判不出来，会输出可见的假阳性。
- 把这种 heuristic 上线相当于把 Q4 题目从"如何防止 agent 假阳性"变成"我已经在产出假阳性"——叙事质感倒退。
- 所以 step 4 先写 schematic net parser（KiCad 多页 + hierarchical label 是已知工程量但不复杂；`.kicad_pcb` 的 `pcb_nets` 只能作 post-Layout diagnostic），parser 一上线，step 5 的 net-aware R004 + step 6 的 R005 + `rolling_log.md` 已经准备好的 R006/R007 是连环动作，单刀基础设施养出来 4 条规则。

**screencast 为什么并行而非单独占一格**
- 视频要录"接近终态"的产物——DecisionTrace 之后已经有"R003 决策链 + 可审计旁注"这套**机制层完整**的画面，初版可以先录定，留个内部演练用的版本。
- 终态版（包含 R004 net-aware + R005）等 step 6 之后定稿，3 分钟脚本：(a) `inspect-kicad` 看 registry → (b) `review --rules R001..R005` 出报告，重点展示 R003 decision/evidence_chain + DecisionTrace 旁注 → (c) `ask "..."` 展示 prompt cache read hit；若换到会暴露 creation accounting 的 endpoint，再展示 cache_create + cache_read 两段闭环 → (d) 候选规则 `memory/rules.md` 一眼带过。每段 30-45 秒。

### 不做什么（同样重要）

- **不做 PCB review / 仿真 / 测试结果回灌 / BOM 管理 / FMEA / PLM**——CLAUDE.md hard rule #5 / DR-007 锁死的"原理图评审节点"边界。任何往这些方向的扩张都是范围蠕变，给 DJI 的窄而真叙事会被打散。
- **不做 Cadence adapter**——DR-002 锁死；要做就在工作机上做，不在 Mac 上花时间。
- **不做 oracle benchmark**——准确率叙事不是 2 周能撑起来的，单测 + 诚实输出 + 公开样例三条已经把"不胡说"的故事讲完。
- **不做多 agent 编排 / vision PDF / WebSocket / Managed Agents**——CLAUDE.md "Out of scope" 列表全部继续作废。

---

## 5. 这份文档的用法

写完归档到 `docs/midpoint_review.md` 后，三种使用场景：

1. **半程自检**：每周末扫一次"§3 弱点"清单，确认状态没有恶化；扫一次"§4 顺序"，确认排序假设没有被现实推翻（比如 net parser 实际工程量超过预算 → R004/R005 一起降级为条件性，把腾出来的时间倒给 DecisionTrace 的深化）。
2. **面试现场**：被问"做到一半你最大的判断是什么"时，§1.3 "对比表本身的价值"那段 + §3 任意两条弱点 + §4 排序里的一个 trade-off 例子，三段拼出来就是 2-3 分钟有质量的口头答案。
3. **复盘后续项目**：下一个 2 周 MVP（不管是 Hardwise 续集还是别的）开局时翻这份文档——"上次中期我学到 X、忽略了 Y、对 Y 的判断是否仍成立"是最便宜的 lessons learned 复盘入口。

不写 changelog 字段、不写 owner 字段、不写日期更新栏——这份是**单次写定的回顾**，不是滚动文档；下次回顾另起一份 `docs/late_review.md` 或 `docs/closeout_review.md`。

---

## 附录 A — 中期一句话故事（用于 README / 简历 / 面试开场）

> Hardwise 是 2 周 MVP 的硬件 R&D 评审 Agent，架构思想来自 Wrench Board（Anthropic 黑客松 2026-04 第 2 名）但代码零拷贝。做到中段（Slice 4 close）时，5 个机制全部 ship 并有真证据：reference-designator 反幻觉两层防御端到端跑通（U999 不再被编造）、双库存储以 refdes 为 join key（SQLite + PostgreSQL 实跑 + Chroma 向量库 ingest 真 datasheet）、R003 按 DR-009 输出 `evidence_chain` + `decision` 并在缺 datasheet 时诚实给出 `reviewer_to_confirm`、tiered routing 槽位结构兑现、prompt cache 在 MiMo proxy 上 `cache_read_input_tokens` 非零、memory consolidation 候选规则池 + 人工 gate 已写入文件。剩下半程先 mechanism 层补强（DecisionTrace），再写真正的 schematic net parser 解锁 R004/R005；不抢做 `.kicad_pcb` / value-string heuristic R004，避免把 post-Layout diagnostic 或假阳性包装成 pre-Layout evidence。

(123 字。)
