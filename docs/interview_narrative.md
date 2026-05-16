# Hardwise 面试叙事

> 用途：面试前先读这份短版。`docs/interview_qa.md` 是背后的证据库，
> 这份文档负责把故事讲顺、讲窄、讲可信。
>
> HTML 阅读版：`docs/interview_narrative.html`

## 核心定位

Hardwise 不是在证明“大模型可以独立评审完整硬件设计”。它证明的是一个更窄但更重要的点：

> 硬件评审 Agent 不能自由发明工程对象。所有 refdes 必须来自 EDA registry，
> 所有 finding 必须带 evidence token。

所以这个项目的核心不是“功能很多”，而是“边界很硬”。确定性的 Python 工具负责解析公开 KiCad 工程，形成可信的位号、pin、datasheet 证据记录；模型负责解释、组织、查询这些记录，但不能自己生成元件、pin 或 datasheet 结论。

## 30 秒开场

我做 Hardwise 是为了验证一个硬件 AI Agent 的最小可信闭环，不是为了两周内做一个完整硬件评审平台。

我选了一个很窄的节点：pre-layout 原理图评审。这个节点里最危险的问题不是模型说错一句话，而是它编出一个看起来很像真的位号、pin 或 datasheet 参数。所以我把模型放到两个约束后面：第一，用户可见的 refdes 必须命中 KiCad 解析出来的 EDA registry；第二，每条 finding 必须带 `sch:<file>#<refdes>` 或 `datasheet:<pdf>#p<N>` 这样的 evidence token。

当前 demo 在公开 KiCad `pic_programmer` 项目上能解析 121 个 components，定位 77 个 NC pins，输出 28 条 review findings，并且 0 个未验证 refdes、0 条无证据 finding。

## 2 分钟版本

这个项目起点是硬件原理图评审里的一个真实痛点：评审人不是只看一个错误，而是在 SCH、位号、value 字段、pin 连接、datasheet 和 checklist 之间反复交叉确认。LLM 如果自由回答，最危险的失败不是措辞不专业，而是把不存在的工程事实说得很像真的。

所以我把 MVP 收窄到一个工作流节点：公开 KiCad 工程上的 pre-layout schematic review。我有意不做 PCB review、仿真、PLM、GitHub PR comment，也不使用任何公司内部硬件数据。在这个窄节点里，我实现了一个最小闭环：

1. 解析 KiCad schematic，生成真实 refdes 和 pin 事实的 registry。
2. 跑确定性规则，统一输出 `Finding` schema。
3. 报告出口经过 Refdes Guard 和 Evidence Ledger。
4. Agent 问答只能通过 `get_component`、`get_nc_pins`、`search_datasheet` 这类结构化工具。

比如模型不能自己判断 `U999` 是否存在。它必须调用 `get_component`，工具查 registry 后返回 `found=false` 和可能的 closest matches。模型可以解释“没找到这个位号”，但不能编一个合法器件记录出来。

我也做了 eval smoke，但我不会把它包装成专家准确率 benchmark。硬件原理图评审没有干净的公开 gold-label 数据集。我的 eval pack 是 regression / guardrail harness：它跑 5 个公开仓库、16 个 KiCad project、1707 个 parsed components，检查 parser failure、unverified refdes、evidence-less finding 这些硬指标不能退化。

这个项目的核心经验是 scope discipline。可信的 MVP 不是“AI 替代硬件评审”，而是“AI 只有在工程事实被工具和 provenance 约束之后，才适合进入评审辅助流程”。

## Demo 顺序

面试屏幕共享时按这个顺序讲：

1. 先跑主命令：

   ```bash
   uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003
   ```

2. 指出真实输出：

   - 121 components reviewed
   - 28 findings
   - relational store 写入 121 components + 77 NC pins
   - 0 unverified refdes wrapped
   - 0 findings dropped for missing evidence

3. 打开 report，看一条 R002：

   - refdes 是 registry 里的真实电容。
   - message 指出 value 字段缺额定耐压后缀。
   - evidence token 指回 `sch:pic_programmer.kicad_sch#C2`。

4. 再看一条 R003：

   - NC pin 来自 KiCad `no_connect` marker 和 pin 坐标匹配。
   - connector/socket 批量 NC 会聚合成低优先级 `likely_ok`。
   - IC/module NC 在没有 datasheet 证据时保持 `reviewer_to_confirm`。

5. 最后跑一个 Agent unknown path：

   ```bash
   uv run hardwise ask data/projects/pic_programmer "What is U999?"
   ```

   重点不是模型回答的文采，而是工具路径会返回 structured miss，不让模型编造 `U999`。

## 面试时重点讲

- 我把硬件工作流收窄到一个节点：pre-layout schematic review。
- 我只使用公开 KiCad 项目和公开 datasheet。
- 我把确定性事实抽取和模型推理分开。
- 我把 unknown 当成一等结果，不把“不知道”藏起来。
- 所有工具输入/输出都是 Pydantic schema，并且有 typed miss path。
- `decision` 和人工 review `status` 分离：机器可以给 `likely_issue`，但 accept/reject/close 仍归 reviewer。
- Eval Pack 是 regression 证据，不是伪装成准确率的 benchmark。

## 面试时不要这么说

- 不说 Hardwise 已经能完整评审硬件设计。
- 不说 eval pack 证明了专家级准确率。
- 不把 prompt caching 或 tiered routing 讲成主创新。
- 不说 R004/R005 或 schematic net parser 已经完成。
- 不暗示 demo 里每颗器件都有 datasheet 证据。
- 不说 Sleep Consolidator 会自动晋升规则；它是 human-gated。

## 被问“为什么不继续做大？”

因为硬件 AI 的难点不是功能堆叠，而是 trust boundary。一个能自由编造工程对象的大平台，可信度反而不如一个窄但诚实的闭环。

两周内我选择先证明最重要、也最可防守的部分：Agent 只能谈 registry-verified objects 和 evidence-backed findings。schematic-side net parser、I2C 地址冲突、PCB review、GitHub PR comment 都是合理的 post-MVP 工作，但不应该抢在核心 anti-hallucination contract 讲清楚之前。

## 一句话收尾

Hardwise 的核心回答是：在让模型评审一块板子之前，先让它在结构上不能发明这块板子。
