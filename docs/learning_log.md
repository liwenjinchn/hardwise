# Hardwise Learning Log

> Every issue debugged is a unit of internalized knowledge. This file is not a complaint board — it's the journal of "what surprised me when reality didn't match my mental model."
>
> Format per entry: **Symptom** / **Root cause** / **Fix** / **Takeaway**. Add a HW analogy in root cause when it actually clarifies; don't force one.
>
> Interview hook: "what surprised you while building this?" → entries here are the honest answer.

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

`cache_create=0` 是因为 cache 已被更早的会话写热（不是没命中，是命中**别人**写的）。第二、三次 `cache_read=2944` ≈ 2×1472 是两次迭代各命中一次系统 prompt cache。**Mechanism #5 在 MiMo 上有真数字，不是 wiring-only。**

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
