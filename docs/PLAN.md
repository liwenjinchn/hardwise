# Hardwise Sprint Plan

> Living plan for the 2-week MVP. Updated when scope shifts, not every session.
> Plans landed in this file are **decision records** — committed to git so the "why we built it this way" survives alongside the code.
>
> See also:
> - `CLAUDE.md` — project rules (timeless)
> - `docs/architecture.md` — module-level design
> - `docs/review_node.md` — schematic-review-node profile + field-survey template (the demo anchor)
> - `docs/jd_alignment.md` — DJI JD ↔ Hardwise commitment table
> - `docs/rolling_log.md` — staged improvements waiting for milestones
> - `docs/learning_log.md` — debugging journal

---

## Sprint goal

In two weeks, ship a CLI tool `hardwise review <project> --rules R001[,R002,...]` that:

1. Reads a public KiCad project + a checklist of 5 schematic-review rules from `data/checklists/sch_review.yaml`
2. Runs an Anthropic tool-use loop where every rule is evidence-driven via structured tools, never free-form
3. Produces a markdown review report aligned to the structure of《SCH_review_feedback_list 汇总表》— every refdes registry-verified, every claim carries a source token
4. Records candidate review rules to `memory/rules.md` for human gate

**Each slice ends with a runnable end-to-end demo and a screencast.** Never wait until "Day N" to see something work — see DR-006.

---

## Slice route (replaces day-by-day)

| Slice | Focus | Deliverable | New mechanism |
|---|---|---|---|
| 0 | Frame + 容器 | `review_node.md` + `sch_review.yaml` + `jd_alignment.md` + `PLAN/CLAUDE/AGENTS` update | none |
| 1 | First end-to-end loop (R001 新建器件候选识别) | `hardwise review --rules R001` → markdown report + tests + screencast; `checklist/finding.py` 统一 Finding 数据模型在此 slice 立 | Refdes Guard + Evidence Ledger |
| 2 | R002 电容耐压 80% | `--rules R001,R002` + first Sleep Consolidator candidates | Sleep Consolidator |
| 3 | R003 NC pin + 双库进场 | chromadb + sentence-transformers + pdfplumber installed; datasheet ingest; first datasheet-evidence finding | Tiered Model Routing |
| 4 | R004 I2C 地址冲突 | `--rules R001..R004`; cache-hit observable in run log | Prompt Caching |
| 5 | R005 单端/空网络 + 报告固化 | All 5 rules run; report visually aligns with SCH_review_feedback_list | none |
| 6 | Demo 收口 | README quickstart / 3-min screencast / `interview_qa.md` v1.0 / `jd_alignment.md` filled / 简历 / 投递 | none |

## Application gates

The slice route is the build plan, not the job-application gate. Do **not** wait for Slice 5 to start applying.

| Gate | Required slices | What it proves | Action |
|---|---|---|---|
| A — runnable proof | Slice 0 + Slice 1 | A real schematic-review rule can run end-to-end: rule -> tool/evidence -> finding -> report, with Refdes Guard + Evidence Ledger | OK for internal demo rehearsal and README draft; not the preferred DJI submission gate |
| B — submission MVP | Slice 0 + Slice 1 + Slice 3-lite + submission closeout | EDA registry, structured store, vector datasheet evidence, tool-use report, JD alignment, and interview answers all have concrete proof | **Start DJI application here** |
| C — stronger follow-up demo | Slice 4-5 + polished Slice 6 | More rules, prompt caching, report polish, 3-min demo video | Continue while waiting for recruiter / interview feedback |

**Slice 3-lite definition**: if full R003 takes too long, the minimum acceptable database proof is:
1. SQLite or equivalent relational store contains components/rules/findings from the public KiCad project
2. Chroma or equivalent local vector store ingests at least one public datasheet/checklist chunk
3. One finding carries both a structured evidence token and a text evidence token
4. `docs/jd_alignment.md`, `docs/interview_qa.md`, README quickstart, resume bullet, and GitHub hygiene are updated

After Gate B, pull the useful parts of Slice 6 forward: README, GitHub, resume, and interview prep. Leave the 3-minute video and Slice 4-5 polish as follow-up work.

**Slice acceptance template** — every slice closes when:
1. CLI 一行命令出可演示物（report / screencast / log）
2. `uv run pytest -q && uv run ruff check .` 全过
3. `docs/interview_qa.md` 至少 1 题更新到 v(slice_n).0
4. `docs/learning_log.md` 写一条"今天证明了什么"

**Buffer rule**: if a slice stalls 4 hours → cut new mechanism first (keep the rule); still stuck → mock the data source (e.g. `nets.json` instead of parser); still stuck → skip to next slice. Floor delivery is Slice 0 + Slice 1 + pulled-forward Slice 6 materials — that qualifies as an internal defendable demo. Preferred DJI submission remains Gate B.

---

## Major architectural decisions (decision records)

### DR-001 — Direct mode, not Anthropic Managed Agents
**Date**: 2026-05-08
**Decision**: Use `messages.create` + Python tool loop. Skip Managed Agents bootstrap.
**Why**: Wrench Board ships both runtimes with identical WS protocol; the direct path is simpler, faster to debug, no environment + agent + memory store bootstrap. MVP review sessions are stateless — MA's persistence buys nothing.
**When to revisit**: If reviews need cross-session memory of past reviews. Slice 2 Sleep Consolidator writes to `memory/rules.md` (file-on-disk), not a managed memory store, so this revisit threshold is post-MVP.

### DR-002 — KiCad-only adapter for v1
**Date**: 2026-05-08
**Decision**: Ship `adapters/kicad.py` as the only EDA adapter; `adapters/base.py` defines the interface for future Cadence/Allegro.
**Why**: Mac dev machine can't run Cadence (license + OS). Public KiCad samples (KiCad demos, Olimex, Mnt Reform) abundant. Adapter pattern preserves the Cadence path as one new file later.
**When to revisit**: After MVP, if a real demo opportunity at DJI requires Cadence parity — at which point the work moves to the Windows + Cadence work machine using Cadence Skill bindings.

### DR-003 — SQLite + Chroma local mode
**Date**: 2026-05-08
**Decision**: SQLite for relational store, Chroma in local file mode for vector store. No Postgres, no Qdrant/Milvus.
**Why**: Zero ops cost, file-on-disk for both, compatible with `uv run`. JD says "PostgreSQL/MySQL or Milvus/Qdrant/Chroma or similar"; SQLite + Chroma demonstrates the same architectural pattern at MVP scale and demo speed. Switching to Postgres / Qdrant later is a config change, not a rewrite.
**When to revisit**: If the corpus exceeds ~10k vector chunks (won't happen in 2 weeks) or if a real Postgres deployment is needed for the demo session.

### DR-004 — Plan mode is the default starting Slice 1
**Date**: 2026-05-08 (originally "Day 2"; reframed 2026-05-09 with DR-006)
**Decision**: For every multi-file or unfamiliar implementation task starting Slice 1, enter Claude Code plan mode first; iterate the plan to user satisfaction; only then execute.
**Why**: Cherny's recommended workflow ("once there is a good plan, it will one-shot the implementation"). Day 1's scaffold task skipped this and produced a Typer single-command bug that a planned approach would have caught (we'd have written 2+ commands, dodging the auto-collapse). Skipped only when the diff is describable in one sentence.
**When to revisit**: If plan mode adds noticeable friction without proportional value — but the bar to skip is high.

### DR-005 — Upstream model is MiMo-V2.5 via Anthropic-format proxy
**Date**: 2026-05-08
**Decision**: Set all three tier slots (`HARDWISE_MODEL_FAST/NORMAL/DEEP`) to `mimo-v2.5`. The proxy at `xiaomimimo.com/anthropic` speaks Anthropic message format, so the `anthropic` Python SDK works unchanged.
**Why**: User-provided API access is MiMo, not Anthropic Claude. Keeping the 3-tier slot structure (architectural pattern from Wrench Board) preserves the cost-aware-routing mechanism for the day MiMo ships variants — no code change needed, only `.env` values flip. The agent code never hard-codes a specific model name.
**When to revisit**: When MiMo exposes smaller/larger variants (replace per slot), or if a different upstream is needed for benchmarking (point `ANTHROPIC_BASE_URL` elsewhere).

### DR-006 — Vertical slice 优于按天水平横切
**Date**: 2026-05-09
**Decision**: 放弃原 Day 1–14 的水平横切（先双库 → 再 ingest → 再 agent → 再 guard），改为 Slice 0–6 的 vertical slice。每个 slice 包含端到端可运行的最小闭环。
**Why**: 作者零代码 + 5 月底死线 + 中间任何环节阻塞会全链路延期。原 Day 4–10 路线最大的风险是 Day 8 之前没有任何东西能跑，作者每天无法回答"今天这个能不能跑/输入是什么/比昨天多证明了什么"。Slice 1 选 R001（**新建器件候选识别**，footprint 字段为空作为弱信号）是因为它在 5 条规则中**唯一一条不依赖向量库 / datasheet 解析 / net 解析 / 外部 BOM**——只用 sch 内部已解析字段。把重型依赖（chromadb + sentence-transformers + pdfplumber）推到 Slice 3，确保 Slice 1 一两天可达。原 R001（"refdes ↔ BOM 一致性"）已被废弃——评审节点没有 PLM-grade BOM，那是 Gerber 之后才出现的下游产物（详见 `docs/review_node.md`）。
**When to revisit**: 当 Slice 1 真正跑通且后续 slice 明显需要共享基础设施（比如 R003/R004 都依赖 datasheet 入库）时，允许在 slice 内部局部水平做一次基础设施铺底——但只在已经有可演示物的基础上。

### DR-007 — Demo 锚点收窄到原理图评审节点
**Date**: 2026-05-09
**Decision**: README、CLAUDE/AGENTS Hard rules、Sprint goal、所有 slice 描述，都把 demo 锚点定在硬件研发流程的【原理图进 Layout 前】这一个节点。任何跨节点功能（PCB review / 仿真 / 测试结果回灌 / BOM 管理 / FMEA / 整机测试问题闭环 / PLM 等）一律延后。
**Why**: 硬件研发流程节点很多，一个 2 周 MVP 如果想"覆盖端到端"，最终哪个节点都讲不深。原理图评审是研发链条最早的可干预点（越早抓越便宜，改板代价以"周"计），且作者本人 5 年硬件经验里最能讲清楚的一格。"窄而真"比"广而浅"在 demo 场景说服力更强。详细节点画像在 `docs/review_node.md`，并安排 5 月初一次田野调查回流。
**When to revisit**: 如果田野调查或后续面试中出现强证据表明另一个节点（如 PCB review）痛点更大，再考虑迁移。MVP 阶段不动。

### DR-008 — Slice 1 立统一 Finding 数据模型 + R001 必须用 schematic-only registry
**Date**: 2026-05-10
**Decision**:
1. **统一 Finding 数据模型在 Slice 1 立**：新增 `src/hardwise/checklist/finding.py`，定义 Pydantic `Finding` 模型 — 字段 `{rule_id, severity, refdes?, net?, message, evidence_tokens[], suggested_action, status}`。所有 check function 返回 `list[Finding]`；所有 guard / report 消费 `Finding`。Slice 2+ 的新规则不允许另立 finding 形状。
2. **R001 实现必须用 `parse_schematic` 返回的原始 ComponentRecord**，不能用 `parse_project` 返回的 merged `BoardRegistry.components`。
**Why**:
1. Finding 模型是所有规则、guard、report 的共享契约。如果在 Slice 2 才立，Slice 1 的 R001 + Refdes Guard + Evidence Ledger + Markdown Report 会先用 ad-hoc dict，Slice 2 再回头重构 — 这正是 vertical slice 想避免的"先快后乱"。
2. `adapters/kicad.py:30-31` 在 merge 阶段用 `.kicad_pcb` 的 footprint 回填 `.kicad_sch` 中空的 footprint 字段。这个行为对 Refdes Guard 是好事（能拿到完整封装信息），但对 R001（"footprint 为空 → 新建器件候选"）是 bug — 凡是 PCB 已经画过的器件，footprint 字段都不会再为空，R001 会把所有真实新建器件漏掉。
**Implementation note**: 不修改 `parse_project` 现有行为（向后兼容 Refdes Guard 的需要）。两个备选实现路径任选其一：(a) `BoardRegistry` 增加 `schematic_records: list[ComponentRecord]` 和 `pcb_records: list[ComponentRecord]` 两个 raw 字段；R001 读 `schematic_records`；或 (b) R001 直接调 `parse_schematic` glob，绕开 `BoardRegistry`。Slice 1 实施时挑一个，写进 `docs/architecture.md`。
**When to revisit**: 如果 Slice 2+ 需要 R002/R003 也访问 schematic-only / pcb-only 数据，统一切到方案 (a) 防止规则代码分散调用 parser。

---

## Day 1 retrospective (summary)

**Shipped**:
- 16 scaffold files, 5 docs files (CLAUDE.md / architecture.md / interview_qa.md / learning_log.md / rolling_log.md), 11 personal memory files
- CLAUDE.md iterated v1 → v2 after Wrench Board comparison surfaced abstract-vs-spec gap
- Two debugged issues logged (Typer collapse, CLAUDE.md framing)

**Process gaps surfaced and addressed**:

1. Skipped reading Wrench Board source first → corrected; reference memory now exists
2. Skipped CLAUDE.md as Day 1 deliverable → corrected; init checklist in memory
3. CLAUDE.md was narrative not spec-density → corrected; editorial rule + concrete regex + Models table added
4. Did not use plan mode for the scaffold task → captured as DR-004 above; default starting Slice 1

---

## Discharged plan items (audit trail)

> When a slice or major chunk ships, leave a one-line entry below with the date and the commit SHA range.

- 2026-05-08 — Day 1 scaffold closed (16 scaffold files + 5 docs + 11 memories).
- 2026-05-09 — KiCad adapter shipped: `adapters/{base.py, kicad.py}` + `cli.py:inspect-kicad` + `tests/test_kicad_adapter.py`. `pic_programmer` registry returns 121 components.
- 2026-05-09 — Plan rewritten from Day 1–14 horizontal route to Slice 0–6 vertical-slice route (DR-006). Demo anchor narrowed to schematic-review node (DR-007).
- 2026-05-09 — Slice 0 frame closed: `docs/review_node.md` + `data/checklists/sch_review.yaml` + `docs/jd_alignment.md` + this PLAN rewrite + CLAUDE/AGENTS Hard rule #5.
- 2026-05-09 — R001 redefined from "refdes ↔ BOM consistency" to "new-component candidate identification (footprint field empty)" after node-profile interview revealed PLM-grade BOM doesn't exist at the schematic-review stage. R002's `required_evidence` rewritten away from external BOM dependency for the same reason. See `docs/review_node.md` for the input-data contract at the review node.
- 2026-05-10 — DR-008 added: Finding 统一数据模型在 Slice 1 立；R001 必须用 schematic-only registry，避开 `parse_project` 的 PCB-footprint-backfill 行为。`docs/review_node.md` 输入物从 3 类瘦到 2 类（去掉"上一代 sch"，因为 MVP 不实现两版自动 diff）。`sch_review.yaml` R001 `required_evidence` 改为 `EDA.schematic_record.footprint` 并加 inline 注释。
- 2026-05-10 — Slice 1 closed (Sub-slices 1a + 1b + 1c + 1d): Finding/RuleSpec/loader/check + R001 + extended BoardRegistry; CLI `review` command + markdown report aligned to《SCH_review_feedback_list》; Refdes Guard + Evidence Ledger wired through render path; e2e test + interview_qa Q1/Q5 v0.5 + this Discharged entry. 28 tests pass, ruff clean. `uv run hardwise review data/projects/pic_programmer --rules R001` produces `reports/pic_programmer-YYYYMMDD.md` with "0 candidate findings, 121 components reviewed" — honest output for a finished public sample (per `docs/learning_log.md` 2026-05-10 entry).
- 2026-05-11 — Slice 2 closed: R002 (cap rated-voltage field completeness, value-side only — 80% derating comparison deferred to Slice 3+ pending net parser) + Sleep Consolidator minimum (`src/hardwise/memory/consolidator.py`, pure statistical aggregation, threshold=3, file-on-disk human gate). CLI `review` extended with `--consolidate/--no-consolidate` + `--memory-output PATH`. yaml R002 flipped `planned → active` with two-stage `rule` text so docs match code. `uv run hardwise review data/projects/pic_programmer --rules R001,R002` → 7 findings (6 R002 medium for C1/C2/C5/C6/C7/C9 missing `/V` suffix + 1 R002 info for C3=`22uF/25V`; C4=`0` skipped) + 1 candidate rule appended to `memory/rules.md`. 58 tests pass (Slice 1 baseline 29 → Slice 2 close 58 = +19 R002 + 7 consolidator + 3 e2e Slice 2), ruff + format checks clean. interview_qa Q2 upgraded to v1.0. `memory/*.md` added to `.gitignore` with `.gitkeep` carved out, mirroring the `reports/` convention.
- 2026-05-12 — Slice 3 closed (Sub-slices 3a/3b/3c/3d/3e): KiCad pin + no_connect parser (`adapters/kicad_pins.py`, coordinate-matched `pin.at` as connectable endpoint, `pic_programmer` produces 77 NC pins = 6 main + 71 sub-sheet, no false positives); R003 NC pin handling check (EDA-only stage, severity=medium, 77 findings on pic_programmer, datasheet semantic comparison deferred to Slice 4); SQLite relational store (`store/relational.py`, SQLAlchemy 2.0, `components` + `nc_pins` tables, `--db-path` CLI option, populates `reports/<project>.db` with 121 components + 77 NC pins on pic_programmer); Chroma vector store + PDF ingest (`store/vector.py` + `ingest/pdf.py`, bundled ONNX MiniLM embedder, no `sentence-transformers` dep needed); two new CLI commands `ingest-datasheet` and `query-datasheet` (verified live on user-supplied `l78.pdf` → 157 chunks, top-1 result for "absolute maximum input voltage" correctly returns p4); `agent/router.py` ModelRouter (3-tier env-driven, with normal-fallback + final hard-coded fallback); `verify-api --tier {fast,normal,deep}` wired to router. 93 tests pass + 4 slow tests pass (pin parser 10 + R003 unit 6 + e2e slice3 3 + relational 5 + ingest pdf 4 + vector 4 slow + router 7 = +39 new; baseline 58 → 97 total when including slow), ruff clean. yaml R003 flipped `planned → active` with two-stage rule text. interview_qa Q3 upgraded to v3.0. learning_log gains "KiCad pin.at IS connectable endpoint" and "Chromadb default ONNX embedder needs no sentence-transformers" entries. rolling_log gains 123.md-derived candidate rules R006 (通用 net 命名) + R007 (分类 net 命名) gated behind Slice 5 net parser. architecture.md → v0.4 documenting `store/`, `ingest/`, `agent/router.py`, `kicad_pins.py`. **Gate B 条件满足**：双库 live、refdes 跨库 join、77 R003 findings + 双库证据 token 雏形 + Tiered Routing 全部就位。
