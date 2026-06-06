# Hardwise Demo 录屏脚本

目标时长：60-90 秒。主线只讲 trust architecture：模型不能自由评审硬件，必须被 EDA registry、evidence token、deterministic validator 和 Refdes Guard 约束住。coverage 数字只当支撑材料。

## 录屏前准备

```bash
uv sync
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003,DS001 --report-style component --output /tmp/hardwise-review.md
uv run hardwise design-validator-ui \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --ai-snapshot \
  --output /tmp/hardwise-copilot-workbench.html
```

开录前先打开 `/tmp/hardwise-copilot-workbench.html`。浏览器里只保留 README 和 workbench 两个页面，避免录屏时切到无关 tab。

## 分镜

1. README 开场，10 秒

   说：Hardwise 不是让 LLM 自由判断硬件，而是一个 pre-layout 原理图评审工作台。模型只能通过结构化工具拿到 EDA registry、netlist 和 evidence token，输出再经过 Refdes Guard。

2. 工作台摘要，15 秒

   指顶部指标：25 components、16 L1 rows、PASS-WARN-ERROR=4/9/3。说：16 个 L1 rows 不是 16 个深度 datasheet review，其中 4 个是 profile-backed targets，12 个是 generic passive checks；剩余 9 个保持 manual/no-local-profile。

3. 确定性问题，20 秒

   点 `U12`，展示 buck 错误。说：这个 ERROR 不是模型意见，是 deterministic validator 从网表和 XL1509 profile 里得到的结论：L1 是 6.8 uH，低于 profile 最小值；D5 是 1N4007W，不是 Schottky-style freewheel diode。

4. Copilot trace，20 秒

   打开右下角 Hardwise 助手，点一条已烘焙的问题，例如 `这个 U3 为什么是 ERROR/WARN?`。展开 evidence/tool trace。说：Copilot 的回答来自 structured tools；`run_component_validation` 是 L1 deterministic，证据 token 必须可见、可复制。

5. Refdes Guard，15 秒

   点 `板上有没有 U999?`。说：不存在的位号不会被模型编造成器件，工具返回 `found=false`，最终显示会把它包成 `⟨?U999⟩`。

6. 收束，10 秒

   说：边界是刻意收窄的：只做 schematic-side review，只用公开输入，不做 PCB layout、boardview、PLM、供应商、价格库存，也不碰公司内部硬件数据。

## 不要这么说

- 不说“模型独立验证整块板”。
- 不说 generic passive checks 是深度 datasheet review。
- 不说所有 profile token 都经过 live vector retrieval。当前只有 L78 smoke 是完整 ingest/retrieve/ask 路径。
- 不暗示覆盖 PCB geometry、layout、routing、supplier status、lifecycle 或 PLM。
