# 大疆 JD ↔ Hardwise 兑现对照表

> 岗位：中/高级硬件 AI 效能工程师（深圳，技术类）。
>
> 这张表用于自检：JD 每一项要求，Hardwise 是否有具体文件 / 模块 / 文档兑现。
>
> 状态标记：
> - ✅ 已落地 — 给出文件路径
> - ⏳ slice N — 已规划，对应 slice 落地
> - 📝 文档 — 通过 docs/ 内的叙事 + 简历兑现，不需要代码
>
> 表格随 slice 推进刷新，最终目标：所有格子状态都是 ✅ 或 📝；如果某格直到 Slice 6 还卡 ⏳，要么砍掉那块 JD 要求的 Hardwise 对位（在 README 里诚实标注），要么写明为什么这个 demo 阶段做不到。

---

## 职位描述（6 项）

| # | JD 原文（节选） | Hardwise 兑现 | 状态 |
|---|---|---|---|
| 1 | 深入硬件开发（原理图、PCB、仿真、测试验证等）端到端业务场景，识别高价值数字化与 AI 落地实践机会点 | `docs/review_node.md` 节点画像 + 田野调查 7 问 + 选型说明（为什么是原理图评审节点而不是 PCB / 仿真 / 测试） | 📝 |
| 2 | 主导硬件效能工具及平台的设计与开发（如开发/测试工具、数字化作业平台、作业场景 AI Agent 等），提升硬件作业效率、质量 | CLI `hardwise review` 一行触发 84 findings + SQLite/PG store + markdown/HTML 报告；CLI `hardwise ask` 跑 Anthropic tool-use loop（`agent/runner.py` + `prompts.py` + `tools.py` 4 工具），在 pic_programmer 上 3 次真实问答闭环，含 `get_component("U999") → not_found` 防幻觉路径；`data/checklists/sch_review.yaml` 3 条 active (R001/R002/R003) + 2 条 planned (R004/R005) | ✅ R001-R003 + agent loop ＋ ⏳ R004/R005 (slice 5) |
| 3 | 基于主流硬件开发工具（如 EDA、仿真工具等），进行脚本/插件二次开发，打通工具链与 AI Agent 之间的数据与操作链路 | `src/hardwise/adapters/kicad.py`（Python S-expression 解析器，pic_programmer 121 个 refdes）+ `src/hardwise/adapters/kicad_pins.py`（坐标匹配 no_connect → pin，77 个 NC pin）+ `adapters/base.py` 适配器接口；未来 Cadence Skill/Tcl 适配器是一个新文件 | ✅ Python/KiCad + ⏳ Cadence 后续 |
| 4 | 构建并维护向量数据库（如 Milvus、Qdrant、Chroma 等），及结构化数据库（如 PostgreSQL、MySQL） | `src/hardwise/store/vector.py` (Chroma local persistent + ONNX MiniLM, l78.pdf 157 chunks) + `src/hardwise/store/relational.py` (SQLAlchemy 2.0 — PostgreSQL 与 SQLite 同套 schema 已并存验证: `HARDWISE_DB_URL=postgresql+psycopg2://...` 跑通 121 components + 77 NC pins 入 PG，默认仍写 SQLite) + `src/hardwise/ingest/pdf.py` (pdfplumber 切页 + 滑窗分块) | ✅ |
| 5 | 推动 AI Agent、自动化工具、数字化作业流在真实硬件项目中的落地与闭环迭代，持续跟踪使用数据，优化准确性与作业流顺畅度 | 3 条 active 规则 + agent tool-use loop 在公开 KiCad 工程 `pic_programmer` 上闭环；`src/hardwise/memory/consolidator.py` Sleep Consolidator 候选规则池 (R002/R003 medium 两条已沉淀) + 人工 gate；`docs/learning_log.md` 跟踪每个 slice 的命中/漏检/误报，含 Slice 4 实测 `cache_read_input_tokens` ≠ 0 的 mechanism #5 验证条目 | ✅ R001-R003 + agent loop ＋ ⏳ R004/R005 (slice 5) |
| 6 | 与硬件、流程 IT、交付团队协作，打造数字化智能化的硬件效能平台 | `docs/review_node.md` 真实评审节点画像（基于一线硬件工程师视角 + 7 问田野调查回流）；公开仓库便于跨团队复用 | 📝 |

## 任职要求（按图片原文 1, 2, 4, 5, 6）

| # | JD 原文（节选） | Hardwise / 简历兑现 | 状态 |
|---|---|---|---|
| 1 | 本科及以上学历，计算机、电子工程、自动化、通信等相关专业 | 简历条目 | 📝 |
| 2 | 四年以上工作经验，对硬件开发业务有基础认知，了解硬件开发流程，能够将业务问题转化为数字化/AI 解决思路 | 5 年国企服务器硬件经验（原理图 / BRD 检查 / BOM 导出 / PLM 维护 / 整机测试问题闭环）+ Hardwise 项目本身把这些业务动作转成 Agent 工具 | 📝 |
| 4 | 具备 EDA 或其他硬件开发工具的脚本二次开发经验（如 Skill、Python、Tcl 等） | `src/hardwise/adapters/kicad.py` + `kicad_pins.py` 一共 ~350 行 Python S-expression 解析器，手写 tokenizer + tree walker，无 kiutils 依赖；坐标变换匹配 no_connect → pin 已验证；未来 Cadence Skill/Tcl 适配器是一个新文件 | ✅ Python/KiCad + ⏳ Cadence Skill/Tcl |
| 5 | 了解向量数据库（如 Milvus、Qdrant）和结构化数据库的实际建库与使用经验 | `store/vector.py` (Chroma) + `store/relational.py` (PostgreSQL + SQLite 双后端，本地 PG 16 e2e 实测 121 components + 77 NC pins 入库，3 个 PG round-trip smoke test 全绿) + `ingest/pdf.py`；面试讲"为什么 datasheet 入向量库 / refdes 入结构化库 / refdes 是 join key"+ "Chroma → Qdrant 是 config 改动而非重写 + SQLite ↔ PostgreSQL 已通过 `HARDWISE_DB_URL` env var 切换实测" | ✅ |
| 6 | 开放心态，拥抱新事物，对 AI 与硬件结合有强烈兴趣，具备较强的自驱与落地能力 | Hardwise 整个项目（两周窗口、零代码起步、按 vertical slice 推进、公开 GitHub） | 📝 |

## 6 个面试问题与本表的关系

详见 [`docs/interview_qa.md`](interview_qa.md)。每条面试问题都会引用本表中的具体格子：

1. **这个工具帮硬件工程师省了哪一步？** → JD 职责 1, 2, 5
2. **输入数据是什么，输出报告是什么？** → JD 职责 2 + 任职 5
3. **哪些数据进向量库，哪些进结构化库？** → JD 职责 4 + 任职 5
4. **Agent 有哪些工具？为什么不能让模型自由回答？** → JD 职责 2 + Hardwise 5 机制
5. **怎么防止它编造元件编号和 datasheet 参数？** → Refdes Guard + Evidence Ledger
6. **再做一个月会补什么？** → 表中所有 ⏳ 格子的 next-step

## 自检红线

- [ ] 本表内容不引用任何公司真实项目 / 客户 / 料号 / 内部系统名
- [ ] JD 原文截图只放 `~/.claude/`，不在本仓库展示
- [ ] 每个状态变化在 `docs/learning_log.md` 留一条记录，知道哪一格在哪个 commit 翻绿
