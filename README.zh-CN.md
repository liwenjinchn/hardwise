# Hardwise

[English](README.md) | [中文](README.zh-CN.md)

> 面向公开 KiCad 工程的原理图检视可信闭环：位号来自 EDA registry，检视意见必须带证据 token，Agent 只能通过结构化工具追问原理图。

Hardwise 是一个两周完成的作品集 MVP，锚定硬件研发里的 **pre-layout 原理图评审** 节点。它不声称大模型已经能独立判断完整硬件设计，而是证明一个更窄、更关键的工程闭环：解析公开 EDA 工程，运行检视规则，把所有输出位号压到 parsed registry 里校验，给每条 finding 挂证据 token，再让 Agent 通过工具回答器件和脚位问题。

架构灵感来自 [Wrench Board](https://github.com/Junkz3/wrench-board)（Anthropic *Build with Opus 4.7* hackathon，2026 年 4 月第二名）。只借鉴设计思路，不复制代码。

本项目使用 AI 辅助完成；设计决策和最终代码由作者审阅并负责。

---

## 简历快速入口

如果只有 90 秒，先看这里：

[![Hardwise 产品介绍页截图](docs/assets/hardwise-product-intro-screenshot.png)](https://liwenjinchn.github.io/hardwise/product-intro.html)

GitHub 会把 HTML 文件显示成源码。可以先扫上面的截图，或者打开渲染后的 GitHub Pages：

- **产品介绍页：** [https://liwenjinchn.github.io/hardwise/product-intro.html](https://liwenjinchn.github.io/hardwise/product-intro.html)
- **硬件评审展示页：** [https://liwenjinchn.github.io/hardwise/hardware-demo.html](https://liwenjinchn.github.io/hardwise/hardware-demo.html)
- **技术机制快照：** [`docs/demo.html`](docs/demo.html)
- **90 秒文字版：** [`docs/demo.md`](docs/demo.md)
- **本地复现：** `uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003 --format html`

## 这个 MVP 证明了什么

```bash
$ uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003
report: reports/pic_programmer-YYYYMMDD.md (28 findings, 121 components reviewed)
store:  reports/pic_programmer.db (121 components, 77 NC pins)
consolidator: 2 candidate rule(s) appended to memory/rules.md
```

在公开 KiCad demo 工程 `pic_programmer` 上，Hardwise 跑了三条确定性原理图检视规则：

- R001：新建器件候选识别
- R002：电容 value 字段是否声明额定耐压
- R003：NC pin 处理，含连接器/插座类批量 NC 聚合降噪

当前样例报告有 **28 条 finding**：6 条 R002 电容耐压字段 finding，22 条 R003 NC pin finding。每条 finding 都带 `sch:<file>#<refdes>` 证据 token；NC pin 是从 KiCad `no_connect` 标记坐标反查到具体位号和管脚，不由模型生成。一次 review 还会写入关系库、运行 trace ledger，并把重复出现的问题沉淀为人工审核的候选规则。

公开 eval pack 覆盖更宽的 smoke path：

```text
5 个公开 repo / 16 个 KiCad project directory
1707 个 parsed component
437 条 deterministic finding
0 个 project failure
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

机制 1、2、4 借鉴 Wrench Board 的 defense-in-depth 和 tiered runtime。机制 3 是适合 MVP 的规则演化版本：先沉淀候选，不自动污染规则库。

## 快速开始

```bash
git clone <repo> hardwise
cd hardwise
uv sync
cp .env.example .env  # API 命令需要填写 ANTHROPIC_API_KEY
```

仓库自带公开 KiCad 样例：`data/projects/pic_programmer/`。`inspect` / `review` 类本地命令在 `uv sync` 后即可运行；API-backed 命令需要 `.env`。

### 检视原理图

```bash
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003 --format html
```

产物：

```text
report: reports/pic_programmer-YYYYMMDD.md   (28 findings, 121 components reviewed)
report: reports/pic_programmer-YYYYMMDD.html (加 --format html 时生成中文可视化报告)
store:  reports/pic_programmer.db            (121 components, 77 NC pins)
memory: memory/rules.md                      (2 条候选规则)
trace:  reports/trace.jsonl                  (append-only run ledger)
```

### 通过工具追问原理图

```bash
uv run hardwise ask data/projects/pic_programmer "U4 有几个 NC 脚？"
uv run hardwise ask data/projects/pic_programmer "U999 是什么器件？"
```

Agent 有 4 个结构化工具：`list_components`、`get_component`、`get_nc_pins`、`search_datasheet`。不存在的对象会返回结构化 miss，例如 `found=false` 和相近候选；工具不会编造不存在的位号。

### Datasheet ingest 和语义搜索

```bash
# 先把公开 datasheet 放到 data/datasheets/
uv run hardwise ingest-datasheet data/datasheets/l78.pdf --part-ref U3
uv run hardwise query-datasheet "absolute maximum input voltage" --top-k 3

# 导入相关公开 datasheet 后，可给 R003 加 datasheet evidence path
uv run hardwise review data/projects/pic_programmer --rules R003 --vector
```

datasheet chunk 会携带 `[l78.pdf p7 part=U3]` 这类 provenance，后续转成 `datasheet:<pdf>#p<N>` evidence token。

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
export HARDWISE_DB_URL="postgresql+psycopg2://$USER@localhost:5432/hardwise"
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
| 4 — Agent Loop + Prompt Caching | 已完成 | `hardwise ask`、4 个工具、实测 prompt-cache read hit |
| 5 — Submission Closeout | 进行中 | README/GitHub hygiene、最终面试答案、简历材料 |

后续项明确属于 post-MVP：schematic-side net parser、人工标注 calibration set、Cadence/Allegro adapter。

## 面试问答

[`docs/interview_qa.md`](docs/interview_qa.md) 里维护了这个项目需要能回答的 6 个高频问题。

## License

MIT. See [`LICENSE`](LICENSE).

## 致谢

- [Wrench Board](https://github.com/Junkz3/wrench-board)：架构灵感来源。
- KiCad open-source ECAD project：公开样例输入。
- Anthropic：Anthropic-format API protocol 和 Python SDK。
- MiMo（小米）：通过 Anthropic-compatible proxy 使用的 `mimo-v2.5` upstream。
