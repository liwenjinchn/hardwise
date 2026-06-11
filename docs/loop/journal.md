# 自主循环 Journal — loop/backend-allegro

> 每次迭代追加一条,格式:
> `日期时间 | 轨道(A/B) | 选了什么 | 结果(commit hash 或丢弃/STUCK/RED/ASK 原因) | 下一步意图`
>
> 本文件 + git log 是期末人工验收的主要材料。不删改旧条目。

## 迭代记录

- 2026-06-11 | A | 首个网络级检查 `net_single_endpoint`(`validation/nets.py` + 6 测试):勘察确认 Design.nets 已有 (refdes,pin) 端点但零消费方;单端点网络报保守 WARN + `netlist:<file>#net=<NAME>` 证据 token;公开 fixture 真值锁定(mixed_controller_power_stage.net → ADC_POT/PWM1L 恰 2 条,pst → 0 条) | 绿 44eed81(604 passed,ruff 干净) | 下一步:CLI/report 接入 net 检查结果(让 finding 进现有报告通路),之后考虑电源轨识别(Net.is_power_rail 预留字段)
- 2026-06-11 | A | net 检查接入报告通路:ProjectValidationIndex 加 net_checks 字段(builder 用网表 basename 做 token 标签,绝对路径不进 token),markdown 报告加 Net Checks 节(有发现出表格/无发现出明示行),组件级 totals 不动 | 绿 8fc1a5f(607 passed,ruff 干净);一次测试断言过宽返工(发现既有行为:report 头部对仓库外路径显示绝对路径,系 display_path 既有语义,非本迭代引入,已收窄断言并注释) | 下一步:workbench 状态/UI 暴露 net_checks(view_model/server,涉及前端展示的部分留给前端轨),或先做电源轨识别充实检查族
