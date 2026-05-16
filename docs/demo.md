# Hardwise Demo — 90 秒阅读版

Hardwise 是一个面向硬件研发“原理图检视”节点的 AI Agent。这个 demo 用公开 KiCad 工程 `pic_programmer` 跑完整链路：解析原理图、生成检视意见、校验位号、写入证据 token、输出报告和结构化库。

## 直接看效果

- 产品介绍首页：[`product-intro.html`](product-intro.html)
- 面向硬件评审的中文展示页：[`hardware-demo.html`](hardware-demo.html)
- 技术机制快照：[`demo.html`](demo.html)
- 样例报告命令：

```bash
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003 --format html
```

样例输出摘要：

```text
report: reports/pic_programmer-YYYYMMDD.html (84 findings, 121 components reviewed)
store:  reports/pic_programmer.db (121 components, 77 NC pins)
consolidator: 2 candidate rule(s) appended to memory/rules.md
```

## 看简历的人应该记住什么

1. **不是聊天机器人套壳**：模型不能自由编位号，所有 `U1/C3/J1` 这类 refdes 都要命中 KiCad 解析出的 EDA registry。
2. **报告可追溯**：每条 finding 都带 `sch:<file>#<refdes>` 证据 token；没有证据的 finding 会被丢弃。
3. **能跑真实工程输入**：demo 解析公开 KiCad 项目，扫描 121 个 component，识别 77 个 NC pin。
4. **Agent 工程机制完整**：tool-use loop、Pydantic 工具 schema、tiered model routing、prompt caching、Sleep Consolidator 都已落地。
5. **边界清楚**：只做 pre-Layout schematic review，不碰 PCB review、PLM、FMEA 或公司内部硬件数据。

## 一眼看懂的结果

| 指标 | demo 结果 | 意义 |
|---|---:|---|
| Components reviewed | 121 | 从 KiCad 工程真实解析，不是手填样例 |
| Findings | 84 | 7 条电容耐压字段检查 + 77 条 NC pin 复核 |
| NC pins | 77 | 用 no-connect 坐标反查到具体 refdes/pin |
| Evidence tokens | 每条 finding 至少 1 个 | 支撑“无证据不输出” |
| Sanitizer | 未验证位号会包成 `⟨?U999⟩` | 防止模型幻觉流到报告 |

## 面试时可以这样讲

> 我做的是硬件研发里“原理图检视”这个窄节点，不是泛泛的硬件 AI。Hardwise 把 KiCad 工程解析成可验证 registry，让 Agent 只能通过工具查询元件和 NC pin，再把每条检视意见写成带证据 token 的报告。重点不是模型有多会说，而是系统结构上不给它编位号、编证据的机会。
