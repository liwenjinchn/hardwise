# Hardwise Demo — 90 秒阅读版

Hardwise 是一个面向硬件研发“设计验证”节点的本地静态工作台。现在的 V1 demo 先用公开 KiCad 工程展示原理图检视闭环，再用公开 Allegro/BOM 项目展示项目级验证器：自动识别 PST+BOM、按 BOM/device group 建 coverage index、匹配本地公开 datasheet index，并对一个真实 power family 输出 deterministic validation。

## 直接看效果

- 产品介绍首页：[`product-intro.html`](product-intro.html)
- 面向硬件评审的中文展示页：[`hardware-demo.html`](hardware-demo.html)
- 设计验证器工作台示例：[`hardware-demo.html`](hardware-demo.html)，由 `design-validator-ui` 直接生成
- 技术机制快照：[`demo.html`](demo.html)
- 样例报告命令：

```bash
uv run hardwise design-validator-ui \
  "<public-allegro-folder>" \
  --document-index data/document_indexes/power_v1_docs.csv \
  --output reports/v1-design-validator.html \
  --index-output reports/v1-design-validator-index.md \
  --index-json reports/v1-design-validator-index.json
```

样例输出摘要：

```text
selected-bom: <public-allegro-folder>/SWITCH BOARD 144-VA_20240712 1401(1).BOM
document-index: data/document_indexes/power_v1_docs.csv (matched=2, no_result=90, ambiguous=0, manual_needed=40)
design-validator-ui: reports/v1-design-validator.html (4010 components, validated=4, BOM matched=4010, PASS/WARN/ERROR=4/0/0, manual=4006)
validation-index-json: reports/v1-design-validator-index.json (4010 rows)
```

## 看简历的人应该记住什么

1. **不是聊天机器人套壳**：模型不能自由编位号，所有 `U1/C3/J1` 这类 refdes 都要命中 EDA registry。
2. **报告可追溯**：每条 finding 都带 `sch:` / `datasheet:` / `bom:` 这类证据 token；没有证据的 finding 不进报告。
3. **能跑真实工程输入**：demo 既能解析公开 KiCad 项目，也能对公开 Allegro/PST+BOM 项目生成 132 个器件组的项目级 coverage index。
4. **验证逻辑是 deterministic 的**：V1 用本地公开 document index 匹配 MPQ8626 datasheet，并用 buck family validator 验证 U13/U20/U23/U26；未覆盖器件以 manual/no-profile 透明显示。
5. **边界清楚**：只做 pre-Layout schematic-side validation，不碰 PCB review、PLM、FMEA、账号次数或公司内部硬件数据。

## 一眼看懂的结果

| 指标 | demo 结果 | 意义 |
|---|---:|---|
| Components reviewed | 121 / 4010 | KiCad 旧 demo + Allegro design-validator workbench 都是真实解析，不是手填样例 |
| Component groups | 132 | 真实 Allegro 项目按 BOM/device group 扫读，不让 4010 行 raw refdes 淹没评审 |
| Findings / validation | 28 / 4 validated + 4006 manual | KiCad 侧是 checklist findings；验证器侧是 MPQ8626 power family validated，其余透明等待 profile/family 覆盖 |
| Validation rollup | 4 PASS / 0 WARN / 0 ERROR | U13/U20/U23/U26 都走 MPQ8626 synchronous buck validator |
| Public docs | 2 matched groups | `MPQ8626GD` / `MPQ8626GD-Z` 匹配本地公开 document index |
| Evidence tokens | 每条 finding 至少 1 个 | 支撑“无证据不输出” |
| Sanitizer | 未验证位号会包成 `⟨?U999⟩` | 防止模型幻觉流到报告 |

## 面试时可以这样讲

> 我做的是硬件研发里“设计验证”这个窄节点，不是泛泛的硬件 AI。Hardwise 把 schematic netlist、BOM identity 和 structured datasheet profile 接成可审计的 deterministic validation workbench；模型只能在 registry guard 和 evidence guard 的边界内解释结果。重点不是模型有多会说，而是系统结构上不给它编位号、编证据的机会。
