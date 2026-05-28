# Hardwise Demo — 90 秒阅读版

Hardwise 是一个面向硬件研发“设计验证”节点的本地静态工作台。现在的 demo 先用公开 KiCad 工程展示原理图检视闭环，再用公开 Allegro/BOM 样例展示项目级验证器：解析 design facts、自动匹配本地 structured profiles，生成“顶部摘要 + 器件列表 + 验证区 + 报告详情”的静态网页，同时保留 manual/no-profile 行和结构化索引。

## 直接看效果

- 产品介绍首页：[`product-intro.html`](product-intro.html)
- 面向硬件评审的中文展示页：[`hardware-demo.html`](hardware-demo.html)
- 设计验证器工作台示例：[`hardware-demo.html`](hardware-demo.html)，由 `design-validator-ui` 直接生成
- 技术机制快照：[`demo.html`](demo.html)
- 样例报告命令：

```bash
uv run hardwise design-validator-ui \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --output reports/controller-design-validator.html \
  --index-output reports/controller-design-validator-index.md \
  --index-json reports/controller-design-validator-index.json
```

样例输出摘要：

```text
report: reports/controller-design-validator.html (4 validated targets, 21 manual/no-profile)
index:  reports/controller-design-validator-index.md / .json
rollup: 25 components, PASS/WARN/ERROR=1/0/3
```

## 看简历的人应该记住什么

1. **不是聊天机器人套壳**：模型不能自由编位号，所有 `U1/C3/J1` 这类 refdes 都要命中 EDA registry。
2. **报告可追溯**：每条 finding 都带 `sch:` / `datasheet:` / `bom:` 这类证据 token；没有证据的 finding 不进报告。
3. **能跑真实工程输入**：demo 既能解析公开 KiCad 项目，也能对公开 Allegro/BOM 样例生成项目级验证索引和三段式静态工作台。
4. **验证逻辑是 deterministic 的**：当前公开 profile 覆盖 L78、XL1509、EG2132、STM32G030 basic，未覆盖器件以 manual/no-profile 透明显示。
5. **边界清楚**：只做 pre-Layout schematic-side validation，不碰 PCB review、PLM、FMEA、账号次数或公司内部硬件数据。

## 一眼看懂的结果

| 指标 | demo 结果 | 意义 |
|---|---:|---|
| Components reviewed | 121 / 25 | KiCad 旧 demo + Allegro design-validator workbench 都是真实解析，不是手填样例 |
| Findings | 28 / 4 validated + 21 manual | KiCad 侧是 6 条电容耐压字段检查 + 22 条 NC pin 复核；验证器侧是 4 个自动匹配器件 |
| Validation rollup | 1 PASS / 0 WARN / 3 ERROR | U1 PASS，U12/U3/U8 进入明确错误态 |
| Evidence tokens | 每条 finding 至少 1 个 | 支撑“无证据不输出” |
| Sanitizer | 未验证位号会包成 `⟨?U999⟩` | 防止模型幻觉流到报告 |

## 面试时可以这样讲

> 我做的是硬件研发里“设计验证”这个窄节点，不是泛泛的硬件 AI。Hardwise 把 schematic netlist、BOM identity 和 structured datasheet profile 接成可审计的 deterministic validation workbench；模型只能在 registry guard 和 evidence guard 的边界内解释结果。重点不是模型有多会说，而是系统结构上不给它编位号、编证据的机会。
