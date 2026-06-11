# Hardwise Demo 录屏脚本

目标时长：90 秒。主线录 `serve-workbench --fake-ai` 启动的本地工作台：模型不能自由评审硬件，必须被器件台账、证据出处、确定性验证器和位号防护约束住。`--fake-ai` 用确定性假模型，但仍跑真实 Runner + 工具 + 位号防护，不需要 API key。`design-validator-ui --ai-snapshot` 生成的 `file://` 静态快照作为无需起服务的离线备份；KiCad `review` / `ask` 只作为证据链复现附录。

## 录屏前准备

```bash
uv sync
uv run hardwise serve-workbench \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --fake-ai
```

命令会打印 `serve-workbench: http://127.0.0.1:8765 (...)`，开录前在浏览器打开这个 URL（默认端口 8765，可用 `--port` 改）。浏览器里只保留 README 和工作台两个页面，避免录屏时切到无关 tab。

离线备份（评审人不便起服务时）：

```bash
uv run hardwise design-validator-ui \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --ai-snapshot \
  --output /tmp/hardwise-copilot-workbench.html
```

直接用 `file://` 打开生成的 HTML，无需起服务、无需 API key（同一份校验真值与位号防护，复用产品界面和离线快照数据）。

## 分镜

1. 项目摘要，10 秒

   指顶部指标：25 个器件、22 行 L1 验证、通过-警告-错误=5/13/4、3 行人工缺口。说：Hardwise 消费导出的网表/PST + BOM，生成 Layout 前评审工作台；这不是实时 EDA 插件，也不是让模型自由审板。

2. 必须修，10 秒

   指"必须修"队列。说：工作台先回答评审会最关心的问题：哪些条目必须在交给 Layout 前看，哪些只是人工缺口，哪些已经确定性通过。

3. `U12` 确定性错误，18 秒

   点 `U12`，展示 XL1509 降压错误。说：这个错误不是模型意见，是确定性验证器从网表和 XL1509 器件档案得到的结论：`L1=6.8uH` 低于档案最小值，`D5=1N4007W` 不是肖特基类续流二极管。

4. AI 问答轨迹，18 秒

   打开右下角 Hardwise 助手，点一条推荐问题（或直接提问），展开证据/工具轨迹。说：`--fake-ai` 只产出确定性的工具调用和文本，回答仍来自真实 Runner 的结构化工具；`run_component_validation` 是 L1 确定性，证据出处必须可见、可复制。

5. `U999` 包裹，12 秒

   在助手里输入 `板上有没有 U999?`。说：不存在的位号不会被模型编造成器件，工具返回 `found=false`，最终显示会把它包成 `⟨?U999⟩`。

6. L78 证据页码，12 秒

   点 L78 证据问题或 U1/L7805 轨迹，停在 `datasheet:l78.pdf#p4`。说：L78 是 L2 有出处证据：有页码级证据出处供评审人核对，但它不会自动升级成模型自由判断。

7. 收束，10 秒

   说：边界是刻意收窄的：只做原理图侧评审，只用公开输入，不做 PCB layout、boardview、PLM、供应商、价格库存，也不碰公司内部硬件数据。

## 证据链复现附录

```bash
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003,DS001 --report-style component --output /tmp/hardwise-review.md
uv run hardwise ask data/projects/pic_programmer "What is U999?"
uv run hardwise ingest-datasheet data/datasheets/l78.pdf --part-ref L7805 --persist-dir /tmp/hardwise-evidence-audit
uv run hardwise query-datasheet "absolute maximum input voltage" --top-k 3 --persist-dir /tmp/hardwise-evidence-audit
```

附录命令证明 KiCad 器件台账、未知位号结构化未命中、L78 入库/检索和 `datasheet:l78.pdf#p4` 边界；不抢 90 秒工作台主舞台。

## 不要这么说

- 不说"模型独立验证整块板"。
- 不说通用被动件检查是深度规格书审查。
- 不说所有档案出处都经过实时向量检索。只有本地入库并检索过的 PDF 才能说成实时检索。
- 不暗示覆盖 PCB 几何、布局布线、供应商状态、生命周期、PLM 或实时 EDA 插件。
