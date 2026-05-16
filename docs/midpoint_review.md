# Hardwise 现状盘点与收束评审

> 目的：把项目从"继续工程扩张"切换到"投递型 MVP 收束"。
>
> 这份文档不回答"还能加什么"，只回答：
> 1. 已经真实证明了什么；
> 2. 什么是主线，什么只是支线；
> 3. 哪些方向现在应该停；
> 4. 接下来最小收尾动作是什么。

---

## 0. 结论

Hardwise 当前不是"没做完"，而是**已经有可演示闭环，但叙事被支线工程稀释**。

新的 MVP 定锚：

> Hardwise 不是证明"大模型能自动评审硬件"，而是证明"硬件评审 Agent 必须被 EDA registry 和 evidence token 约束；模型只能解释工具查到的对象，不能自由发明工程事实。"

接下来不再用功能数量证明项目价值。用**边界感、证据链、反幻觉约束**证明项目价值。

---

## 1. 当前可复现事实

### 1.1 主 demo 已经跑通

```bash
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003
```

已验证输出：

```text
report: reports/pic_programmer-20260516.md (28 findings, 121 components reviewed)
store:  reports/pic_programmer.db (121 components, 77 NC pins)
Sanitizer: 0 unverified refdes wrapped, 0 findings dropped (no evidence)
```

最小闭环：

```text
KiCad project -> parser/registry -> deterministic rules -> guard/evidence -> report -> store
```

### 1.2 质量门是绿的

```bash
uv run pytest -q
uv run ruff check .
```

结果：

```text
163 passed, 7 deselected
All checks passed!
```

当前状态可以作为投递材料的基线，不需要继续追加规则来证明"项目还活着"。

### 1.3 Public smoke 足够支撑"可复现"叙事

`hardwise eval` 当前结果：

```text
5 public repos
16 KiCad project directories
1707 parsed components
437 deterministic findings
0 project failures
0 unverified refdes wrapped
0 findings dropped for missing evidence
```

这些数字不能叫"准确率"，也不应该包装成 expert gold-label benchmark。它们能证明的是 parser/guardrail 在公开项目上可复现，且 finding distribution 可被回归跟踪。

---

## 2. 主线资产

### 2.1 Refdes Guard

位置：

- `src/hardwise/guards/refdes.py`
- `src/hardwise/agent/tools.py:get_component`
- `src/hardwise/agent/runner.py`

两层防御：

- **工具层**：`get_component("U999")` 返回 structured miss，而不是让模型自由回答。
- **输出层**：用户可见文本中的 refdes-shaped token 必须命中 registry；未验证 token 被包成 `⟨?U999⟩`。

核心表达：

> 不是提示模型"不要幻觉"，而是让幻觉对象很难进入用户可见报告。

### 2.2 Evidence Ledger

位置：

- `src/hardwise/guards/evidence.py`
- `src/hardwise/checklist/finding.py`
- `src/hardwise/report/markdown.py`
- `src/hardwise/report/html.py`

规则：

> No token, no claim.

每条 finding 至少要带 `sch:<file>#<refdes>` 这样的 source token；没有 evidence token 的 finding 会在报告前被丢弃。

### 2.3 Tool-use Agent

位置：

- `src/hardwise/agent/tools.py`
- `src/hardwise/agent/runner.py`
- `src/hardwise/agent/prompts.py`

当前工具：

- `list_components`
- `get_component`
- `get_nc_pins`
- `search_datasheet`

面试里不要强调"有 4 个工具"，而要强调：

> 模型不能直接声明工程事实。它必须通过工具查询 refdes、NC pin 和 datasheet evidence。

### 2.4 三条 active rules 已够 MVP

当前 active rules：

- R001: 新建器件候选识别，footprint 空字段作为弱信号；
- R002: 电容 value 字段是否声明额定电压；
- R003: NC pin handling，含 connector/socket 聚合与 `decision` 分桶。

这三条已能展示 EDA 单字段检查、硬件字段规范检查、pin 级结构解析和 reviewer attention allocation。不要为了"看起来完整"强行补 R004/R005。

---

## 3. 支线资产

这些东西有价值，但不该当主卖点。

| 支线 | 应该怎么讲 | 不该怎么讲 |
|---|---|---|
| Eval Pack | public regression smoke / guardrail regression | 准确率 benchmark |
| Prompt Caching | `cache_control` 已接入，MiMo 上有 `cache_read_input_tokens` 非零 | creation accounting 已完整验证 |
| Tiered Routing | 三槽结构已落地，模型名不写死 | 已经有真实成本分层收益 |
| Sleep Consolidator | human-gated candidate rule memory | 自动进化系统 |
| PostgreSQL / HTML / trace.jsonl | 工程完整度和可展示性 | 核心创新 |

---

## 4. 诚实边界

### 4.1 没有专家 gold-label accuracy

当前没有公开的 KiCad schematic + expert review issue 成对数据集。

不能说：

```text
Hardwise 准确率 xx%
```

应该说：

```text
Hardwise 在 public corpus 上完成 regression smoke，
并跟踪 parser failure、unverified refdes、evidence dropped、finding distribution。
```

### 4.2 R003 数据不漂亮，但结构正确

R003 已有 `decision` 和 `evidence_chain`。但 `pic_programmer` 里真正有 NC pin 的器件没有对应 datasheet ingest，所以很多结果是：

```text
decision=reviewer_to_confirm
```

这不是失败。它说明系统在证据不足时不会假装知道。

推荐说法：

> 我宁愿让系统输出 reviewer_to_confirm，也不让它在没有 datasheet 证据时编一个 likely_ok。

### 4.3 R004/R005 不应现在硬上

R004 I2C 地址冲突和 R005 dangling nets 都依赖 schematic-side net parser。

当前已有 PCB-side net parser 只能作为 post-Layout diagnostic，不能作为 pre-Layout schematic review evidence。现在硬做 R004/R005，会用不合法证据或字符串 heuristic 伪装 net-aware reasoning。

### 4.4 Cadence/Allegro 不在当前 MVP

当前只做 KiCad，是因为：

- Mac 本地没有 Cadence 环境；
- 公开可复现样例主要来自 KiCad；
- MVP 必须全部基于 public data。

合理说法：

> 我先用 KiCad 证明 adapter boundary 和 guardrail 机制；Cadence 是后续在授权环境中的一个新 adapter，而不是重写系统。

---

## 5. 停工线

从现在开始，下面这些方向停止推进，除非有明确面试或投递需求触发。

### 5.1 停止扩规则数量

暂停：

- R004 I2C 地址冲突；
- R005 dangling nets；
- R006/R007 net naming；
- 更多 checklist rules。

理由：规则数量已经不是短板。主线是 anti-hallucination + evidence discipline。

### 5.2 停止扩大 eval

暂停：

- 继续下载更多 public repos；
- 继续追大规模 corpus 数字；
- 继续试图包装 accuracy benchmark。

理由：没有人工 gold label，再大的 corpus 也只是 smoke。

### 5.3 停止产品化入口

暂停：

- GitHub Action；
- PR comment bot；
- Web UI；
- WebSocket streaming；
- boardview canvas。

理由：这些是产品入口，不是 MVP 证明点。

### 5.4 停止跨节点扩张

暂停：

- PCB review；
- 仿真；
- 测试结果回灌；
- BOM/PLM；
- FMEA；
- manufacturing checks。

理由：Hardwise 的 demo anchor 是 pre-Layout schematic review node。跨节点扩张会稀释叙事。

---

## 6. 下一步最小收尾

### 6.1 重写面试叙事

准备一条 2 分钟主线：

> 我用两周做了一个受约束的 schematic-review Agent。它不让模型自由评审硬件，而是先解析公开 KiCad 项目，建立 refdes registry；所有用户可见 refdes 都必须被 registry 验证，所有 finding 都必须带 evidence token；模型只能通过工具查询工程对象。当前在 public KiCad sample 上输出 28 findings / 121 components reviewed，并在 public smoke 上跑过 5 repos / 16 projects / 1707 components，guardrail 指标为 0 unverified refdes、0 evidence-less dropped。

### 6.2 清理 README / PLAN 的扩张语气

材料应改成：

- MVP 已收束；
- R001-R003 是当前 active scope；
- R004/R005 是 post-MVP；
- eval 是 regression smoke；
- prompt caching / tier routing / consolidator 是 supporting mechanisms。

不要让读者以为项目必须补到 R005 才算完成。

### 6.3 准备 demo script

推荐 3 段：

1. `review`：展示 report、28 findings、0 guardrail failure；
2. `ask U999`：展示 unknown refdes 不被编造；
3. eval summary：展示 public smoke 和 guardrail metrics。

不要在 demo 里现场讲 R004/R005，也不要讲太多 prompt cache。

### 6.4 只做稳定性收尾

允许修 README/命令不一致、报告显示、测试失败、demo artifact、投递材料。不允许新增 parser、rule、UI 或平台集成。

---

## 7. 一句话复盘

这轮项目最大的收获不是多做了几条规则，而是及时识别出：**硬件 AI Agent 的价值不在模型说得多像专家，而在它什么时候被允许说、说的对象从哪里来、证据能不能追溯。**
