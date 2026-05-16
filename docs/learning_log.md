# Hardwise Learning Log

> Every issue debugged is a unit of internalized knowledge. This file is not a complaint board — it's the journal of "what surprised me when reality didn't match my mental model."
>
> Format per entry: **Symptom** / **Root cause** / **Fix** / **Takeaway**. Add a HW analogy in root cause when it actually clarifies; don't force one.
>
> Interview hook: "what surprised you while building this?" → entries here are the honest answer.

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

Full public-corpus smoke (`eval/manifest.yaml`, 5 repos / 16 discovered KiCad project
directories) passed structurally: 1707 components parsed, 231 NC pins, 437 findings,
`unverified_refdes_wrapped=0`, `findings_dropped_no_evidence=0`.

**Takeaway**

This is exactly what the eval harness should do: expose a real integration boundary, not
just print a bigger-looking score. Guardrail metrics need examples attached, otherwise
they are not actionable for engineering review.

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
