# Hardwise 传播稿包

> 用途：把 `hardwise_evolution_narrative.md` 改写成小红书、LinuxDo、面试口播等不同场景的可用素材。
> 所有版本都保持同一条底线：Hardwise 是可信 pre-Layout schematic-review workbench，不是“LLM 自动评审整板”。

## 标题候选

求职向：

- 我用 Vibe Coding 做了一个硬件原理图评审 AI Agent
- 从 KiCad 小脚本到 Allegro 工作台：我的硬件 AI 项目复盘
- 一个硬件工程师如何把评审经验做成 AI workbench

技术向：

- 一个硬件 Agent 项目的 30 天演进：Refdes Guard、Evidence Ledger 和 Allegro workbench
- 不让模型发明位号：我做 Hardwise 时真正解决的问题
- 从 rule-driven report 到 component-centric review workbench

自学成长向：

- 零代码背景做硬件 AI 项目，我真正学到的是“收边界”
- Vibe Coding 不是让 AI 乱写代码，而是逼自己学会验证
- 我如何从“想做 AI 工具”走到“做可信 workflow”

产品化向：

- 一个硬件 AI demo 如何长成 reviewer workbench
- AI Copilot 不是裁判：它应该解释工具证明过的事实
- 从 demo 到产品感：Hardwise 的工作台化路径

## 小红书图文脚本

### 封面标题

我用 Vibe Coding 做了一个硬件原理图评审 AI 工作台

副标题：

从 KiCad 小 Agent，到 Allegro netlist+BOM workbench，再到前端/SaaS 产品化方向。

### 卡 1：起点不是“AI 替代硬件工程师”

我一开始想做的是硬件 review Agent，但后来发现最危险的问题不是模型说得不够专业，而是它可能把不存在的位号、pin、datasheet 参数说得像真的。

所以 Hardwise 的第一原则是：

> 模型不能自由发明板子上的工程对象。

### 卡 2：第一个版本很简陋，但方向是对的

最早只支持公开 KiCad 项目：

- 读原理图
- 跑几条 checklist rule
- 输出 markdown review
- 每条 finding 带 source token

它不好看，也不“产品化”，但已经有一个关键骨架：refdes 必须来自 EDA registry。

### 卡 3：我学会的第一件事：unknown 要变成一等结果

硬件 AI 不能把“不知道”藏起来。

比如用户问 `U999`，系统必须查 registry。如果没有这个位号，就返回 structured miss，再在显示层包成 `⟨?U999⟩`。

这比模型回答得漂亮更重要，因为硬件评审里，一个不存在的位号可能会把后续判断全部带歪。

### 卡 4：从 KiCad 到 Allegro，是一次真正的升级

KiCad 适合公开复现，但企业原理图评审更接近 netlist/PST+BOM 这种输入形态。

所以我做了 V2：

- component-centric IR
- Allegro schematic netlist parser
- BOM join
- datasheet/profile matching
- 单器件和多器件 validation UI

这一步让项目从“开源样例 demo”变成更接近真实硬件评审流程的 engine。

### 卡 5：真正产品化的转折是 workbench

命令行能证明技术，但 reviewer 不会喜欢只看长日志。

后期我把它做成 workbench：

- Must Review
- Manual Gap
- Passed
- evidence token
- Copilot tool trace
- L1/L2/L3 trust tier

Copilot 不负责替你判定硬件对错，它负责解释工具已经证明过的事实。

### 卡 6：我自己也在进化

这个项目最大的变化不是代码量，而是我的思维方式变了：

- 从追功能，到收边界
- 从 prompt，到工具合约
- 从“AI 能不能做”，到“AI 凭什么可信”
- 从命令行 demo，到面试能讲清楚的产品

Vibe Coding 真正训练我的，不是偷懒写代码，而是每一步都要问：输入是什么、输出是什么、怎么验证、哪里不能夸大。

### 卡 7：现在它做到什么程度？

当前公开 demo 是一个离线 Copilot workbench：

- 25 components
- 22 validated rows
- BOM matched = 25
- PASS/WARN/ERROR = 5/13/4
- 3 manual rows

注意：这不是“整板专家自动评审”。它证明的是一个可信闭环：registry、evidence、deterministic validator、Copilot trace 都能接起来。

### 卡 8：一句话总结

Hardwise 的核心不是让模型变成硬件专家。

它的核心是：

> 在让模型评审一块板子之前，先让它在结构上不能发明这块板子。

## 小红书正文草稿

我最近把自己的硬件 AI 项目 Hardwise 梳理了一遍，发现它其实也是我 Vibe Coding 自学过程的一条时间线。

一开始它只是一个很简陋的 KiCad 原理图 Agent：读公开原理图，跑几条 checklist rule，输出 markdown report。后来我逐渐意识到，硬件 AI 里最危险的问题不是模型说错一句话，而是它把不存在的工程对象说得像真的。

所以我给它加了 Refdes Guard 和 Evidence Ledger：位号必须来自 EDA registry，finding 必须带 source token。再后来，它从 KiCad demo 进化到 component-centric IR，能消费 Allegro netlist/PST+BOM，也能做 datasheet/profile matching。最后才变成现在这个 reviewer workbench：Must Review、Manual Gap、Passed、Copilot trace、L1/L2/L3 trust tier。

这个项目对我最大的意义，是让我从“想让 AI 帮我做东西”，变成“我得知道 AI 在什么边界里才可信”。Vibe Coding 不是让模型乱写代码，而是把需求、边界、验证、复盘逼得更具体。

Hardwise 还不是完整 SaaS，也不是自动硬件专家。它现在证明的是一个窄但诚实的闭环：让 AI 进入硬件评审之前，先让它不能发明这块板子。

## LinuxDo 技术帖草稿

### 标题

一个硬件 Agent 项目的 30 天演进：从 KiCad 规则脚本到 Allegro Copilot workbench

### 开头

这篇不是宣传“LLM 自动评审硬件”。我做 Hardwise 的结论几乎相反：硬件 Agent 的第一步不是让模型更会判断，而是让模型在结构上不能发明工程对象。

项目地址可以从 GitHub repo 和 GitHub Pages demo 看。这里主要复盘演进过程，以及一个 Vibe Coding 自学者在这个项目里怎么被迫建立工程纪律。

### 时间线

1. 2026-05-11：KiCad MVP

最早的 commit 是 `72ca609 feat: initial commit`。当时只做公开 KiCad 项目、R001/R002 规则、markdown review。这个版本很小，但已经开始坚持两件事：refdes 从 registry 来，finding 要带 source token。

2. 2026-05-12 至 2026-05-14：工具化 Agent

`522cbee` 加 SQLite/Chroma/PDF ingest，`4757946` 加 tool-use loop，`416506a` 把 R003 NC pin 接上 EDA + datasheet evidence chain，`75d60cc` 修正 sanitizer，让用户可见输出被保护，但工具事实通道不被污染。

这个阶段的关键是 structured miss：找不到就是 `found=false`，没有向量库就是 `not_configured`，没有 profile 就是 `no_profile`。工具不编，模型也不能编。

3. 2026-05-15 至 2026-05-17：MVP 硬化

项目开始做 run ledger、public corpus eval、part-matched datasheet evidence。这里最重要的不是加功能，而是防止叙事失真：eval 是 regression / guardrail，不是专家准确率；L78 是 live retrieval，其它 profile token 不自动等于 live RAG。

4. 2026-05-25 至 2026-05-26：V2 IR 和 Allegro 入口

`2021bac` 落 V2 component-centric spec，`7b34b30` 加 IR aggregator，`af74364` 解析 Allegro schematic netlist，`b5857dd` 做 BOM matching，`e58d717` 做 datasheet document matching。

这一步解决的是平台错配：KiCad 适合公开 demo，但企业场景常见的是 Allegro/PST/netlist+BOM artifact。Hardwise 不碰 `.brd` 和 layout，只保持在 pre-Layout schematic review 节点。

5. 2026-05-27 至 2026-05-29：validation workbench 和 family coverage

这一阶段出现 single/multi validation UI、family validators、profile target manifest，以及 `029ce67 feat(agent): bridge the review loop to family validators`。这让 agent 不只是回答 component context，也能调用 deterministic validator。

6. 2026-05-30 至 2026-06-05：Allegro Copilot workbench

`7d3ba1b` 加 Copilot panel，`58cf87f` fail-closed snapshot fallback，`2bf07e1` surface grounded datasheet trace evidence，`c1171ce` 加 six-section validation panel，`611c16f` 锁定 L2 不能覆盖 L1。

这时 Hardwise 的产品语言变成 L1/L2/L3：

- L1 deterministic：Python rule / validator 决定 PASS/WARN/ERROR。
- L2 grounded：本轮有页码级 datasheet retrieval evidence。
- L3 manual：没有 ready profile、没有 retrieval evidence 或上下文不足。

7. 2026-06-06：公开 demo closeout

`4c8c51e` 合并 closeout，tag `demo-video`。主 demo 变成 `design-validator-ui --ai-snapshot` 离线 workbench。这个版本不需要 server 或 API key，也不是实时 EDA 插件，而是一个可复现的 reviewer workbench。

8. 2026-06-08：产品化支线

后续分支开始做 evidence source class、diode/transistor family profiles、external risk hints contract、workbench risk hints render。这是前端/SaaS 产品化方向，但还不能说已经是完整 SaaS。

### 设计教训

第一，硬件 AI 的 unknown path 要一开始就设计。没有 `found=false`，模型就会倾向于补全。

第二，证据分层比“覆盖率”更重要。generic passive coverage 只能叫 light deterministic coverage，不能冒充深度 datasheet review。

第三，demo 要从用户工作流讲，不要从架构讲。Reviewer 先关心 Must Review / Manual Gap / Passed，不关心你底层用了几个模块。

第四，Vibe Coding 的核心不是快，而是复盘快。每次模型写完，都要回到测试、lint、learning log、interview QA、demo 口径。

### 结论

Hardwise 现在最有价值的不是“功能已经多完整”，而是它证明了一条可信路径：让模型进入硬件评审之前，先用 registry、tools、evidence 和 deterministic validators 把它约束住。

## 面试口播包

### 30 秒

Hardwise 是我用 Vibe Coding 做的硬件 AI portfolio MVP。它不证明 LLM 能独立评审整板，而是证明一个更窄的 pre-Layout schematic review workflow：导入公开 KiCad 或 Allegro netlist+BOM，建立 registry-verified component table，跑 deterministic validators，再让 Copilot 解释工具事实。未知位号比如 `U999` 会被工具返回 miss，并在显示层包成 `⟨?U999⟩`。核心是让模型在结构上不能发明这块板子。

### 2 分钟

我做 Hardwise 的背景是硬件评审里一个很实际的问题：评审人要在 SCH、BOM/netlist、datasheet、checklist 和反馈表之间来回切换。AI 如果直接自由回答，最危险的是编出看起来真实的位号或 datasheet 参数。

所以我从一个很小的 KiCad MVP 开始，先跑几条规则和 markdown report。接着加 Refdes Guard、Evidence Ledger、SQLite/Chroma、PDF ingest 和 tool-use loop，让模型只能通过结构化工具拿事实。后面我把它升级成 component-centric IR，支持 Allegro schematic netlist/PST+BOM，接上 deterministic family validators。

最后形成的是一个 workbench：左边是 Must Review、Manual Gap、Passed，右边是 component detail、evidence token 和 Copilot trace。L1 是 deterministic validator，L2 是有页码级 retrieval evidence 的 grounded answer，L3 是 manual gap。它现在不是完整 SaaS，也不是自动专家评审，但已经是一个可信、可演示、可解释的硬件 AI review workflow。

### STAR 项目经历

Situation：

硬件原理图评审需要跨 schematic、BOM、datasheet、checklist 和反馈表反复确认。LLM 如果自由回答，容易发明不存在的 refdes 或规格参数，风险比普通文本错误更高。

Task：

做一个两周 MVP，证明 AI 可以进入 pre-Layout schematic review，但必须被 registry、tools、evidence 和 deterministic validators 约束。

Action：

我先用公开 KiCad 项目做 vertical slice，再加入 Refdes Guard、Evidence Ledger、SQLite/Chroma、PDF ingest、tool-use loop。随后抽 component-centric IR，支持 Allegro netlist+BOM，接入 family validators，最后做成离线 Copilot workbench。

Result：

当前公开 demo 能生成 25 components / 22 validated rows / PASS-WARN-ERROR=5/13/4 / 3 manual rows 的 workbench。未知 refdes 会被包成 `⟨?U999⟩`，L78 能展示 `ingest -> retrieve -> agent citation` 的 page-level evidence。项目从命令行 demo 收成了可用于面试和公开展示的硬件 AI 工作台。

## 被追问时的红线回答

**这是不是已经能替代硬件工程师？**

不是。它只覆盖 pre-Layout schematic review 的可信辅助链路。判断仍然归 reviewer，Hardwise 负责整理 registry、evidence、deterministic findings 和 manual gaps。

**是不是所有 datasheet 证据都来自 RAG？**

不是。L78 是完整 live retrieval smoke；其它 profile token 主要是 reviewed public profile evidence。对外不能混讲。

**是不是已经是 SaaS？**

不是。当前是本地/离线 workbench 和前端产品化支线。可以说它在往 SaaS-like product surface 走，但账号、多租户、计费、团队协作都还没完成。

**是不是接入了真实公司项目？**

不使用公司内部硬件数据。所有 demo 都使用公开 KiCad、public-safe synthetic Allegro fixture 和公开 datasheet/profile evidence。

## 可配图建议

- Git 时间线图：8 个阶段，从 `72ca609` 到 `958d701`。
- 产品演进图：CLI report -> component-centric IR -> validation UI -> Copilot workbench -> risk hints/product surface。
- Trust architecture 图：Refdes Guard、Evidence Ledger、L1/L2/L3、structured tools。
- `U999` 反幻觉图：用户问 `U999` -> `get_component` miss -> `⟨?U999⟩`。
- Workbench 截图：Project Summary、Must Review、Copilot trace、evidence token。
- 开发者进化图：追功能 -> 收边界 -> 做验证 -> 做叙事 -> 做产品表面。

## 外发前检查清单

- 没有原始 Codex JSONL 大段内容。
- 没有 API key、token、`.env`、cookie、Bearer、邮箱、手机号、私有 URL。
- 没有本地绝对路径或公司内部硬件数据。
- 没有说 Hardwise 已经完整自动评审整板。
- 没有说所有 profile 都是 live retrieval。
- 没有说 eval 是专家 gold-label accuracy。
- 没有说当前已经是完整 SaaS。
- 小红书版本有人味，LinuxDo 版本有 commit 和架构证据，面试版本能 2 分钟讲完。
