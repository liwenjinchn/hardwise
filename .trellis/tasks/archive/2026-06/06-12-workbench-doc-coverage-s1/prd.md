# PRD — Workbench 规格书覆盖 S1：demo 喂入资料索引 + UI 显示覆盖状态

## 背景与问题

原理图评审的核心依据是规格书，但当前 demo 工作台上规格书能力完全不可见：

1. `serve-workbench` / `design-validator-ui` 均有 `--document-index` 参数，
   但 README 所有 demo 命令和 `scripts/start_hardwise_workbench.command`
   启动脚本都没有传，导致 `context.document_report = None`，每个器件的
   文档状态恒为 `not_configured`。
2. 后端 view model（`DocumentCoverageView`：status/title/url/source/
   candidates/reason）与候选搜索接口
   `/api/workbench/profile-gaps/{id}/datasheet-candidates` 已存在，
   但前端只有 `DetailColumn.tsx:108` 一个纯文本状态格，标题/链接/原因/
   候选都没有渲染，候选搜索接口在 UI 上不可达。
3. 仓库内三份 `data/document_indexes/*.csv` 都不覆盖 demo fixture
   （`mixed_controller_power_stage`）的料号。

用户长期方向（S2/S3，**不在本任务范围**，停放至 rolling_log）：
自动下载规格书、宽松自动放行、只把拿不准的交给工程师确认；闭源场景
provider 换成 PLM 按料号取附件。

## 本任务（S1）需求

R1. 新增 demo 资料索引
`data/document_indexes/mixed_controller_power_stage_docs.csv`，覆盖 demo
BOM 中的真实料号（L7805、XL1509-12E1、EG2132、STM32G030C8T6、
MBRA210LT3G，及可核验的 1N4007W / SS8050 / JMTK3005A）。每条 URL 必须
在实现时在线核验可达且为公开来源（制造商官网优先）；核验不过的料号
直接不写入（如实呈现为 no_result 覆盖缺口）。fixture 假料号
（CAP-100N / RES-* 等）不写入，让 demo 同时展示"有规格书"与"无规格书"
两种状态。

R2. demo 入口喂入索引
`scripts/start_hardwise_workbench.command` 和 README 中全部
`serve-workbench` / `design-validator-ui` demo 命令补
`--document-index data/document_indexes/mixed_controller_power_stage_docs.csv`。

R3. 前端渲染文档覆盖
- 器件详情（DetailColumn）：把单一状态文本升级为资料索引块——状态徽标
  （matched / no_result / ambiguous / manual_needed / not_configured）
  + 文档标题 + 来源 + 可点击 URL；未命中时显示 reason。
- 器件列表行展示文档状态徽标（数据已在 state 接口的器件行里），让
  覆盖情况一眼可扫。
- 不在本任务做候选搜索按钮 / 下载动作 / 审批操作（属 S2/S3）。

R4. 离线快照同样生效
`design-validator-ui --ai-snapshot --document-index ...` 烘焙出的静态
HTML 必须包含同样的覆盖展示（同一 view model，预期零额外后端代码）。

## 验收标准

- [ ] A1. `uv run hardwise serve-workbench <demo fixture> --fake-ai --document-index data/document_indexes/mixed_controller_power_stage_docs.csv --dry-run` 成功构建 context 且 document_report 非空。
- [ ] A2. 浏览器打开 demo 工作台：U1/U12/U3/U8 等器件详情显示 matched + 标题 + 链接；fixture 假料号显示 no_result + 原因。
- [ ] A3. 离线快照 HTML 同样显示上述覆盖状态（file:// 打开，无服务器）。
- [ ] A4. 索引 CSV 每条 URL 已在线核验（HTTP 可达、指向公开制造商/公开渠道页面或 PDF），核验结论记录在任务 research/ 下。
- [ ] A5. `uv run pytest -q`、`uv run ruff check .` 通过；`frontend/workbench`：`npm run typecheck`、`npm run test:unit` 通过，bundle 重新构建并提交。
- [ ] A6. README demo 命令与启动脚本均带 `--document-index`，文案说明覆盖状态含义；S2/S3 已停放至 `docs/rolling_log.md`。

## 边界（明确不做）

- 不做自动下载 / 自动放行 / 审批流（S2）。
- 不做工作台确认队列（S3）。
- 不接 PLM、不做在线供应商查询、不引入 `DATASHEETS_API_KEY` 依赖。
- 不提交 PDF 本体进 git（版权；仓库惯例只提交链接索引 CSV）。
- 不改 ValidationReport PASS/WARN/ERROR 真值，不改五工具契约。
