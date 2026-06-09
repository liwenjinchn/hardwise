# Hardwise Demo 录屏脚本

目标时长：90 秒。主线录 `serve-workbench --fake-ai` 启动的本地 workbench：模型不能自由评审硬件，必须被 EDA registry、evidence token、deterministic validator 和 Refdes Guard 约束住。`--fake-ai` 用确定性 fake 模型块，但仍跑真实 Runner + 工具 + Refdes Guard，不需要 API key。`design-validator-ui --ai-snapshot` 生成的 `file://` 静态快照作为无需起服务的离线备份；KiCad `review` / `ask` 只作为证据链复现附录。

## 录屏前准备

```bash
uv sync
uv run hardwise serve-workbench \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --fake-ai
```

命令会打印 `serve-workbench: http://127.0.0.1:8765 (...)`，开录前在浏览器打开这个 URL（默认端口 8765，可用 `--port` 改）。浏览器里只保留 README 和 workbench 两个页面，避免录屏时切到无关 tab。

离线备份（reviewer 不便起服务时）：

```bash
uv run hardwise design-validator-ui \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --ai-snapshot \
  --output /tmp/hardwise-copilot-workbench.html
```

直接用 `file://` 打开生成的 HTML，无需起服务、无需 API key（同一份校验真值与 Refdes Guard，复用 SPA 外观和离线快照数据）。

## 分镜

1. 项目摘要，10 秒

   指顶部指标：25 components、22 L1 rows、PASS-WARN-ERROR=5/13/4、3 manual/no-local-profile。说：Hardwise 消费导出的 netlist/PST+BOM，生成 pre-Layout review workbench；这不是实时 EDA 插件，也不是让模型自由审板。

2. Must Review，10 秒

   指 Must Review 队列。说：工作台先回答评审会最关心的问题：哪些条目必须在 Layout handoff 前看，哪些只是 manual gap，哪些已经 deterministic pass。

3. `U12` deterministic ERROR，18 秒

   点 `U12`，展示 XL1509 buck 错误。说：这个 ERROR 不是模型意见，是 deterministic validator 从网表和 XL1509 profile 得到的结论：`L1=6.8uH` 低于 profile 最小值，`D5=1N4007W` 不是 Schottky-style freewheel diode。

4. Copilot trace，18 秒

   打开右下角 Hardwise 助手，点一条 suggested 问题（或直接提问），展开 Evidence / Tool trace。说：`--fake-ai` 只产出确定性 `tool_use`/text，回答仍来自真实 Runner 的 structured tools；`run_component_validation` 是 L1 deterministic，证据 token 必须可见、可复制。

5. `U999` wrapped，12 秒

   在 Copilot 输入 `板上有没有 U999?`。说：不存在的位号不会被模型编造成器件，工具返回 `found=false`，最终显示会把它包成 `⟨?U999⟩`。

6. L78 evidence token，12 秒

   点 L78 evidence 问题或 U1/L7805 trace，停在 `datasheet:l78.pdf#p4`。说：L78 是 L2 grounded evidence：有页码级 evidence token 供 reviewer 核对，但它不会自动升级成模型自由判断。

7. 收束，10 秒

   说：边界是刻意收窄的：只做 schematic-side review，只用公开输入，不做 PCB layout、boardview、PLM、供应商、价格库存，也不碰公司内部硬件数据。

## 证据链复现附录

```bash
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003,DS001 --report-style component --output /tmp/hardwise-review.md
uv run hardwise ask data/projects/pic_programmer "What is U999?"
uv run hardwise ingest-datasheet data/datasheets/l78.pdf --part-ref L7805 --persist-dir /tmp/hardwise-evidence-audit
uv run hardwise query-datasheet "absolute maximum input voltage" --top-k 3 --persist-dir /tmp/hardwise-evidence-audit
```

附录命令证明 KiCad registry、unknown-refdes structured miss、L78 ingest/retrieve 和 `datasheet:l78.pdf#p4` 边界；不抢 90 秒 workbench 主舞台。

## 不要这么说

- 不说“模型独立验证整块板”。
- 不说 generic passive checks 是深度 datasheet review。
- 不说所有 profile token 都经过 live vector retrieval。只有 staged and queried 的 PDF 才能说成 live retrieval。
- 不暗示覆盖 PCB geometry、layout、routing、supplier status、lifecycle、PLM 或实时 EDA 插件。
