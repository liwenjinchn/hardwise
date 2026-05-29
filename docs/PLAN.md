# Hardwise Sprint Plan

> Living plan for the 2-week MVP. Updated when scope shifts, not every session.
> Plans landed in this file are **decision records** — committed to git so the "why we built it this way" survives alongside the code.
>
> HTML 阅读版：`docs/PLAN.html`
>
> See also:
> - `CLAUDE.md` — project rules (timeless)
> - `docs/architecture.md` — module-level design
> - `docs/review_node.md` — schematic-review-node profile + field-survey template (the demo anchor)
> - `docs/jd_alignment.md` — DJI JD ↔ Hardwise commitment table
> - `docs/rolling_log.md` — staged improvements waiting for milestones
> - `docs/learning_log.md` — debugging journal

---

## Submission boundary

Hardwise is now in **submission closeout**, not feature expansion. The MVP claim is:

> A public KiCad schematic can be parsed into a trusted registry; deterministic checks can produce evidence-gated findings; and the agent can answer schematic questions only through structured tools, with unverified refdes blocked before reaching the user.

The submission demo is complete when the following remain true:

1. `hardwise review data/projects/pic_programmer --rules R001,R002,R003` produces a report with registry-verified refdes and evidence tokens.
2. `hardwise ask ...` demonstrates the tool-use loop, including an unknown-refdes path such as `get_component("U999") -> not_found`.
3. `uv run pytest -q` and `uv run ruff check .` pass.
4. README, interview answers, and resume materials describe the narrow proof honestly.

R004/R005, schematic-side net parsing, GitHub Action packaging, larger gold-label evaluation, Cadence/Allegro adapters, and PR-comment workflows are **post-MVP**. They can remain in backlog documents, but they are no longer submission gates.

## Sprint goal

In two weeks, ship a CLI tool `hardwise review <project> --rules R001[,R002,...]` that:

1. Reads a public KiCad project + active schematic-review rules from `data/checklists/sch_review.yaml`
2. Runs deterministic checks and an Anthropic-format tool-use loop where board objects come from structured tools, never free-form generation
3. Produces a markdown/HTML review report aligned to the structure of《SCH_review_feedback_list 汇总表》— every refdes registry-verified, every finding carries a source token
4. Records candidate review rules to `memory/rules.md` for human gate

**Each slice ends with a runnable end-to-end demo and a screencast.** Never wait until "Day N" to see something work — see DR-006.

---

## Slice route (historical build route)

| Slice | Focus | Deliverable | New mechanism |
|---|---|---|---|
| 0 | Frame + 容器 | `review_node.md` + `sch_review.yaml` + `jd_alignment.md` + `PLAN/CLAUDE/AGENTS` update | none |
| 1 | First end-to-end loop (R001 新建器件候选识别) | `hardwise review --rules R001` → markdown report + tests + screencast; `checklist/finding.py` 统一 Finding 数据模型在此 slice 立 | Refdes Guard + Evidence Ledger |
| 2 | R002 电容耐压 80% | `--rules R001,R002` + first Sleep Consolidator candidates | Sleep Consolidator |
| 3 | R003 NC pin + 双库进场 | chromadb + sentence-transformers + pdfplumber installed; datasheet ingest; first datasheet-evidence finding | Tiered Model Routing |
| 4 | Agent loop + prompt caching | `hardwise ask` with 4 tools; unknown-refdes path; cache-read observable in run log | Prompt Caching |
| 5 | Submission closeout | README quickstart / demo pages / `interview_qa.md` / `jd_alignment.md` / resume materials | none |
| Post-MVP | Schematic net parser + R004/R005 | Net-aware checks after `.kicad_sch` topology parser exists | none |

## Application gates

The slice route is the build plan, not the job-application gate. Do **not** wait for post-MVP net-aware work to start applying.

| Gate | Required slices | What it proves | Action |
|---|---|---|---|
| A — runnable proof | Slice 0 + Slice 1 | A real schematic-review rule can run end-to-end: rule -> tool/evidence -> finding -> report, with Refdes Guard + Evidence Ledger | OK for internal demo rehearsal and README draft; not the preferred DJI submission gate |
| B — submission MVP | Slice 0 + Slice 1 + Slice 3-lite + submission closeout | EDA registry, structured store, vector datasheet evidence, tool-use report, JD alignment, and interview answers all have concrete proof | **Start DJI application here** |
| C — stronger follow-up demo | Slice 4 + submission closeout | Tool-use loop, prompt caching, report polish, demo pages | Continue while waiting for recruiter / interview feedback |

**Slice 3-lite definition**: if full R003 takes too long, the minimum acceptable database proof is:
1. SQLite or equivalent relational store contains components/rules/findings from the public KiCad project
2. Chroma or equivalent local vector store ingests at least one public datasheet/checklist chunk
3. One finding carries both a structured evidence token and a text evidence token
4. `docs/jd_alignment.md`, `docs/interview_qa.md`, README quickstart, resume bullet, and GitHub hygiene are updated

After Gate B, pull the useful parts of closeout forward: README, GitHub, resume, and interview prep. Leave net-aware rules, GitHub Action packaging, and larger evaluation as follow-up work.

**Slice acceptance template** — every slice closes when:
1. CLI 一行命令出可演示物（report / screencast / log）
2. `uv run pytest -q && uv run ruff check .` 全过
3. `docs/interview_qa.md` 至少 1 题更新到 v(slice_n).0
4. `docs/learning_log.md` 写一条"今天证明了什么"

**Buffer rule**: if a post-MVP feature stalls 4 hours → stop expanding and return to the submission boundary above. The defensible demo is already the R001/R002/R003 report + guarded tool-use loop + passing tests/lint; extra rules are not required for submission.

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

### DR-009 — Finding 加 evidence_chain + decision 两个向后兼容字段（DR-008 之后允许的扩展）
**Date**: 2026-05-14
**Decision**:
1. **`Finding` 新增两个可选字段**，**都向后兼容、默认空**——不替换、不重命名、不改变任何既有字段语义：
   - `evidence_chain: list[EvidenceStep] = Field(default_factory=list)` — 结构化证据链，按出现顺序排列；
   - `decision: Optional[Literal['likely_ok', 'likely_issue', 'reviewer_to_confirm']] = None` — 规则对该 finding 的判断结论，与流程状态严格分离。
2. **新增 `EvidenceStep` Pydantic 模型**（同文件 `checklist/finding.py`），最小字段集：
   - `source: Literal['eda', 'datasheet', 'rule']` — 证据来源类型；
   - `claim: str` — 一句人话写的证据陈述（用于报告渲染、reviewer 阅读）；
   - `token: str` — 机器可读 provenance，复用 `ingest/pdf.py:26` 的 `evidence_token()` 风格（例如 `sch:foo.kicad_sch#U4` / `pdf:l78.pdf#p4` / `rule:R003#nc_match`）。
3. **`status` 字段语义不变**：仍是评审流程状态 `open / accepted / rejected / closed`，由人审或后续 review-workflow 改。**规则代码不写 `status`**——规则的判断写进 `decision`。这是「判断结论（机器）」与「流程状态（人）」的强制分工。

**Why**:
1. **Slice 5 之前要给 R003 装 datasheet 证据闭环**（"EDA 标 NC + datasheet 第 N 页说 NC ⇒ 建议接受"），需要把 datasheet hit + 规则判断挂到 Finding 上。但 DR-008 把 Finding 的结构锁住了——「Slice 2+ extend behavior, never structure」。原文锁的是「不另起 Finding 替代类型、不改既有字段语义」，并不禁止「添加默认空的可选新字段」——后者对所有现存代码是无副作用的。DR-009 把这条边界写明，避免下次有人误以为 DR-008 永远封死 Finding。
2. **不并入 `status` 的原因**：`status` 是审评流程的状态机字段（open → accepted/rejected/closed），由 reviewer 或后续工作流推进；规则给出的 `likely_ok / likely_issue / reviewer_to_confirm` 是**判断结论**——一个 finding 可以同时是 "rule 判 likely_ok"（机器结论）+ "open"（人还没看）。混在一起会导致：reviewer 看到一个 `status=likely_ok` 的 finding 不知道是规则建议还是已经 accepted。所以拆成两个字段。
3. **不另起 `FindingWithTrace` / `TracedFinding` 的原因**：报告渲染、guard、Sleep Consolidator、序列化路径都消费 `Finding`。新建并行类型会引发到处分支判断（"这个 finding 有没有 trace?"），DR-008 想避免的"两套形状"问题会重新出现。可选默认空字段在 Pydantic 序列化里也是无成本的（默认空时不出现在 dict 里）。
4. **`source: Literal[...]` 而不是自由字符串**：三类来源（EDA registry / datasheet vector store / rule 自身的演绎）是当前架构的唯一三个证据通道；用 Literal 强制收敛，避免后来人随便加 `"intuition"` 之类的非证据来源。

**Implementation note**: 实际落地拆成 A3（`checklist/finding.py` 加字段 + EvidenceStep 模型 + 单元测试，不动任何 check）与 A4（R003 是第一个写新字段的 rule）两步，每步独立 commit。R001 / R002 不动——它们没有 datasheet 证据闭环需求，让旧 finding 形状继续运作。Report 渲染层（`report/markdown.py` / `report/html.py`）按"如果 `evidence_chain` 非空则展开成子列表，否则继续用 `evidence_tokens`"渐进升级，向后兼容。

**When to revisit**:
- 如果出现第 4 个结构性需求（比如 finding 之间的关联引用、reviewer 反馈文本、规则自评信心分），优先考虑**组合**（子模型 / 关联表）而不是继续加 Finding 顶层字段——再加就该写一个单独 decision record 重新审视 Finding 类型边界。
- 如果 `evidence_chain` 在多个 rule 之间出现明显的「相同 datasheet 多次重复嵌入」开销，把 EvidenceStep 改为 `token` 引用 + 单独的 evidence store——但这是性能优化，非 MVP 必要。

### DR-010 — Final validator path stays component-index first
**Date**: 2026-05-26
**Decision**: The path toward the target design-validator experience is staged through component-index artifacts before AI validation output. V2.8 adds report index/readability (`Component Prefix Summary`, `BOM Item Groups`, `--summary-only`, `--mismatch-only`, short source tokens). V2.9 adds local datasheet/document matching by BOM item identity or MPN, with explicit evidence states instead of live supplier lookup. V3.0 adds structured pin profiles. V3.1 adds deterministic single-component pin-level PASS/WARN/ERROR reports for one selected refdes plus one structured profile. V3.2 adds a local static HTML UI that mirrors the component list + detail workflow without adding a hosted app or PCB canvas.

**Why**: The desired product shape includes component list, datasheet links, per-component validation, status counts, and detail reports. Jumping straight from Allegro+BOM intake to model-written validation would bypass the registry/BOM facts that make Hardwise trustworthy. Component-index-first keeps every later claim anchored to parsed refdes, BOM rows, source tokens, and eventually datasheet profile tokens.

**Scope boundary**: These stages remain inside the pre-Layout schematic-review node. They may use schematic netlists, schematic-exported BOMs, public datasheets, structured pin profiles, and deterministic rule templates. They must not parse `.brd`, boardview, placement, routing, PCB geometry, PLM lifecycle, pricing, supplier-risk, simulation, or test-result feedback.

**When to revisit**: After the first deterministic regulator report has been exercised on public inputs, expand only by adding one component-family template at a time, such as gate driver, MCU, diode/MOSFET, or connector. If registry-verified refdes/pin evidence and datasheet/profile source tokens are not achievable for a family, keep that family at intake/index + manual review instead of widening scope.

---

### DR-011 — Post-migration priority is the agent↔validator bridge, not more families
**Date**: 2026-05-29
**Context**: Codebase audit on the `codex/migrate-codex-mainline` product trunk after the diode/connector/MOSFET family migration. Two findings drive this record:

1. **Two parallel pipelines that do not connect.** Pipeline A is `hardwise review <kicad>` — checklist rules (R001/R002/R003/DS001) plus the Anthropic-format tool-use loop in `agent/runner.py` exposing four tools (`list_components`, `get_component`, `get_nc_pins`, `search_datasheet`). Pipeline B is the `design-validator-ui` / `report-validator-ui` workbench — the deterministic `validation/` family validators (buck, gate_driver, mcu, i2c_mux, diode, connector, mosfet). `agent/` has **zero** references to `validation/`; none of the four agent tools call a family validator. The strongest deterministic work (the family validators) is unreachable from the agent that is supposed to be the product's "AI hardware review agent".
2. **Datasheet profiles are hand-authored; no real PDF has been ingested.** Every `data/datasheet_profiles/*.json` cites synthetic evidence tokens like `datasheet:irf540n.pdf#p1`, but no such PDF exists on disk. The `pdfplumber → chroma → search_datasheet` ingest path is real code but has never been exercised on a real public datasheet end-to-end, so provenance is *claimed* rather than *proven*.

**Decision**: After the validator-family migration, the next two work blocks are, in priority order:
- **Phase 1 — agent↔validator bridge (highest narrative leverage).** Add a `run_component_validation(refdes)` tool that lets the agent call `validate_component_against_profile`, receive structured PASS/WARN/ERROR, and assemble evidence-carrying findings. This fuses pipelines A and B into one "AI hardware review agent" story.
- **Phase 2 — real datasheet evidence chain (highest credibility leverage).** Ingest one real public PDF (L78 or SS34 are public) through the existing ingest path so at least the `abs_max` facts carry real `#pN` page tokens, turning provenance from claimed into proven. Closes the Slice 3 anchor.

Continuing to add device families (BJT, P-channel MOSFET) is **lower** leverage than either bridge and is explicitly deprioritised until Phase 1+2 land.

**Why**: The DJI JD pitch is "AI agent for hardware efficiency". The audit shows the agent and the validators are two separate demos; the single highest-value change is making the agent actually drive the deterministic validators. Real provenance is the second pillar of the trust story (Refdes Guard being the first). Both are收口 / closure work on existing assets, not new scope — they stay inside the pre-Layout schematic-review node (DR-007).

**Scope boundary**: Phase 1 wires existing components together; it adds no PCB, boardview, placement, routing, PLM, pricing, or simulation surface. Phase 2 uses only public datasheets already cited by the profiles. The bridge tool returns structured nulls for unknown refdes/profile, consistent with the tools-never-fabricate rule.

**When to revisit**: If Phase 1 reveals the agent loop needs structural change to consume validator output (e.g. a new evidence shape), capture it as a follow-up DR. If real-PDF ingest proves a profile's hand-authored facts wrong, fix the profile and log it in `learning_log.md`.

---

## Post-migration roadmap (toward Gate B submission)

The validator-family work is late-stage closure, not early build. This roadmap sequences the remaining work by leverage on the DJI submission narrative (DR-011). Each phase keeps the slice-acceptance template: one CLI/demo artifact, green `pytest` + `ruff`, an `interview_qa.md` touch, and a `learning_log.md` entry.

| Phase | Goal | Key deliverable | Ship gate | Leverage |
|---|---|---|---|---|
| 0 | Housekeeping | Archive the two `in_progress` Trellis tasks; confirm DS001 runs end-to-end in `review` | No stale in-progress tasks; DS001 produces a finding on a profiled component | low, fast |
| 1 | **Agent↔validator bridge** | `run_component_validation(refdes)` tool + `agent/runner.py` wiring + one end-to-end test where the agent validates a single component and returns an evidence-carrying finding | Agent run on a public/synthetic project calls a family validator and surfaces structured PASS/WARN/ERROR with source tokens | **highest** |
| 2 | **Real datasheet evidence chain** | One real public PDF (L78 or SS34) ingested via `pdfplumber → chroma`; at least one profile's `abs_max` fact carries a real `#pN` token; `search_datasheet` returns a real hit | A finding cites a real datasheet page, not a synthetic token; Slice 3 anchor closed | **high** |
| 3 | BJT family + MOSFET finish | `validation/bjt.py` reusing the reference-node pattern (Vbe = base − emitter); P-channel / body-diode notes as backlog | BJT fixture catches a base-drive issue; dispatch stays topology_family-only | medium |
| 4 | End-to-end demo + narrative | Screencast on a public controller board: agent review → validator call → datasheet-cited finding → HTML workbench; update `interview_qa.md` + resume bullet | Reproducible public demo; submission materials current | = Gate B |

**Sequencing note**: Phase 1 and Phase 2 are the two pieces that turn the "AI agent for hardware review" pitch into a real demo; both rank above adding more families (Phase 3). Phase 0 is a sub-hour warm-up. Phase 4 is the submission close.

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
- 2026-05-13 — Slice 4 prep: `src/hardwise/agent/tools.py` shipped — 4 tools (`list_components` / `get_component` / `get_nc_pins` / `search_datasheet`), each with Pydantic input + output and a structured null/unknown branch; `get_component` miss returns `ComponentNotFound{refdes, closest_matches}` via `difflib.get_close_matches` over `BoardRegistry.refdes_set` — tools never fabricate. `TOOL_DEFINITIONS` is Anthropic-SDK `tools=[…]` shaped. 7 fast tests added (baseline 93 → 100 fast pass, 4 deselected slow), ruff + format check clean. Discharges rolling_log "first tool registered" trigger → `CLAUDE.md` gains a "Tool manifest" section between Models and Run/test/lint. architecture.md `agent/tools.py` filled in (no version bump — kept v0.4 since runner.py + prompts.py + R004 still TBD). interview_qa Q4 upgraded v0.1 → v1.0 with the `get_component("U999") → closest_matches` example. CLI wiring (`runner.py` + `prompts.py` + `messages.create(tools=...)` loop + Prompt Caching `cache_control`) is next-session work, deliberately deferred to keep this commit zero-conflict with parallel PG-backend work on `cli.py` / `relational.py` / `pyproject.toml`.
- 2026-05-13 — **Slice 4 closed**: `agent/prompts.py` + `agent/runner.py` + CLI `hardwise ask` command shipped. The `Runner` class drives the finite tool-use loop (`messages.create` with `tools=TOOL_DEFINITIONS` and `system=[{cache_control: ephemeral}]`), dispatches `tool_use` blocks to the four tools.py functions, feeds `tool_result` back, caps at 10 iterations, and accumulates per-iteration `input_tokens / output_tokens / cache_creation_input_tokens / cache_read_input_tokens` for audit. 8 fast tests added via a `FakeAnthropic` script-driven client (text-only / single tool / multi-tool-per-turn / unknown-refdes / no-collection / unknown-tool / iteration-cap / token-accumulation paths — no API key needed). Total fast suite: 105 baseline + 8 new = 113 pass, 7 deselected slow. Ruff + format check clean. **Live API verification on MiMo-V2.5 via `xiaomimimo.com/anthropic`** with three pic_programmer queries: (a) `U3 是什么器件？` → `get_component(U3) → found` → answer cites `7805 / TO-220 / l78.pdf` URL, tokens in/out 1635/240, cache create/read **0/1472**; (b) `U999 是什么器件？` → `get_component(U999) → not_found` → model honors anti-fabrication and answers "未找到" without inventing, tokens 129/171, cache **0/2944**; (c) `U4 这颗器件有几个 NC 脚？` → `get_nc_pins(refdes_filter=U4) → total=2` → tabular answer with FB-/S/S, tokens 196/154, cache **0/2944**. **Mechanism #5 (Prompt Caching) has measured numbers on MiMo, not just wiring.** Tool-use loop runs on MiMo with zero proxy-specific code — Anthropic-format compatibility extends to `tools=[...]` + `tool_use/tool_result` blocks. architecture.md → v0.5; Five Mechanisms × file map corrected (#4 router.py was mislabeled runner.py; #5 split across prompts.py + runner.py). interview_qa Q4 v1.0 → v4.0 with the 3-row live-evidence table. learning_log gains "MiMo proxy honors cache_control" entry. Slice 5 (R005 dangling-nets) and the planned R004 (I2C address conflict, needs cli.py dispatch refactor) remain.
- 2026-05-14 — Slice 5 prep · Sanitizer Layer 2 closed + DR-009 added. Sanitizer guard now sanitizes every user-visible egress (final assistant text on `RunResult.text`, plus `ToolCallTrace.input` and `output_summary` copies) while leaving the tool-fact channel — the `tool_result` JSON blocks sent back to the model — untouched. Added `sanitize_args(dict, registry)` helper + per-trace `wrapped` counter + `text_wrapped` field on `RunResult`; cli ask path dropped its redundant second-pass sanitize. New `tests/guards/test_refdes_egress.py` pins the asymmetric invariant (final text + trace wrapped; message-history `tool_result.content` must remain raw). DR-009 added immediately after DR-008: the Finding type is extended with two backward-compatible optional fields — `evidence_chain: list[EvidenceStep] = []` and `decision: Optional[Literal['likely_ok','likely_issue','reviewer_to_confirm']] = None` — without touching existing field semantics or replacing the Finding type. `status` stays the flow-state field (open/accepted/rejected/closed); `decision` is the rule-side judgment; the two are intentionally separated. R001/R002/R003 unchanged at this step — A3 will land `EvidenceStep` model + Finding extensions, A4 will be R003's first use of both new fields. Surprise of the day in learning_log: the existing `\b[A-Z]{1,3}\d{1,4}\b` regex over-wraps part numbers like `LM7805` — accepted as the documented Layer 2 trade-off (over-wrap is the safer side; semantic refdes vs part-number disambiguation belongs in Layer 1 via tool returns, not regex).
- 2026-05-16 — Prompt-cache cold-start follow-up: unique cacheable prompt against the configured MiMo proxy gave run 1 `input_tokens=5445, cache_creation_input_tokens=null, cache_read_input_tokens=null`; immediate run 2 `input_tokens=5, cache_creation_input_tokens=null, cache_read_input_tokens=5440`. This proves MiMo's read-hit path beyond the earlier warm-cache `ask` runs, but also proves the endpoint does **not** expose creation accounting. Strict `cache_creation_input_tokens` nonzero evidence needs a different Anthropic-format endpoint; direct Anthropic API could not be tested with the current MiMo proxy key (`401 invalid x-api-key`). README + interview_qa + learning_log updated to avoid claiming creation nonzero.
- 2026-05-26 — V2.8 Allegro+BOM report index shipped: `report-allegro-bom` keeps full component table mode, and adds prefix summary, BOM item groups, short source tokens, `--summary-only`, and `--mismatch-only`. Public Allegro+BOM smoke produced three consistent outputs: full 4209 lines, summary 194 lines, mismatch triage 27 lines; all reported `4010/4010 matched, 0 mismatches`. DR-010 records the staged path from intake index to datasheet match, pin profile, single-component validation, and Web UI while staying inside pre-Layout schematic review.
- 2026-05-26 — V2.9 datasheet/document match layer shipped: new `documents/` package parses local CSV/TSV document indexes and matches BOM item groups by MPN or part-like value into `matched / no_result / ambiguous / manual_needed` states. `report-allegro-bom --document-index` renders document summary and per-item document rows with `doc:<file>#line<N>` source tokens; `--document-index` is rejected with `--mismatch-only` because mismatch triage omits index sections. Synthetic fixture smoke proves one matched public-safe datasheet row without live supplier/PLM/lifecycle lookup.
- 2026-05-27 — V3.0 structured pin profile shipped: `DatasheetProfile` keeps old scalar fields and adds `pins[]` rows with pin number/name/category/function/limits/recommended_topology/evidence. Public L78 profile upgraded to schema v2 with VI/GND/VO pin rows. New `report-pin-profile` command writes a markdown pin-facts artifact and explicitly stops before schematic validation, PASS/FAIL judgement, supplier/PLM, or PCB work.
- 2026-05-27 — V3.3 XL1509 buck validation shipped: `data/datasheet_profiles/xl1509.json` adds public structured XL1509-12E1 facts and DCDC recommended limits; `validation/pins.py`, `validation/dcdc.py`, and `validation/types.py` split generic pin checks from component-level buck topology checks. The synthetic Allegro+BOM fixture `xl1509_buck.net` + `xl1509_buck_bom.csv` validates `U12` and reports overall `ERROR` for `D5=1N4007W` freewheel diode and `L1=6.8uH` inductor below the profile range, while nominal Schottky + in-range inductor returns no ERROR. Markdown/UI reports now render component checks without changing the single-selected-component UI contract or crossing into `.brd`, boardview, placement, routing, PCB geometry, live supplier lookup, PLM, lifecycle, pricing, or availability.
- 2026-05-27 — V3.4 multi-validation UI shipped: `report-validator-ui-batch <netlist_or_pst> <bom> REFDES=profile.json [...]` renders multiple explicit component/profile validations into one static HTML artifact. The mixed synthetic fixture validates `U1=L7805` as PASS and `U12=XL1509-12E1` as ERROR in the same component index/detail UI, with per-component markdown downloads and schematic-net/scope panes. The command still requires explicit profile assignment and does not auto-profile every component, host an app, parse `.brd`/boardview/PCB geometry, or add supplier/PLM/lifecycle/pricing scope.
- 2026-05-27 — V3.5 validation targets manifest shipped: `report-validator-ui-batch` now accepts `--targets-manifest tests/fixtures/allegro/mixed_regulators_targets.yaml` as the reusable equivalent of positional `U1=data/datasheet_profiles/l78.json U12=data/datasheet_profiles/xl1509.json`. The manifest parser uppercases refdes values, rejects duplicates and malformed target rows, keeps profile paths current-working-directory relative, and refuses mixed positional+manifest input. It preserves explicit profile assignment only; no BOM-wide profile matching, supplier/PLM scope, hosted app state, `.brd`, boardview, placement, routing, or PCB geometry is added.
- 2026-05-27 — V3.6 profile candidate manifest shipped: `suggest-validation-targets <bom> --profiles data/datasheet_profiles` scans a schematic BOM and local structured profiles, then writes a YAML candidate manifest with `matched / no_result / ambiguous / manual_needed` rows. Matching is normalized exact identity matching: BOM MPN first, part-like value second, against profile `part_number`. `--matched-only` emits the V3.5 minimal `project + targets[]` manifest shape for matched rows. It does not run validation, auto-accept targets, fetch datasheets, infer missing profiles, or add supplier/PLM/PCB scope.
- 2026-05-27 — V3.7 product-like validator UI polish shipped: `report-validator-ui-batch` now renders the same multi-component validation truth as a three-column static workbench with project summary, filterable component index, validation cards, issue-first detail panels, Chinese report sections, pin summary cards, component-check cards, schematic connections, scope boundary, and per-component markdown downloads. The mixed fixture opens on `U12 ERROR` and surfaces `D5=1N4007W` plus `L1=6.8 uH` without changing validation logic. It adds no new validation families, hosted app state, automatic validation, supplier/PLM scope, `.brd`, boardview, placement, routing, or PCB geometry.
- 2026-05-27 — V3.8 EG2132 gate-driver validation shipped: `data/datasheet_profiles/eg2132.json` adds public structured EG2132 pin facts and half-bridge driver recommendations; `validation/gate_driver.py` adds component-level checks for VCC, HIN/LIN, HO/LO gate loads, VS switch node, and VB/VS bootstrap topology. The synthetic Allegro+BOM fixture `eg2132_gate_driver.net` + `eg2132_gate_driver_bom.csv` validates `U3` and reports overall `ERROR` for `D1=MBRA210LT3G` as a low-reverse-voltage bootstrap diode in a 24 V-class path, while nominal diode/load variants return no component ERROR. It adds no MCU/LED/transistor template, timing/deadtime simulation, MOSFET loss calculation, hosted app state, supplier/PLM scope, `.brd`, boardview, placement, routing, or PCB geometry.
- 2026-05-28 — Design-validator workbench entry shipped: `design-validator-ui <netlist_or_pst> <bom>` auto-matches BOM identities against local structured profiles, runs deterministic validation for matched components, writes the screenshot-like static workbench HTML, and optionally writes markdown/JSON project validation index sidecars. It keeps `report-validator-ui-batch` for explicit target control, but gives the product demo a one-command project-level entry. It remains a local static artifact: no upload backend, account quota, hosted app state, `.brd`, boardview, placement, routing, PCB geometry, live supplier lookup, PLM, lifecycle, pricing, or availability.
- 2026-05-28 — V3.10 STM32G030 MCU/SWD validation shipped: `data/datasheet_profiles/stm32g030c8t6.json` adds a public structured MCU fixture subset, and `validation/mcu.py` adds component-level checks for VDD/VDDA/VBAT, NRST, BOOT0, SWDIO/SWCLK, and simple GPIO connectivity. The synthetic `stm32g030_mcu` fixture validates `U8` and reports overall `ERROR` for swapped `SWDIO/SWCLK`; the mixed controller power-stage fixture lets `design-validator-ui` show `U1 PASS`, `U12 ERROR`, `U3 ERROR`, and `U8 ERROR` in one workbench. It adds no firmware, clock-tree, full alternate-function matrix, timing, PCB/layout, supplier/PLM, `.brd`, boardview, placement, routing, or PCB geometry scope.
- 2026-05-28 — V3.11 zero-profile coverage workbench shipped: `design-validator-ui` now succeeds even when profile candidate matching produces zero validated rows. It renders a coverage/gap HTML artifact, writes markdown/JSON index sidecars, reports `validated=0` with PASS/WARN/ERROR all zero, and surfaces `no_result / ambiguous / manual_needed` rows without fabricating electrical judgement. It adds no new profiles, validation families, parsers, datasheet search, supplier/PLM scope, or PCB/layout scope.
- 2026-05-29 — Validator-family migration (codex mainline trunk): diode + connector families (`ae04a51`), redundant MPN dispatch fallbacks removed so dispatch is uniformly `topology_family`-driven (`d318419`), and MOSFET family with gate-to-source Vgs (`b0de983`). MOSFET fix: `Vgs = V_gate − V_source` (not gate-to-ground), profile Source recategorised `switch_node`, WARN instead of assuming ground when the reference floats; see `docs/learning_log.md` 2026-05-29. DR-011 added: post-migration priority is the agent↔validator bridge (Phase 1) and real datasheet evidence chain (Phase 2), ranked above adding more families. `uv run pytest -q` → 373 passed; `uv run ruff check .` → clean.
