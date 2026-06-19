# Hardwise

[English](README.md) | [中文](README.zh-CN.md)

**[▶ 打开在线工作台 demo](https://liwenjinchn.github.io/hardwise/hardware-demo.html)** ——
评审工作台的离线快照，浏览器直接打开：评审队列、带证据 token 的确定性
finding、可审计的 Copilot 问答轨迹。

[![Hardwise 评审工作台——器件队列、验证明细与 Copilot 面板](docs/assets/hardwise-workbench-snapshot.png)](https://liwenjinchn.github.io/hardwise/hardware-demo.html)

> 面向公开硬件项目的 pre-Layout 原理图评审工作台：review queue、证据化
> finding、registry-verified 位号和确定性验证。

**为什么重要：** Layout 前原理图评审是重证据、重搬运的人工工作；Hardwise
把导出的 netlist+BOM 文件变成有边界的评审队列，而不是无依据聊天机器人。

**我做了什么：** 一个本地 AI 辅助评审工作台，包含确定性硬件 validator、
registry-verified 位号防护、规格书/文档覆盖状态，以及带工具 trace 的
Copilot 解释路径。

**可验证证据：** 公开 fixture、可点击的离线 SPA demo、GitHub Actions CI，
以及覆盖位号防护、证据过滤、workbench API、CLI 流程和报告出口的 687 条
回归测试。

Layout 前的原理图评审至今仍靠人肉：对位号、翻规格书、给每条结论找证据。
Hardwise 只锚定 **pre-layout 原理图评审** 这一个节点。它不声称大模型已经
能独立判断完整硬件设计，而是证明一个更窄、更有用的工程闭环：导入公开
原理图工程或 schematic netlist+BOM，建立可信 component registry，运行
确定性 review 检查，把硬 finding 和 manual/profile gap 分开，给每条结论挂
evidence token，再让 Agent 只解释工具查到的事实。范围刻意收窄：两周完成
的 MVP，只覆盖 pre-layout 原理图评审节点。

架构灵感来自 [Wrench Board](https://github.com/Junkz3/wrench-board)（Anthropic *Build with Opus 4.7* hackathon，2026 年 4 月第二名）。只借鉴设计思路，不复制代码。

本项目使用 AI 辅助完成；设计决策和最终代码由作者审阅并负责。

---

## 简历 bullet

Built **Hardwise**, a local AI-assisted schematic review workbench that imports
netlist+BOM files, runs deterministic hardware validators, prevents
hallucinated reference designators, and surfaces evidence-backed review queues
with tool-traced Copilot explanations and 687-test regression coverage.

中文表述：构建 Hardwise，一个本地 AI 辅助原理图评审工作台；可导入
netlist+BOM，运行确定性硬件验证器，防止模型编造位号，并以带工具轨迹的
Copilot 解释呈现证据化评审队列，配套 687 条回归测试。

---

## Demo

**▶ 60 秒产品短片** —— 问题、反幻觉内核（Refdes Guard + Evidence Ledger）、真实工作台与信任分级。点击封面播放：

[![Hardwise —— 60 秒产品短片](docs/assets/hardwise-promo-poster.png)](https://github.com/liwenjinchn/hardwise/raw/main/docs/assets/hardwise-promo.mp4)

两个入口，都不用安装：

- **Demo 视频（约 90 秒）：** [hardwise-demo.mp4](https://github.com/liwenjinchn/hardwise/releases/download/demo-video/hardwise-demo.mp4)
- **在线工作台：** [hardware-demo.html](https://liwenjinchn.github.io/hardwise/hardware-demo.html) —— 离线 SPA 快照，浏览器里直接点

GitHub 会把 HTML 文件显示成源码。请打开渲染后的 GitHub Pages 阅读页：

- **阅读索引：** [https://liwenjinchn.github.io/hardwise/](https://liwenjinchn.github.io/hardwise/)
- **产品介绍页：** [https://liwenjinchn.github.io/hardwise/product-intro.html](https://liwenjinchn.github.io/hardwise/product-intro.html)
- **离线 SPA 工作台快照：** [https://liwenjinchn.github.io/hardwise/hardware-demo.html](https://liwenjinchn.github.io/hardwise/hardware-demo.html)
- **MVP 定义：** [https://liwenjinchn.github.io/hardwise/mvp_definition.html](https://liwenjinchn.github.io/hardwise/mvp_definition.html)
- **技术机制快照：** [https://liwenjinchn.github.io/hardwise/demo.html](https://liwenjinchn.github.io/hardwise/demo.html)
- **录屏脚本：** [https://liwenjinchn.github.io/hardwise/demo_recording_script.html](https://liwenjinchn.github.io/hardwise/demo_recording_script.html)
- **文档清单：** [https://liwenjinchn.github.io/hardwise/docs_inventory.html](https://liwenjinchn.github.io/hardwise/docs_inventory.html)

本地 quickstart：

```bash
uv sync
./scripts/start_hardwise_workbench.command
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003,DS001 --report-style component --output /tmp/hardwise-review.md
uv run hardwise design-validator-ui tests/fixtures/allegro/mixed_controller_power_stage.net tests/fixtures/allegro/mixed_controller_power_stage_bom.csv --ai-snapshot --document-index data/document_indexes/mixed_controller_power_stage_docs.csv --output /tmp/hardwise-copilot-workbench.html
```

Windows 可双击 `scripts/start_hardwise_workbench.cmd`。两个启动器都会加载内置
demo 项目、打开 `http://127.0.0.1:8765/`，并保留“导入”页用于替换
netlist/PST 和 BOM。

## MVP 产品闭环

Hardwise 围绕 Layout handoff 前的原理图评审会组织：

```text
导入原理图 / netlist+BOM
  -> 建立 registry-verified 器件台账
  -> 运行确定性规则和器件档案 validator
  -> 分成 Must Review / Manual Gap / Passed
  -> 用带工具 trace 的 Copilot 解释证据
  -> 导出可逐项 close 的 review feedback list
```

工作台第一屏应该先回答 reviewer 的问题，而不是先讲架构：哪些项需要评审，
哪些只是 manual gap，哪些已经 pass，每一行由哪个 source token 支撑。
稳定边界见 [`docs/mvp_definition.md`](docs/mvp_definition.md)：用户问题、
核心流程、页面结构、MVP 范围、非目标和验收标准。
如果不确定某份文档是当前口径还是历史材料，先看
[`docs/docs_inventory.md`](docs/docs_inventory.md)。

## 这个 MVP 证明了什么

当前实现通过 **五大 trust 机制 + L1/L2/L3 信任分层** 证明这条 review
闭环。两条 demo 轨都是公开输入，互相补位；它不是假装同一块公开板覆盖
所有命令。

产品动作和 trust tier 的关系：

| Review 动作 | 含义 | Trust tier |
|---|---|---|
| **Must Review** | 确定性 ERROR/WARN 或高价值 checklist finding，进 Layout 前应该讨论。 | 通常 L1 |
| **Manual Gap** | 没有 ready profile、没有检索证据或原理图上下文不足，明确留给 reviewer。 | L3 |
| **Passed** | 确定性检查完成且未发现问题。 | L1 |
| **Evidence Question** | Copilot 可以引用页码级 datasheet hit 供核验，但不生成硬 validator 结论。 | L2 |

| 机制 | demo 中证明什么 |
|---|---|
| Refdes Guard | 用户可见的位号形 token 必须来自 parsed EDA registry，否则输出前包裹。 |
| Evidence Ledger | report finding 必须带 `sch:<file>#<refdes>`、`datasheet:<pdf>#p<N>` 或 `rule:<id>` 这类 source token。 |
| Sleep Consolidator | 重复 finding 只沉淀为人工审核的候选规则，不自动污染确定性规则库。 |
| Tiered Model Routing | 运行时模型从 `fast` / `normal` / `deep` env slot 选择，代码不硬编码 vendor model。 |
| Prompt Caching | 静态 agent prompt 可缓存，并在当前 Anthropic-format proxy 上实测过 cache read hit。 |

| Trust tier | 含义 | 出现位置 |
|---|---|---|
| **L1 deterministic** | Python rule / validator 产出 PASS/WARN/ERROR 真值；模型可以解释，但不负责判定。 | Component validation rows、`run_component_validation`、静态 workbench。 |
| **L2 grounded** | 某次 datasheet search turn 真的带回页码级检索证据，供 reviewer 核验；它不是逐句 NLP 证明。 | L78 trace：`datasheet:l78.pdf#p4`；U12/XL1509 workbench trace：`datasheet:xl1509.pdf#p11`、`datasheet:xl1509.pdf#p9`。 |
| **L3 manual** | 没有 ready profile 或没有 retrieval evidence，系统把问题留在人工确认区。 | no-profile workbench rows、无检索命中的 datasheet question。 |

Coverage loop 是支撑材料：Hardwise 先给 profile gap 排序，再按 family 把有公开证据的 L3/manual group 推进到 L1 deterministic rows。它证明这条产品闭环可重复，但主角仍然是 trust：模型被 registry object、evidence token、deterministic validator 和 tool returns 约束住。

KiCad 轨证明 agent / review / evidence 路径：

```bash
$ uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003,DS001 --report-style component
report: reports/pic_programmer-YYYYMMDD.md (29 findings, 121 components reviewed)
store:  reports/pic_programmer.db (121 components, 77 NC pins)
consolidator: 3 candidate rule(s) appended to memory/rules.md
```

在公开 KiCad demo 工程 `pic_programmer` 上，Hardwise 跑了四条确定性原理图检视规则：

- R001：新建器件候选识别
- R002：电容 value 字段是否声明额定耐压
- R003：NC pin 处理，含连接器/插座类批量 NC 聚合降噪
- DS001：L78 稳压器 Vin 绝对最大额定值证据检查

当前样例报告有 **29 条 finding**：6 条 R002 电容耐压字段 finding，22 条 R003 NC pin finding，以及 1 条 DS001 `U3` / L7805 finding，引用 reviewed profile token `datasheet:l78.pdf#p4`。DS001 因为当前 schematic path 不能推断实际 Vin rail，所以保持 `reviewer_to_confirm`，不会猜。每条 finding 都带 source token；NC pin 是从 KiCad `no_connect` 标记坐标反查到具体位号和管脚，不由模型生成。一次 review 还会写入关系库、运行 trace ledger，并把重复出现的问题沉淀为人工审核的候选规则。

L78 和 XL1509 这两条路径都跑过真实检索 smoke：L78 把 `l78.pdf` ingest 到 Chroma，`query-datasheet "absolute maximum input voltage"` 返回 `[l78.pdf p4 part=L7805]`，`hardwise ask ... --vector` 会先调用 `search_datasheet` 再引用第 4 页；XL1509 把公开 XLSEMI PDF 作为 `xl1509.pdf` ingest，U12 workbench 的目标问题会返回 `datasheet:xl1509.pdf#p11`（12 V 应用 / 68 uH 电感）和 `datasheet:xl1509.pdf#p9`（Schottky diode table）。详见 [`docs/evidence_chain_audit.md`](docs/evidence_chain_audit.md)。其它 profile token 是 reviewed public profile evidence；除非对应 PDF 已 staged 并检索过，否则不把它们说成 live Chroma retrieval。

Allegro 轨证明项目工作台。真实 Copilot 路径可直接双击启动器：

```bash
./scripts/start_hardwise_workbench.command
```

不需要 API key 的确定性录屏可用 fake-agent server：

```bash
uv run hardwise serve-workbench \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --document-index data/document_indexes/mixed_controller_power_stage_docs.csv \
  --fake-ai \
  --port 8765
```

公开/离线兜底用同款 SPA shell 的单文件快照：

```bash
uv run hardwise design-validator-ui \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --ai-snapshot \
  --document-index data/document_indexes/mixed_controller_power_stage_docs.csv \
  --output reports/controller-workbench.html \
  --index-output reports/controller-design-validator-index.md \
  --index-json reports/controller-design-validator-index.json
```

`--document-index` 喂入一份已审核的公开规格书链接 CSV；每个器件随后会显示
资料覆盖状态——`matched`（已有一条已审核公开链接）、`no_result`（暂无已审核
链接，如实显示覆盖缺口）、`ambiguous`（多条候选需要评审挑选）、
`manual_needed`（BOM 身份不足以匹配）。matched 只证明资料覆盖，不代表任何
电气结论。

mixed controller fixture 输出 **25 components, 22 validated rows, BOM matched=25, PASS/WARN/ERROR = 5/13/4, 3 manual/no-local-profile rows**。22 个 L1 rows 包括 9 个 profile-backed targets（U1/U12/U3/U8、D1/D5、Q1/Q2/Q12）和 13 个 generic passive checks；generic passive 只覆盖 BOM/netlist 里的显式轻量事实，不等同于深度 datasheet review。U1/L7805 重复 L78 evidence path；U12/XL1509、U3/EG2132、U8/STM32G030、Q12/SS8050 展示确定性 topology / debug-interface / profile-pin 错误。

公开/合成 pressure fixture 导入只是 coverage-planning evidence，不是主公开 demo。收口复跑结果是：Switch fixture 4010 components / 3794 validated / 216 manual / PASS/WARN/ERROR = 3663/125/6；mainboard fixture 8180 components / 7248 BOM matched / 6847 validated / 1333 manual / PASS/WARN/ERROR = 3921/2926/0。见 [`docs/closeout_pressure_summary.md`](docs/closeout_pressure_summary.md)；这次提升来自保守的 generic inductor/ferrite coverage 和 reviewed PE537BA P-MOS profile，不代表整板自动正确性判断。

同一个 Allegro 工作台可以渲染 Copilot 面板。`serve-workbench --fake-ai`
用确定性的假 client 驱动真实 agent loop；真模型模式则连接 `.env`
里配置的任意 Anthropic-format endpoint。`design-validator-ui --ai-snapshot`
把 state、component detail、exports、prep packet 和已审计问答一起烘焙进单文件
HTML（无服务、无 key）。每条面板回答都跑同一套五工具 Runner 和同一个
Refdes Guard，所以像 `U999` 这种不存在的位号会被包成 `⟨?U999⟩` 而不是被编造出来。

对于同类型重复器件，Hardwise 可以用可复用的器件档案模板（profile archetype）生成
`needs_review` 骨架，例如 `74x165_piso_16pin`。详见
[`docs/profile_archetypes.md`](docs/profile_archetypes.md)。这类草稿不会自动进入验证，
必须人工用公开 datasheet 确认后改成 `ready`。

公开 eval pack 覆盖更宽的 smoke path：

```text
5 个公开 repo / 6 个有 components 的 KiCad project directory
1707 个 parsed component
437 条 deterministic finding
0 个 project failure
10 个空 KiCad directory 被跳过
0 个 unverified refdes wrapped
0 条 finding 因缺少 evidence 被丢弃
```

这些是可复现性和回归防护指标，不是专家 gold-label 准确率声明。

## 它是什么

Hardwise 是原理图进入 PCB layout 之前的检视助手。它把公开 KiCad 工程和公开 datasheet 转成可追溯的 review artifact，并强制两条约束：

1. 用户可见的 reference designator 必须来自解析出的 EDA registry。
2. 报告里的每条 finding 必须带来源 token，例如 `sch:<file>#<refdes>`、`datasheet:<pdf>#p<N>` 或 `rule:<id>`。

它的核心不是让模型“更会说”，而是先把模型最容易胡说的地方关起来：不能编位号，不能编证据，不知道就返回 unknown 或 reviewer_to_confirm。

## 它不是什么

- 不是 PCB layout、SI/PI、EMC 或热仿真工具
- 不是 PLM 或生产级 BOM 管理系统
- 不是 Cadence/Allegro 企业集成
- 不是维修工具；Wrench Board 才是 board repair 方向的参考项目
- 不是生产产品；这是作品集 MVP

所有 demo 输入都来自公开资料。本项目不使用任何公司内部硬件数据。

## 五个机制

| # | 机制 | 作用 | 状态 |
|---|---|---|---|
| 1 | **Refdes Guard** | 用户可见的 `U1`、`R10`、`J5` 等位号形 token 必须命中 EDA registry；未知 token 会在输出前被包裹。 | 已落地：`src/hardwise/guards/refdes.py` |
| 2 | **Evidence Ledger** | 没有 evidence token 的 finding 会被丢弃。无证据，不输出。 | 已落地：`src/hardwise/guards/evidence.py` |
| 3 | **Sleep Consolidator** | 重复 finding 会沉淀为 `memory/rules.md` 里的候选规则，必须人工审核后才能启用。 | 已落地：`src/hardwise/memory/consolidator.py` |
| 4 | **Tiered Model Routing** | `fast` / `normal` / `deep` 三档模型从环境变量读取；代码不硬编码具体 upstream model。 | 已落地：`src/hardwise/agent/router.py` |
| 5 | **Prompt Caching** | 静态 agent prompt 使用 Anthropic-format `cache_control`；MiMo 实测有非零 cache read。 | 已落地：`src/hardwise/agent/prompts.py`、`src/hardwise/agent/runner.py` |

机制 1、2、4 借鉴 Wrench Board 的 defense-in-depth 和 tiered runtime。机制 3 是适合 MVP 的规则演化版本：先沉淀候选，不自动污染规则库。Agent 输出面使用同一套 tier 词汇：`L1 deterministic` 代表确定性 validator，`L2 grounded` 代表本轮有页码级检索证据，`L3 manual` 代表仍需人工确认。

## 快速开始

```bash
git clone <repo> hardwise
cd hardwise
uv sync
cp .env.example .env  # API 命令需要填写 ANTHROPIC_API_KEY
```

仓库自带公开 KiCad 样例：`data/projects/pic_programmer/`。`inspect` / `review` 类本地命令在 `uv sync` 后即可运行；API-backed 命令需要 `.env`。

Windows 用户看 [`docs/windows.md`](docs/windows.md) 里的 PowerShell 命令。当前判断是：主 CLI 和本地原理图检验工具路径应当能在原生 Windows 上跑，但只有 `windows-latest` CI 对目标 commit 通过后，才把它说成已验证支持。

### 检视原理图

```bash
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003,DS001 --report-style component
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003 --format html
```

产物：

```text
report: reports/pic_programmer-YYYYMMDD.md   (29 findings, 121 components reviewed with DS001)
report: reports/pic_programmer-YYYYMMDD.html (加 --format html 时生成 28 finding R001/R002/R003 可视化报告)
store:  reports/pic_programmer.db            (121 components, 77 NC pins)
consolidator: 3 candidate rule(s) appended to memory/rules.md
trace:  reports/trace.jsonl                  (append-only run ledger)
```

### 通过工具追问原理图

```bash
uv run hardwise ask data/projects/pic_programmer "U4 有几个 NC 脚？"
uv run hardwise ask data/projects/pic_programmer "U999 是什么器件？"
```

Agent 有 5 个结构化工具：`list_components`、`get_component`、`get_nc_pins`、`search_datasheet`、`run_component_validation`。不存在的对象会返回结构化 miss，例如 `found=false` 和相近候选；没有加载 design 或 profile 时 validation 返回 `not_configured` / `no_profile`，工具不会编造不存在的位号或验证结论。

### 带 Copilot 面板的工作台

```bash
# 离线单文件 demo（无服务、无 key）：
uv run hardwise design-validator-ui \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --ai-snapshot --document-index data/document_indexes/mixed_controller_power_stage_docs.csv \
  --output reports/controller-workbench.html

# 本地实时服务（确定性假模型，无 key）：
uv run hardwise serve-workbench \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --document-index data/document_indexes/mixed_controller_power_stage_docs.csv \
  --fake-ai --port 8765
```

两者都渲染三栏验证工作台加右侧 Copilot 面板。离线快照把已审计问答烘焙进 HTML；实时服务暴露 `POST /api/workbench/chat`。`--fake-ai` 不需要 key 就能驱动真实 agent loop（真工具、真 Refdes Guard）；去掉它并在 `.env` 配好真模型即可走在线模式。每条回答都带一个可折叠的证据 / 工具 trace，未验证位号在显示前会被包裹。

### Datasheet ingest 和语义搜索

```bash
# 先把公开 datasheet 放到 data/datasheets/
uv run hardwise ingest-datasheet data/datasheets/l78.pdf --part-ref L7805
uv run hardwise query-datasheet "absolute maximum input voltage" --top-k 3

# 导入相关公开 datasheet 后，可给 R003 加 datasheet evidence path
uv run hardwise review data/projects/pic_programmer --rules R003 --vector
```

datasheet chunk 会携带 `[l78.pdf p4 part=L7805]`、`[xl1509.pdf p11 part=XL1509-12E1]` 这类 provenance，和 reviewed profile token `datasheet:l78.pdf#p4`、`datasheet:xl1509.pdf#p11` 汇合到同一页码证据。

当前证据链边界：L78 和 XL1509 已通过 `ingest -> retrieve -> agent/workbench citation` smoke。其它 profile JSON 是 reviewed deterministic inputs，不代表每个 profile fact 都已经从 Chroma live retrieval 得到。

### 跑公开 eval pack

```bash
uv run hardwise eval --download
uv run hardwise eval --limit-projects 1
```

输出：

- `reports/eval/eval-summary.json`
- `reports/eval/eval-summary.html`

MVP 阶段的 eval gate 故意很窄：project parse failure、新增未验证位号包裹、新增无 evidence finding 被丢弃会失败；finding 数量变化先作为观察项，因为有效规则调整也可能合理增加或减少 finding。

### 切换到 PostgreSQL

关系库基于 SQLAlchemy 2.0。默认写 SQLite（`reports/<project>.db`）；设置 `HARDWISE_DB_URL` 可切 PostgreSQL 或 MySQL。

```bash
uv sync --extra postgres
export HARDWISE_DB_URL="postgresql+psycopg2://<user>@<db-host>:5432/hardwise"
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003
```

## Prompt cache 验证

`hardwise ask` 会打印 Anthropic-format `usage` token 统计。

2026-05-16 的最新冷启动探针使用配置好的 MiMo Anthropic-format proxy（`mimo-v2.5`）和一个唯一 cacheable system prompt：

| Run | Input/output tokens | Cache create/read | Result |
|---|---:|---:|---|
| 1 | 5445 / 16 | `null` / `null` | 冷 prompt 按普通 input 计费 |
| 2 | 5 / 16 | `null` / **5440** | 同一 prompt 立即命中 cache |

结论要讲准：MiMo 确实提供了可观测的 prompt cache read hit，但当前 endpoint 不返回 `cache_creation_input_tokens` 的非空创建计数。严格的 creation accounting 需要换一个会暴露该字段的 Anthropic-format endpoint 复验。

## 架构

详见 [`docs/architecture.md`](docs/architecture.md)。EDA 边界使用 adapter pattern（`src/hardwise/adapters/`），所以未来接 Cadence/Allegro 是新增一个 adapter，而不是重写主流程。

## 路线状态

当前 MVP 状态：

| Slice | 状态 | 重点 |
|---|---|---|
| 0 — Frame | 已完成 | review-node profile、sprint plan、JD alignment |
| 1 — R001 + Guards | 已完成 | Finding model、Refdes Guard、Evidence Ledger |
| 2 — R002 + Consolidator | 已完成 | 电容耐压字段检查、候选规则记忆 |
| 3 — R003 + Dual Store + Router | 已完成 | NC pin parser、SQLite/Chroma、datasheet ingest、tiered routing |
| 4 — Agent Loop + Prompt Caching | 已完成 | `hardwise ask`、5 个工具、实测 prompt-cache read hit |
| 5 — Submission Closeout | 已完成 | Phase 4 两轨 demo narrative、README/demo/docs 收口、最终 artifacts |
| Workbench — Allegro Copilot | 已完成 | `serve-workbench` 实时 agent loop + `design-validator-ui --ai-snapshot` 离线；复用五工具 Runner + Refdes Guard |

MVP 到这里停止。R004/R005 式 net-aware checks、schematic-side net parser、人工标注 calibration set、Windows CI 结果回填、Cadence/Allegro 运行时集成都明确属于 post-MVP。

## 常见技术问题

[`docs/faq.md`](docs/faq.md) 回答了关于这个项目设计取舍的 6 个高频技术问题。

## License

MIT. See [`LICENSE`](LICENSE).

## 致谢

- [Wrench Board](https://github.com/Junkz3/wrench-board)：架构灵感来源。
- KiCad open-source ECAD project：公开样例输入。
- Anthropic：Anthropic-format API protocol 和 Python SDK。
- MiMo（小米）：通过 Anthropic-compatible proxy 使用的 `mimo-v2.5` upstream。
