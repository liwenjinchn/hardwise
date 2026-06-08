# Hardwise MVP Demo — 90 秒 workbench runbook

Hardwise 是一个面向硬件研发 pre-Layout 原理图评审节点的本地工作台。MVP 的主张不是让模型独立评审整块硬件，而是：

> 导入公开原理图或导出的 schematic netlist/PST+BOM，生成 reviewer 能直接使用的 review queue：Must Review、Manual Gap、Passed、Evidence。五大 trust 机制和 L1/L2/L3 分层是这条工作流的安全边界。

90 秒主舞台是 `design-validator-ui --ai-snapshot` 生成的离线 Copilot workbench。KiCad `review` / `ask` 命令保留为证据链附录和复现命令，用来证明 registry、L78 检索、Refdes Guard 和 agent tool discipline。

产品闭环：

```text
导入设计 -> 建立 registry-verified 台账 -> 跑确定性检查
  -> 分成 Must Review / Manual Gap / Passed
  -> Copilot 只解释工具证据 -> 导出 feedback list
```

## 90 秒主舞台

```bash
uv run hardwise design-validator-ui \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --ai-snapshot \
  --output /tmp/hardwise-workbench.html \
  --index-output /tmp/hardwise-workbench-index.md \
  --index-json /tmp/hardwise-workbench-index.json
```

示例输出：

```text
design-validator-ui: /tmp/hardwise-workbench.html
(25 components, validated=22, BOM matched=25, PASS/WARN/ERROR=5/13/4, manual=3)
validation-index-json: /tmp/hardwise-workbench-index.json (25 rows)
```

录屏顺序固定为：

| Step | 屏幕动作 | 讲清楚的点 |
|---|---|---|
| 项目摘要 | 看顶部 metrics 和分组 review queue。 | 输入已经变成评审工作台，不是聊天记录。 |
| Must Review | 切到 Must Review 区域。 | ERROR/WARN 在 Layout handoff 前保持显眼。 |
| `U12` deterministic ERROR | 打开 XL1509 detail。 | ERROR 来自 netlist + reviewed profile 的 Python validator。 |
| Copilot trace | 展开 baked Copilot 的 Evidence / Tool trace。 | Copilot 解释 structured tool result，不决定 PASS/WARN/ERROR。 |
| `U999` wrapped | 点“板上有没有 U999?”。 | 未知位号返回 structured miss，并显示成 `⟨?U999⟩`。 |
| L78 evidence token | 点 L78 evidence 问题或 U1/L7805 trace。 | `datasheet:l78.pdf#p4` 是可见、可核对的 L2 evidence token。 |

四个 profile-backed targets 是主讲对象；13 个 generic passive rows 只表示轻量确定性覆盖，不包装成深度 datasheet review：

| Refdes | Profile | Status | What it shows |
|---|---|---|---|
| U1 | L7805 | PASS | L78 pin/profile checks, including `datasheet:l78.pdf#p4` evidence. |
| U12 | XL1509-12E1 | ERROR | Buck topology flags `D5=1N4007W` and `L1=6.8uH`. |
| U3 | EG2132 | ERROR | Gate-driver bootstrap diode rating issue. |
| U8 | STM32G030C8T6 | ERROR | SWDIO/SWCLK swap. |

`--ai-snapshot` 会把已审计的 Copilot 快照烤进单文件 HTML，不需要 server 或 API key。live path 用 `serve-workbench --fake-ai` 跑本地 FastAPI server；fake client 只发 tool_use/text，仍然经过真实 Runner、五个工具和 Refdes Guard。

这个路径不是实时 Cadence/Allegro 插件。它消费导出的 netlist/PST+BOM artifact，离线或通过本地 server 生成 reviewer workbench。

## Trust boundary

五大机制：

| 机制 | 它限制了什么 |
|---|---|
| Refdes Guard | 模型不能自由编 `U1/C3/J1`；用户可见位号必须来自 parsed EDA registry。 |
| Evidence Ledger | Finding 没有 source token 就不能进入报告。 |
| Sleep Consolidator | 重复问题只能进入人工审核候选规则，不会自动变成新 rule。 |
| Tiered Model Routing | 运行时按 `fast` / `normal` / `deep` slot 选模型，代码不写死 vendor model。 |
| Prompt Caching | 静态 agent prompt 可缓存，并有一次实测 cache-read 证明。 |

Trust 分层：

| Tier | 含义 | 可见证据 |
|---|---|---|
| **L1 deterministic** | Python rule / validator 决定 PASS/WARN/ERROR。模型只能解释结构化结果。 | `run_component_validation`、workbench validated rows。 |
| **L2 grounded** | 本轮 datasheet search 返回了带 `source_pdf + page` 的检索证据，供 reviewer 核对。 | L78 trace：`datasheet:l78.pdf#p4`。 |
| **L3 manual** | 没有 ready profile 或没有检索证据，保持人工确认。 | no-profile/manual rows、无 vector hit 的 datasheet 问答。 |

Coverage loop 是支撑材料：profile-gap ranking 可以驱动多个 family 从 L3/manual 进入 L1 deterministic，但主叙事不是“覆盖率又涨了”，而是“模型被工程事实、证据链和 tier 边界约束住”。

## 证据链附录 / 复现命令

### KiCad review

```bash
uv run hardwise review \
  data/projects/pic_programmer \
  --rules R001,R002,R003,DS001 \
  --report-style component \
  --output /tmp/hardwise-review.md
```

示例输出：

```text
report: /tmp/hardwise-review.md (29 findings, 121 components reviewed)
store: reports/pic_programmer.db (121 components, 77 NC pins)
trace: /tmp/trace.jsonl
```

关键 evidence 行：

```text
U3 / DS001 -> datasheet:l78.pdf#p4
```

含义：`U3` 是 registry 里的 L7805；profile 里 reviewed fact 是 `abs_max.vin = 35.0 V`，source token 是 `datasheet:l78.pdf#p4`。Hardwise 不能从这个 KiCad schematic 推断 Vin 实际电压，所以输出 `reviewer_to_confirm`，不猜测、不替 reviewer 下最终结论。

### L78 ingest / retrieve / ask

```bash
uv run hardwise ingest-datasheet data/datasheets/l78.pdf \
  --part-ref L7805 --persist-dir /tmp/hardwise-evidence-audit

uv run hardwise query-datasheet "absolute maximum input voltage" \
  --top-k 3 --persist-dir /tmp/hardwise-evidence-audit

uv run hardwise ask data/projects/pic_programmer \
  "请先用 search_datasheet 查询 L7805 absolute maximum input voltage，再回答 U3 的 Vin absolute maximum 来自哪一页；如果没有检索证据就明确说没有。" \
  --vector --persist-dir /tmp/hardwise-evidence-audit --trace
```

示例结果：`query-datasheet` top-1 返回 `[l78.pdf p4 part=L7805]`，`ask --vector` 调用 `search_datasheet` 和 `get_component`，最终引用 `l78.pdf` 第 4 页和 35 V。其它 profile JSON 的 `datasheet:<part>.pdf#pN` 是 reviewed public profile token，除非对应 PDF 也被 staged and queried，否则不能说成 live vector retrieval。完整 audit 见 [`docs/evidence_chain_audit.md`](evidence_chain_audit.md)。

### Ask guard

```bash
uv run hardwise ask data/projects/pic_programmer "What is U999?"
```

未知对象返回 structured miss，例如 `found=false` 和 closest matches；用户可见文本再经过 Refdes Guard，未知 refdes 会显示为 `⟨?U999⟩`。

### Agent bridge test

```bash
uv run pytest tests/agent/test_validation_bridge.py -q
# 6 passed
```

该测试证明 `Runner` 能把模型的 `run_component_validation(refdes)` tool call 派发到 `validate_component_against_profile()`，返回结构化 PASS/WARN/ERROR 和 evidence tokens；默认验证不需要 API key。

## 看简历的人应该记住什么

1. **主舞台是 workbench**：`design-validator-ui --ai-snapshot` 是 90 秒入口，KiCad review/ask 是证据链附录。
2. **不是聊天机器人套壳**：模型不能自由编 `U1/C3/J1`；用户可见 refdes 必须来自 EDA registry。
3. **证据有分层**：L1 是确定性规则，L2 是本轮带页码检索证据，L3 是人工确认。
4. **验证逻辑是 deterministic 的**：`run_component_validation` 调用 Python validator，输出 PASS/WARN/ERROR；模型只解释结构化结果。
5. **边界清楚**：只做 schematic-side pre-Layout validation；不是实时 EDA 插件，不做 PCB/boardview、仿真、PLM、supplier/lifecycle/pricing，也不使用公司内部硬件数据。

## Docs inventory

| File | Handling |
|---|---|
| `docs/hardware-demo.html` | 离线 Copilot workbench 展示页；90 秒主舞台。 |
| `docs/demo_recording_script.md` | 录屏分镜：项目摘要 -> Must Review -> U12 -> Copilot trace -> U999 -> L78。 |
| `docs/demo.md`, `docs/demo.html` | 技术叙事和复现命令；workbench 是主线，KiCad 是证据链附录。 |
| `docs/evidence_chain_audit.md` | L78 live retrieval smoke 与 reviewed profile token 的边界说明。 |
| `docs/mvp_definition.md` | MVP 边界：用户问题、核心流程、页面结构、范围、非目标、验收标准。 |
| `docs/docs_inventory.md` | Public/reference/historical/staged 文档清单；新会话先用它判断该读哪份。 |
