# Hardwise Phase 4 + C5 Demo — 90 秒阅读版

Hardwise 是一个面向硬件研发 pre-Layout 设计验证节点的本地工作台。当前 Phase 4 demo 不假装“一块板跑完所有命令”：仓库里没有同时具备 KiCad 工程和 Allegro netlist+BOM 的同一块公开板。诚实口径是：

> 同一条信任主干，两个公开输入轨。

信任主干是 `Refdes Guard + Evidence Ledger + L1 deterministic validators + structured tools`。两个输入轨分别展示这条主干的两面：

- **KiCad hero track**：`pic_programmer` 展示 registry-verified refdes、DS001/L78 evidence token、真实 L78 ingest/retrieve smoke、Refdes Guard 和 agent 工具 discipline。
- **Allegro workbench track**：`mixed_controller_power_stage` 展示项目级 `design-validator-ui`，一次显示 4 个已验证器件和 21 个 no-profile/manual 行。

Coverage loop 是支撑材料：C3/C4 已证明 ranking 可以驱动多个 family 从 L3/manual 进入 L1 deterministic，但主叙事不是“覆盖率又涨了”，而是“模型被工程事实和证据链约束住”。

C5 在这条主线上补了一个很薄的 L2 slice：`search_datasheet` trace 如果真的带回 `source_pdf + page`，Copilot trace 显示 `L2 grounded` 和 `datasheet:<pdf>#p<N>`；如果没有向量检索证据，就保持 `L3 manual` / 人工确认，不把回答包装成事实结论。

## 直接复现

### 1. KiCad hero track

```bash
uv run hardwise review \
  data/projects/pic_programmer \
  --rules R001,R002,R003,DS001 \
  --report-style component \
  --output /tmp/hardwise-phase4-review.md
```

实测输出：

```text
report: /tmp/hardwise-phase4-review.md (29 findings, 121 components reviewed)
store: reports/pic_programmer.db (121 components, 77 NC pins)
trace: /tmp/trace.jsonl
```

关键 evidence 行：

```text
U3 / DS001 -> datasheet:l78.pdf#p4
```

含义：`U3` 是 registry 里的 L7805；profile 里 reviewed fact 是 `abs_max.vin = 35.0 V`，source token 是 `datasheet:l78.pdf#p4`。Hardwise 不能从当前 KiCad schematic 推断 Vin 实际电压，所以输出 `reviewer_to_confirm`，不猜测、不替 reviewer 下最终结论。

L78 还跑过一个 live evidence-chain smoke：

```bash
uv run hardwise ingest-datasheet data/datasheets/l78.pdf \
  --part-ref L7805 --persist-dir /tmp/hardwise-evidence-audit

uv run hardwise query-datasheet "absolute maximum input voltage" \
  --top-k 3 --persist-dir /tmp/hardwise-evidence-audit

uv run hardwise ask data/projects/pic_programmer \
  "请先用 search_datasheet 查询 L7805 absolute maximum input voltage，再回答 U3 的 Vin absolute maximum 来自哪一页；如果没有检索证据就明确说没有。" \
  --vector --persist-dir /tmp/hardwise-evidence-audit --trace
```

实测：`query-datasheet` top-1 返回 `[l78.pdf p4 part=L7805]`，`ask --vector` 调用了 `search_datasheet` 和 `get_component`，最终引用 `l78.pdf` 第 4 页和 35 V。注意：C4 里其它 profile 的 `datasheet:<part>.pdf#pN` 是 reviewed public profile token，不等同于每个 PDF 都已进 Chroma 检索。完整 audit 见 [`docs/evidence_chain_audit.md`](evidence_chain_audit.md)。

Agent bridge 由 fast test 锁住：

```bash
uv run pytest tests/agent/test_validation_bridge.py -q
# 6 passed
```

该测试证明 `Runner` 能把模型的 `run_component_validation(refdes)` tool call 派发到 `validate_component_against_profile()`，返回结构化 PASS/WARN/ERROR 和 evidence tokens；默认验证不需要 API key。

### 2. Allegro workbench track

```bash
uv run hardwise design-validator-ui \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --ai-snapshot \
  --output /tmp/hardwise-phase4-workbench.html \
  --index-output /tmp/hardwise-phase4-index.md \
  --index-json /tmp/hardwise-phase4-index.json
```

实测输出：

```text
design-validator-ui: /tmp/hardwise-phase4-workbench.html
(25 components, validated=4, BOM matched=25, PASS/WARN/ERROR=1/0/3, manual=21)
validation-index-json: /tmp/hardwise-phase4-index.json (25 rows)
```

`--ai-snapshot` 会把已审计的 Copilot 快照烤进单文件 HTML。C5 新增一个 hermetic L78 evidence-chain smoke 问题，trace 里显示：

```text
Trust: L2 grounded
Evidence: datasheet:l78.pdf#p4
```

普通 workbench 器件的 datasheet 问题如果没有配置 vector store，仍显示 `L3 manual` 并回退到 reviewed profile / validation evidence；这不会改变任何 L1 PASS/WARN/ERROR。

四个 validated targets：

| Refdes | Profile | Status | What it shows |
|---|---|---|---|
| U1 | L7805 | PASS | L78 pin/profile checks, including `datasheet:l78.pdf#p4` evidence |
| U12 | XL1509-12E1 | ERROR | buck topology flags `D5=1N4007W` and `L1=6.8uH` |
| U3 | EG2132 | ERROR | gate-driver bootstrap diode rating issue |
| U8 | STM32G030C8T6 | ERROR | SWDIO/SWCLK swap |

## 看简历的人应该记住什么

1. **不是聊天机器人套壳**：模型不能自由编 `U1/C3/J1`；用户可见 refdes 必须来自 EDA registry。
2. **不是一块板假装全能**：KiCad track 证明 agent/review/evidence guard；Allegro track 证明 project workbench 和多 family validation。
3. **证据有分层**：L78 同时有 reviewed profile token 和 live ingest/retrieve/agent-citation smoke；C5 把有检索证据的问答 trace 标成 `L2 grounded`，无检索证据保持 `L3 manual`。
4. **验证逻辑是 deterministic 的**：`run_component_validation` 调用 Python validator，输出 PASS/WARN/ERROR；模型只解释结构化结果。
5. **边界清楚**：只做 schematic-side pre-Layout validation，不碰 PCB/boardview、仿真、PLM、supplier/lifecycle/pricing，也不使用公司内部硬件数据。

## Docs inventory

| File | Phase 4 handling |
|---|---|
| `docs/demo.md`, `docs/demo.html` | 当前 Phase 4 技术快照，已重写为“两轨一主干”。 |
| `docs/evidence_chain_audit.md` | L78 live retrieval smoke 与 C4 reviewed profile token 的边界说明。 |
| `docs/index.html` | 作为当前阅读入口刷新，优先指向 Phase 4 demo。 |
| `docs/hardware-demo.html` | 保留为 Allegro workbench 互补视图；不是 KiCad agent track。 |
| `docs/interview_narrative.*`, `docs/midpoint_review.*` | 面试讲稿 / 历史收束材料；当前口径以本页、README、`interview_qa.md` 和 evidence audit 为准。 |
| `docs/PLAN.html` | 阅读版路线图；source of truth 仍是 `docs/PLAN.md`。 |

## 面试时可以这样讲

> Hardwise 的重点不是让模型“独立评审一块板”，而是把模型放进硬件事实边界里。KiCad 轨证明 refdes guard、L78 检索证据链和 agent tool discipline；Allegro 轨证明同一套 deterministic validation truth 可以渲染成项目级工作台。C3/C4 coverage loop 证明这套主干能持续吃掉 manual rows，但它是支撑材料，不是主角。
