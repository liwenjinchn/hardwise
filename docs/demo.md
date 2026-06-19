# Hardwise MVP Demo — 90 秒工作台主线

Hardwise 是一个面向硬件研发 Layout 前原理图评审节点的本地工作台。MVP 的主张不是让模型独立评审整块硬件，而是：

> 导入 Cadence/Allegro 导出的网表/PST + BOM（或公开原理图工程），生成评审人能直接使用的评审队列：必须修、人工确认、检查已满足，每行带证据出处。五个防编造机制和 L1/L2/L3 可信度分层是这条工作流的安全边界。

90 秒主舞台是 `serve-workbench --fake-ai` 启动的本地 React 工作台；
`design-validator-ui --ai-snapshot` 生成同款界面的离线单文件快照，作为
GitHub Pages / 无服务环境的备份入口。KiCad `review` / `ask` 命令保留为证据链附录和复现命令，用来证明器件台账、L78 检索、位号防护和工具纪律。

产品闭环：

```text
导入设计 -> 建立位号可信台账 -> 跑确定性检查
  -> 分成 必须修 / 人工确认 / 检查已满足
  -> AI 助手只解释工具证据 -> 导出评审反馈清单
```

## 90 秒主舞台

录屏主线：

```bash
uv run hardwise serve-workbench \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --fake-ai \
  --port 8765
```

离线备份 / GitHub Pages 入口：

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
(25 components, validated=22, bom_rows_matched=25, PASS/WARN/ERROR=5/13/4, manual=3)
validation-index-json: /tmp/hardwise-workbench-index.json (25 rows)
```

录屏顺序固定为：

| 步骤 | 屏幕动作 | 讲清楚的点 |
|---|---|---|
| 项目摘要 | 看顶部指标和分组评审队列。 | 输入已经变成评审工作台，不是聊天记录。 |
| 必须修 | 切到"必须修"区域。 | 错误/警告在交给 Layout 前保持显眼。 |
| `U12` 确定性错误 | 打开 XL1509 详情。 | 错误来自网表 + 审核过器件档案的 Python 验证器。 |
| AI 问答轨迹 | 展开 AI 助手的证据/工具轨迹。 | AI 助手解释结构化工具结果，不决定通过/警告/错误。 |
| `U999` 包裹 | 点"板上有没有 U999?"。 | 未知位号返回结构化未命中，并显示成 `⟨?U999⟩`。 |
| L78 证据页码 | 点 L78 证据问题或 U1/L7805 轨迹。 | `datasheet:l78.pdf#p4` 是可见、可核对的 L2 证据出处。 |

9 个有审核档案的目标器件加 13 个通用被动件检查构成 22 行 L1 验证；录屏主讲可聚焦 U1/U12/U3/U8/Q12，通用被动件检查只是轻量确定性覆盖，不包装成深度规格书审查：

| 位号 | 器件档案 | 状态 | 展示什么 |
|---|---|---|---|
| U1 | L7805 | 通过 | L78 引脚/档案检查，含 `datasheet:l78.pdf#p4` 证据。 |
| U12 | XL1509-12E1 | 错误 | 降压拓扑抓到 `D5=1N4007W` 续流二极管与 `L1=6.8uH` 电感问题。 |
| U3 | EG2132 | 错误 | 栅极驱动自举二极管耐压问题。 |
| U8 | STM32G030C8T6 | 错误 | SWDIO/SWCLK 接反。 |
| Q12 | SS8050 | 错误 | 档案引脚/连接不一致，发射极问题保持可见。 |

`serve-workbench --fake-ai` 用确定性假客户端驱动真实 Runner、五个工具和
位号防护，不需要 API key。`--ai-snapshot` 会把同一份工作台状态、器件详情、
准备包/导出数据和已审计的 AI 问答快照烤进单文件 HTML，不需要服务器或 API key。

这个路径不是实时 Cadence/Allegro 插件。它消费导出的网表/PST + BOM 文件，离线或通过本地服务器生成评审工作台。

## 可信边界

五个防编造机制：

| 机制 | 它限制了什么 |
|---|---|
| 位号防护（Refdes Guard） | 模型不能自由编 `U1/C3/J1`；用户可见位号必须来自解析出的器件台账。 |
| 证据台账（Evidence Ledger） | 评审发现没有证据出处就不能进入报告。 |
| 候选规则沉淀（Sleep Consolidator） | 重复问题只能进入人工审核候选规则池，不会自动变成新规则。 |
| 模型分级路由（Tiered Routing） | 运行时按快/标准/深三档选模型，代码不写死供应商型号。 |
| 提示词缓存（Prompt Caching） | 静态提示词可缓存，并有一次实测缓存命中数据。 |

可信度分层：

| 档位 | 含义 | 可见证据 |
|---|---|---|
| **L1 确定性** | Python 规则/验证器决定通过/警告/错误。模型只能解释结构化结果。 | `run_component_validation`、工作台验证行。 |
| **L2 有出处** | 本轮规格书检索返回了带来源 PDF + 页码的证据，供评审人核对。 | L78 轨迹：`datasheet:l78.pdf#p4`。 |
| **L3 人工确认** | 没有就绪器件档案或没有检索证据，保持人工确认。 | 无档案行、无检索命中的规格书问答。 |

覆盖闭环是支撑材料：器件档案缺口排序可以驱动多个器件族从 L3 人工确认进入 L1 确定性，但主叙事不是"覆盖率又涨了"，而是"模型被工程事实、证据链和可信度边界约束住"。

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

关键证据行：

```text
U3 / DS001 -> datasheet:l78.pdf#p4
```

含义：`U3` 是台账里的 L7805；档案里人工审核过的事实是 `abs_max.vin = 35.0 V`，证据出处是 `datasheet:l78.pdf#p4`。Hardwise 不能从这个 KiCad 原理图推断 Vin 实际电压，所以输出"待人工确认"，不猜测、不替评审人下最终结论。

### L78 入库 / 检索 / 问答

```bash
uv run hardwise ingest-datasheet data/datasheets/l78.pdf \
  --part-ref L7805 --persist-dir /tmp/hardwise-evidence-audit

uv run hardwise query-datasheet "absolute maximum input voltage" \
  --top-k 3 --persist-dir /tmp/hardwise-evidence-audit

uv run hardwise ask data/projects/pic_programmer \
  "请先用 search_datasheet 查询 L7805 absolute maximum input voltage，再回答 U3 的 Vin absolute maximum 来自哪一页；如果没有检索证据就明确说没有。" \
  --vector --persist-dir /tmp/hardwise-evidence-audit --trace
```

示例结果：`query-datasheet` top-1 返回 `[l78.pdf p4 part=L7805]`，`ask --vector` 调用 `search_datasheet` 和 `get_component`，最终引用 `l78.pdf` 第 4 页和 35 V。其它器件档案 JSON 里的 `datasheet:<part>.pdf#pN` 是人工审核过的公开档案出处，除非对应 PDF 也被本地入库并检索过，否则不能说成实时向量检索。完整边界说明见 [`docs/evidence_chain_audit.md`](evidence_chain_audit.md)。

### 位号防护演示

```bash
uv run hardwise ask data/projects/pic_programmer "What is U999?"
```

未知对象返回结构化未命中，例如 `found=false` 加最接近的真实位号候选；用户可见文本再经过位号防护，未知位号会显示为 `⟨?U999⟩`。

### Agent 验证桥测试

```bash
uv run pytest tests/agent/test_validation_bridge.py -q
# 6 passed
```

该测试证明 `Runner` 能把模型的 `run_component_validation(refdes)` 工具调用派发到 `validate_component_against_profile()`，返回结构化通过/警告/错误和证据出处；默认验证不需要 API key。

## 读完应该记住什么

1. **主舞台是评审工作台**：`serve-workbench --fake-ai` 是录屏入口，`design-validator-ui --ai-snapshot` 是同款离线备份，KiCad review/ask 是证据链附录。
2. **不是聊天机器人套壳**：模型不能自由编 `U1/C3/J1`；用户可见位号必须来自解析出的器件台账。
3. **证据有分层**：L1 是确定性规则，L2 是本轮带页码检索证据，L3 是人工确认。
4. **验证逻辑是确定性的**：`run_component_validation` 调用 Python 验证器，输出通过/警告/错误；模型只解释结构化结果。
5. **边界清楚**：只做 Layout 前原理图侧验证；不是实时 EDA 插件，不做 PCB/boardview、仿真、PLM、供应商/生命周期/价格，也不使用公司内部硬件数据。

## 相关文档

| 文件 | 用途 |
|---|---|
| `docs/hardware-demo.html` | 同款界面的离线工作台快照；公开展示备份入口。 |
| `docs/demo_recording_script.md` | 录屏分镜：项目摘要 -> 必须修 -> U12 -> AI 问答轨迹 -> U999 -> L78。 |
| `docs/demo.md`, `docs/demo.html` | 技术叙事和复现命令；工作台是主线，KiCad 是证据链附录。 |
| `docs/evidence_chain_audit.md` | L78 实时检索冒烟与人工审核档案出处的边界说明。 |
| `docs/mvp_definition.md` | MVP 边界：用户问题、核心流程、页面结构、范围、非目标、验收标准。 |
| `docs/faq.md` | 六个高频技术问题的简明回答。 |
| `docs/docs_inventory.md` | 当前/参考/历史文档清单；新会话先用它判断该读哪份。 |
