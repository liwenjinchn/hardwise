# 检查结果合同

这是 PRD 三条状态轴的实现说明。机器检查结果、严重度、证据性质和人工处理
分别保存；人工豁免、接受或解决不会把机器 UNKNOWN/FAIL 改写为 PASS。

## 当前字段

| 字段 | 值 | 含义 |
|---|---|---|
| result | PASS / FAIL / UNKNOWN / NOT_APPLICABLE | 该项检查是否完成、是否满足条件 |
| severity | ERROR / WARNING / INFO | 需要多高程度的关注，不能代替结果 |
| evidence_kind | SOURCE_FACT / DERIVED / HYPOTHESIS | 来源记录、规则推导、待核假设 |
| rule_version | 每项生产者的非空声明版本；当前样例含 1、2，不能当作固定全局版本 | 和检查标识一起解释规则版本 |
| needs_review | 布尔值 | 仍需要复核；不能同时认证 PASS |
| migration_state | current / legacy_needs_review | 区分新结果与历史结果待重放 |
| legacy_status | 历史 status 或空 | 保留旧含义，不当作本轮结果 |
| not_applicable_reason | 文本或空 | NOT_APPLICABLE 必须提供适用范围理由 |
| contract_version | hardwise.assessment.v1 | 字段语义版本 |

UNKNOWN 可以有 ERROR 严重度，例如缺少必须补齐的关键输入；这不表示已经
证明设计违反电气限制。FAIL 可以只有 WARNING 严重度，例如不满足已配置的
推荐范围或命名策略。HYPOTHESIS 不允许认证 PASS/FAIL。不适用不能增加通过数。

`status` 保留为派生兼容字段：FAIL+ERROR 为 ERROR；其他 FAIL 为 WARN；
其余取 result。本轮新规则产生的记录明确提供 result/severity，不依靠读取旧
WARN 猜含义。任务顶层的 status/status_group 仍是工作流关注分类；其嵌套
assessment 才是机器结果合同，不能把二者当作相同的语义轴。

组件综合结果按 FAIL → UNKNOWN → PASS → NOT_APPLICABLE 汇总；空检查集为
UNKNOWN。综合 FAIL 的严重度来自实际 FAIL 项，其他紧急 UNKNOWN 不会把一个
提醒级不满足误写成错误级不满足。每条子记录及其严重度完整保留。

## 旧数据

仅有 status 的记录进入 UNKNOWN + needs_review + legacy_needs_review，原值
保存在 legacy_status。这里的 UNKNOWN 表示新合同无法确认旧结论，不能反推
旧 WARN 当时究竟是违规、提醒还是缺资料。需要原输入重跑；本轮不自动补出
历史事实、证据或审批。序列化后再读回不会丢失旧状态与复核标记。

索引 JSON 版本升级为 `hardwise.validation_index.v3`。历史索引经过信任看板时，
不能直接复用旧 totals 的 PASS；看板从检查记录重新读取结果。历史 totals 作为
追溯元数据单列。只有概要而无检查记录，无法重新认证通过。

未审核器件档案产生的检查统一保留为待核假设/UNKNOWN；不是只在一条警告旁
继续认证其余结果。现有 READY 标签本身不等于本轮完成了独立工程复核，仍需
T03 的受控子集、条件参数与出处核查。

## 各端和统计范围

- 组件/引脚/网络模型、工具返回和 JSON 保留独立字段。
- 工作台队列、引脚、检查卡片和问题项通过嵌套 assessment 保留合同；白色
  React 详情和证据区域展示结果、严重度与证据性质。
- Markdown 和旧静态 HTML 也包含独立合同表及不适用原因；未知项不能在总结中
  被省略成“未发现问题”。
- 导入页与索引公布已生成记录数、完成数、未知数、不适用数、待复核数及
  unsupported_components。full_candidate_count 仍为空，并明确提示尚未建立
  全板候选检查集合。这是当前分母的边界，不是覆盖率完成承诺。
- 注入评测把“资料不可解析”的预期改为 UNKNOWN，并保留这项检出验收。
  回归的未预期差分项不是总体误报率。

公开 mixed_controller_power_stage 当前样例：25 个器件，21 个有报告，0 个综合 PASS、
2 个综合 FAIL、19 个 UNKNOWN，另有4个档案缺口。生成146条检查记录：98 PASS、
4 FAIL、44 UNKNOWN、0 NOT_APPLICABLE；完成数102，仅为已生成的PASS+FAIL记录，
full_candidate_count 仍为空。组件与检查记录不是同一分母，也不是全板覆盖率或专家准确率。

## 未完成的产品门槛

完整候选检查集合和所有规则的精确依赖仍待完成。事务日志、同来源跨重启历史、
输入/规则版本失效及运行清单已实现；完整原文件所有权、可搬迁项目恢复仍缺失。
rule_version 字段不替代源码/档案指纹。已有器件族仍需完成 T03/T04：条件约束、
READY 档案逐字段复核，以及网名推断不能充当可信电压输入。DERIVED 说明规则
进行了推导，不单独证明推导前提正确。正式 AI 输出约束、真实 Windows/Cadence
导出和独立同行试用也未因本轮测试而完成。
