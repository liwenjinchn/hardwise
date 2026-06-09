# Hardwise 进化叙事研究稿

> 用途：面试、简历项目讲述、公开复盘文章的母稿。
> 这份文档讲“我是怎么一步一步走到现在”，不是新的产品路线图。

## 一句话定位

Hardwise 是一个 Vibe Coding 自学者把 5 年硬件评审经验压缩成可信 AI workflow 的过程：先做一个能跑的 KiCad 原理图规则 Agent，再把它进化成能消费 Allegro netlist+BOM、带证据分层和 Copilot trace 的 pre-Layout schematic-review workbench，最后开始走向更产品化的前端/SaaS 方向。

更短的面试收尾：

> 在让模型评审一块板子之前，先让它在结构上不能发明这块板子。

## 证据来源

这份叙事只使用四条可交叉验证的证据线：

- Git 时间线：`git log --all`、`origin/main`、tag `demo-video`、各 `codex/*` 分支的提交主题。
- 公开阅读面：GitHub repo、GitHub Pages 入口、README、demo 页面。
- 仓库决策文档：`docs/PLAN.md`、`docs/mvp_definition.md`、`docs/demo.md`、`docs/evidence_chain_audit.md`、`docs/interview_qa.md`、`docs/learning_log.md`。
- 本地 Codex 摘要层：只用概括后的思考轨迹，不引用原始 JSONL，不外发本地路径、工具提示、密钥风险或私人上下文。

对外材料的底线是：不使用公司内部硬件数据，不复制 Wrench Board 代码，不把 eval smoke 包装成专家准确率，不把尚未完成的前端/SaaS 方向说成已经上线。

## 8 阶段时间线

| 阶段 | 时间 | 代表提交/材料 | 应用进化 | 开发者进化 | 对外一句话 |
|---|---|---|---|---|---|
| 1. KiCad MVP 起步 | 2026-05-11 | `72ca609 feat: initial commit`; `afd6025 feat(r002)`; `f629c62 feat(agent)` | 从公开 KiCad 项目读入，跑 R001/R002，生成最小 markdown review。 | 学会先做 vertical slice：规则、finding、报告、测试先闭环。 | “我没有先做大平台，而是先证明一个硬件 Agent 可以只围绕真实 registry 说话。” |
| 2. 工具化 Agent 与证据链 | 2026-05-12 至 2026-05-14 | `522cbee feat(store)`; `4757946 feat(agent)`; `416506a feat(R003)`; `75d60cc fix(guards)` | SQLite/Chroma/PDF ingest、tool-use loop、cache prompt、R003 NC pin 证据链、出站 refdes sanitizer 成型。 | 从“让模型回答”转向“让模型调用结构化工具，并接受 unknown”。 | “Hardwise 开始不是让模型判断硬件，而是让模型解释工具能证明的事实。” |
| 3. 可审计 MVP 硬化 | 2026-05-15 至 2026-05-17 | `63119bd refactor(adapters)`; `65bb3f5 feat(trace)`; `572792c feat(eval)`; `78c3c20 fix(r003)` | 明确 pre-Layout 边界，加入 run ledger、public corpus eval、part-matched datasheet evidence。 | 开始用边界和验证保护项目，而不是继续堆功能。 | “项目开始回答面试里最难的问题：怎么证明没胡说、没退化、没越界？” |
| 4. V2 IR 与 Allegro 企业格式入口 | 2026-05-25 至 2026-05-26 | `2021bac docs(spec)`; `7b34b30 feat(ir)`; `af74364 feat(adapters)`; `b5857dd feat(bom)`; `e58d717 feat(documents)` | 从 rule-driven KiCad demo 转到 component-centric IR，新增 Allegro schematic netlist/PST、BOM join、datasheet matching。 | 认识到岗位/企业场景不只看 KiCad，必须把抽象层做出来。 | “Hardwise 从开源 KiCad demo 转成能接企业原理图格式和 BOM 的 review engine。” |
| 5. 批量验证台与 profile coverage | 2026-05-27 至 2026-05-29 | `a69c1c4 feat(report)`; `c53d0d0 feat(report)`; `be21654 feat(validation)`; `029ce67 feat(agent)` | 单器件/多器件 validation UI、family validators、targets manifest、agent 到 deterministic validator 的 bridge。 | 从“写一条规则”进化到“建立覆盖 gap 队列，一族一族推进”。 | “它不再只是出一次报告，而是能把 manual gap 排队，逐步转成确定性检查。” |
| 6. Allegro Copilot 工作台与 trust 分层 | 2026-05-30 至 2026-06-05 | `7d3ba1b feat(workbench)`; `58cf87f fix(workbench)`; `2bf07e1 feat(agent)`; `c1171ce feat(report)`; `611c16f test(agent)` | 离线 snapshot / live server Copilot panel、evidence-first UI、L1/L2/L3 trust tier、six-section validation detail。 | 学会把“技术机制”翻译成 reviewer 能扫读、能追证据、能开会讨论的产品表面。 | “产品核心从命令行 Agent 变成 reviewer 可追证据、可问 Copilot 的工作台。” |
| 7. 公开 demo closeout | 2026-06-06 | `4c8c51e merge closeout workbench scope`; tag `demo-video`; `e933746 fix(report)`; `537a450 feat(validation)`; `12cb7fb feat(validation)` | README、GitHub Pages、demo 视频、工作台 UI、pressure-test summary 一起收口。 | 从“我做了很多功能”转成“90 秒可讲清楚的作品”。 | “这一步把工程能力包装成能被面试官快速理解的公开作品。” |
| 8. Risk hints / 前端产品化支线 | 2026-06-08 | `21e467f feat(evidence)`; `c9f1aab feat(validation)`; `026d3cb feat(validation)`; `3435208 feat(validation)`; `958d701 feat(workbench)` | evidence source class、更多 family profiles、external risk hints contract、workbench risk hints 渲染入口。 | 开始从 demo workbench 想到产品接口和前端封装，但仍保持“未完成 SaaS”的诚实口径。 | “Hardwise 开始走向可接外部风险信号、可前端化封装的产品界面。” |

## 主叙事

### 起点：不是“AI 评审硬件”，而是“AI 不能编硬件对象”

最早的 Hardwise 很小：公开 KiCad 项目、几个 schematic-review 规则、markdown 报告。这个版本的价值不是功能强，而是方向对：硬件评审里最危险的不是模型措辞不专业，而是它把不存在的位号、pin、datasheet 事实讲得像真的。

所以第一个核心约束是 `Refdes Guard`：用户可见的 refdes 必须来自 EDA registry。第二个约束是 `Evidence Ledger`：finding 必须带 `sch:<file>#<refdes>`、`datasheet:<pdf>#p<N>` 或 `rule:<id>` 这样的 source token。这个选择让项目一开始就不是普通聊天机器人，而是证据型硬件 Agent。

### 第一次转折：从规则脚本到 tool-use loop

第二阶段的关键不是多加一条规则，而是建立工具合约：`list_components`、`get_component`、`get_nc_pins`、`search_datasheet`、`run_component_validation` 这类工具必须返回结构化结果。找不到就返回 `found=false`、`not_configured` 或 `no_profile`，而不是让模型自由补全。

这时 Hardwise 的气质变了：模型不再是事实来源，工具才是事实来源。模型的角色是解释、组织、追问和把证据变成人能读懂的报告。

### 第二次转折：边界比功能更重要

2026-05-15 到 2026-05-17，项目开始做“可信度硬化”：pre-Layout 边界、run ledger、public corpus eval、part-matched datasheet evidence。这个阶段的学习点是，AI 硬件项目如果没有边界，越做越容易虚。

例如 eval pack 只能说是 regression / guardrail smoke，不能说专家准确率。L78 可以说是 live retrieval，因为它跑过 `ingest -> retrieve -> agent citation`；其它 profile token 只能说是 reviewed public profile evidence，不能混成 live RAG。

### 第三次转折：从 KiCad sample 到企业级输入形态

V2 的核心不只是“支持 Allegro”，而是把项目从 rule-driven report 转成 component-centric IR。真实 review 不是按 R001/R002/R003 看问题，而是围绕一个器件看：它是谁、pin 怎么连、BOM identity 是什么、datasheet/profile 有没有、validator 结论是什么。

Allegro netlist/PST + BOM 的入口让 Hardwise 更接近企业原理图评审场景，但仍然不碰 `.brd`、boardview、routing、PLM 或 supplier pricing。这个阶段最重要的表达是：它消费的是原理图导出的 netlist/BOM artifact，不是假装自己是实时 Cadence 插件。

### 第四次转折：从报告到工作台

当 validation UI、family validators、Copilot panel、L1/L2/L3 trust tier 接起来后，Hardwise 的产品形态出现了：不是一份模型写的长报告，而是一个 reviewer workbench。

工作台先回答工程师最想知道的问题：

- 哪些是 Must Review？
- 哪些只是 Manual Gap？
- 哪些已经 deterministic PASS？
- 每条结论背后是哪一个 source token？
- Copilot 调用了什么工具，能不能追 trace？

这也是开发方式的进化：从“代码能跑”到“别人愿意看、看得懂、能追证据”。

### 第五次转折：把作品收成公开 demo

2026-06-06 的 closeout 把项目收成了 90 秒 demo：`design-validator-ui --ai-snapshot` 生成离线 Copilot workbench，公开入口有 GitHub Pages、demo 视频、README、recording script。

公开 demo 的当前口径是 25 components、22 validated rows、BOM matched=25、PASS/WARN/ERROR=5/13/4、3 manual rows。这里要特别说明：22 个 L1 rows 里，9 个是 profile-backed targets（U1/U12/U3/U8、D1/D5、Q1/Q2/Q12），13 个是 generic passive checks。generic passive 是 light deterministic coverage，不等于深度 datasheet review。

### 当前方向：前端化和 SaaS 产品化，但不夸大

2026-06-08 的 risk hints / evidence class / family profile 分支说明项目开始考虑更产品化的输入和展示层。可以说它正在走向“更像 SaaS 产品的前端工作台”，但不能说已经具备完整 SaaS 能力。账号、多租户、部署、计费、团队协作都还不属于当前已落地范围。

## 面试可讲版本

### 30 秒版本

我做 Hardwise 不是为了证明大模型可以独立评审一整块板，而是为了证明一个更窄但更可靠的硬件 AI workflow。

我把节点收窄到 pre-Layout schematic review：导入公开 KiCad 或 Allegro netlist+BOM，建立 registry-verified component table，跑 deterministic validators，再让 Copilot 解释工具返回的事实。未知 refdes 例如 `U999` 必须通过 `get_component` 返回 miss，显示层会包成 `⟨?U999⟩`。所以项目的核心不是“AI 多聪明”，而是“模型在结构上不能发明这块板子”。

### 2 分钟版本

Hardwise 的起点是我作为硬件工程师对原理图评审的观察：评审最耗时的地方不是单点判断，而是在 SCH、BOM/netlist、datasheet、checklist、证据 notes 和 feedback rows 之间来回切换。

一开始我只做了一个很简陋的 KiCad Agent：公开项目、几条规则、markdown 报告。但我很快意识到，硬件 AI 的第一原则不是 prompt 写得多好，而是模型不能编 refdes、pin 和 datasheet 参数。所以我加了两层约束：Refdes Guard 负责挡住未验证位号，Evidence Ledger 要求每条 finding 都有 source token。

后来我把它从规则脚本推进到 tool-use loop：SQLite 存 registry，Chroma 存 datasheet chunks，工具返回 structured miss，模型只能解释工具事实。再往后，我发现 KiCad 只是公开复现入口，企业场景更接近 Allegro netlist/PST+BOM，所以做了 component-centric IR、Allegro parser、BOM join、datasheet profile matching。

真正形成产品感的是 workbench 阶段：它不再只是命令行输出，而是 reviewer 打开就能看到 Must Review、Manual Gap、Passed、evidence token 和 Copilot trace。当前公开 demo 是一个离线 Copilot workbench，核心卖点是 trust architecture：L1 deterministic validator 决定 PASS/WARN/ERROR，L2 只表示有页码级 datasheet retrieval，L3 明确留给人工 review。

所以这个项目展示的是我的两条进化线：应用从 KiCad 小脚本进化成企业输入形态的硬件评审工作台；我自己也从 Vibe Coding 的功能堆叠，进化到会收边界、做证据、做可演示产品。

### 5 分钟深挖版

如果展开讲，我会按三条线讲。

第一条是工程对象可信。Hardwise 的 `Refdes Guard` 会 regex 扫描用户可见文本里的 refdes-shaped token，再到 parsed-board registry 里核验。不存在的 `U999` 不会被模型包装成真实器件，而是显示成 `⟨?U999⟩`。这解决的是硬件 Agent 最危险的一类幻觉：发明工程对象。

第二条是证据可信。每条 hard finding 必须有 evidence token。L78 是最完整的 smoke：PDF ingest、vector retrieval、agent citation，能落到 `datasheet:l78.pdf#p4`。我不会把所有 profile token 都说成 live retrieval；其它没有跑过实时检索的，只能称为 reviewed public profile evidence。

第三条是产品可信。早期 CLI 能证明架构，但不适合 reviewer 使用。后期 workbench 把输出改成 Must Review / Manual Gap / Passed，把 deterministic validator、profile evidence、topology context、Copilot tool trace 放在同一个界面里。`--ai-snapshot` 可以生成离线 HTML，不需要 API key；`serve-workbench --fake-ai` 也仍然跑真实 Runner 和真实工具，只是 fake client 负责发 tool_use/text。

最后我会强调边界：Hardwise 不是 PCB layout review，不碰 `.brd`、routing、PLM、价格库存，也不使用公司内部硬件数据。它是一个 portfolio MVP，证明一个窄但硬的闭环：AI 进入硬件 review 前，必须先被 registry、tools、evidence 和 deterministic validators 约束住。

## 技术可信度证据

| 证据点 | 怎么讲 | 不要怎么讲 |
|---|---|---|
| Refdes Guard | 用户可见 refdes 必须来自 parsed EDA registry。 | 不说模型“自然不会编位号”。 |
| `U999` | unknown refdes 走 `found=false` / closest matches / `⟨?U999⟩`。 | 不把它讲成普通字符串替换小技巧。 |
| Evidence Ledger | hard finding 必须有 source token。 | 不说每句话都有完整形式化证明。 |
| L1/L2/L3 | L1 是 deterministic validator，L2 是页码级 retrieval，L3 是 manual gap。 | 不让 L2 覆盖 L1，不把 L3 包装成失败。 |
| L78 smoke | `ingest -> retrieve -> ask --vector` 的完整证据链。 | 不说所有 datasheet profile 都经过 live RAG。 |
| Allegro Copilot | 通过 `Design -> BoardRegistry` shim 接入 Runner，fake-ai 不绕过工具和 guard。 | 不说这是实时 Cadence/Allegro 插件。 |
| Eval pack | regression / guardrail harness，防止 parser、guard、evidence 退化。 | 不说专家级准确率 benchmark。 |

## 面试追问备答

**为什么不直接做完整硬件评审平台？**

硬件 AI 的风险不是功能少，而是信任边界不清。一个能自由编造工程对象的大平台，可信度反而不如一个窄但诚实的闭环。Hardwise 先证明 pre-Layout schematic review 这一格：registry、evidence、deterministic validator 和 Copilot trace 都能闭环。

**为什么先 KiCad，后来又做 Allegro？**

KiCad 是公开可复现的 MVP 入口，适合证明架构和写 tests；Allegro netlist/PST+BOM 更接近企业原理图评审的输入形态。V2 的真正变化不是多一个 parser，而是抽出 component-centric IR，让不同 EDA 输入都落到同一套 review workflow。

**你自己在这个项目里学到了什么？**

我一开始更关心“能不能让 AI 做事”，后来变成“能不能让 AI 只在可信边界里做事”。这个变化反映在代码里：structured miss、evidence token、L1/L2/L3、manual gap、public-only data、demo closeout。它不是一次性写出来的，是每一轮验证和复盘逼出来的。

**这和 Wrench Board 的关系是什么？**

Wrench Board 是架构灵感，不是代码来源。Hardwise 借鉴的是 anti-hallucination、tool discipline、sanitizer、evidence-minded UI 这些设计思想；代码、数据和 demo 都是独立实现，并且只使用公开硬件项目和公开 datasheet。

**下一步如果继续产品化，做什么？**

先把前端工作台做成更自然的 review surface：risk hints 输入、器件组覆盖、trace-backed rules list、可复现 smoke flow。再考虑 hosted shell、上传体验和团队协作。账号、多租户、计费这些是更后面的 SaaS 能力，现在不能提前宣称。

## 外发红线

- 不说 Hardwise 已经能完整自动评审整板。
- 不说每个 profile 都是 live retrieval。
- 不说 eval pack 证明专家准确率。
- 不说已经是实时 Cadence/Allegro 插件。
- 不说已经完成完整 SaaS。
- 不暴露原始 Codex 会话、API key、`.env`、本地绝对路径或任何公司内部硬件数据。
