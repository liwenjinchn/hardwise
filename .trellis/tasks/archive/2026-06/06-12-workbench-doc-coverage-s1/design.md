# Design — Workbench 规格书覆盖 S1

## 总体判断

后端管线已完整，本任务是"接线"任务：数据（新 CSV）→ 入口（CLI 参数补传）
→ 展示（前端渲染升级）。预期 Python 侧零或极少代码改动。

## 数据流（现状，全部已存在）

```
--document-index CSV
  → documents/index.py parse_document_index()
  → documents/matcher.py match_documents_to_bom(bom, index)   # MPN 优先，part-like value 兜底
  → workbench/context.py WorkbenchContext.document_report
  → workbench/view_model.py _document_view()                  # 每器件 DocumentCoverageView
  → GET /api/workbench/state（器件行含 document_status）
    GET /api/workbench/components/{refdes}（详情含 document 完整对象）
  → 离线快照：同一 view model 烘焙进静态 HTML
```

断点只有两处：入口不传 CSV；前端不渲染。

## 改动点

### 1. `data/document_indexes/mixed_controller_power_stage_docs.csv`

列沿用现有索引惯例：`MPN,Manufacturer,Title,URL,ReviewStatus,Source,LicenseNote`
（参考 `data/datasheets/mpq8626-approved-docs.csv` 与
`documents/index.py` 解析的可选列）。每行 `ReviewStatus=approved`，
`Source` 写实际来源域名，`LicenseNote` 写"Public datasheet"类说明。

候选料号与 URL 核验策略：
- 制造商官网优先（st.com / xlsemi.com / egmicro.com / onsemi.com）。
- 实现时逐条 WebFetch/HTTP 核验：2xx 且内容与料号匹配才收录。
- 核验失败的料号不收录（demo 如实显示覆盖缺口），结论记录在
  `research/url-verification.md`。

### 2. demo 入口

- `scripts/start_hardwise_workbench.command`：`serve-workbench` 命令追加
  `--document-index "$DOC_INDEX"`（变量与 NETLIST/BOM 同样式）。
- README：所有 `serve-workbench` / `design-validator-ui` demo 块同步追加；
  在工作台介绍段补一句覆盖状态语义（matched/no_result/...）。

### 3. 前端（frontend/workbench，React+Vite，build 输出到
`src/hardwise/workbench/static`）

- `types.ts`：`DocumentCoverageView` 等类型已存在，预期不动。
- `views/review/DetailColumn.tsx`：把 line 108 的单一 InfoCell 升级为
  资料索引小节——状态徽标 + title + source + 外链（`target="_blank"
  rel="noreferrer"`）+ 未命中 reason。状态→样式映射沿用工作台现有
  徽标/语义色体系（与验证状态徽标同一套组件，避免新视觉语言）。
- 器件列表（TaskQueueColumn 或对应器件索引列）：每行加文档状态小徽标，
  数据用 state 器件行已有的 `document_status` 字段。
- `documentStatusLabel()` 已存在；如缺状态枚举则补全中文标签。
- 测试：`views.test.tsx` / `ui.test.tsx` 按现有模式补 matched 与
  no_result 两个渲染断言；fixtures.ts 补 document 字段样例。

### 4. 构建与提交物

`npm run build`（含 tsc --noEmit）重建 bundle；
`src/hardwise/workbench/static/assets/*` 哈希文件名会变化，旧文件删除、
新文件提交（仓库现状即提交构建产物）。

## 兼容性

- 不传 `--document-index` 时一切照旧（document=null → not_configured），
  现有测试不受影响。
- 离线快照与 live 服务共用 view model，前端从同一 JSON 形状读取，
  无双轨逻辑。

## 风险与对策

- 公开 URL 会腐烂 → CSV 是 reviewed trust boundary，本来就要求人工
  维护；核验结论留档 research/，坏链只影响 demo 跳转不影响功能。
- 前端 bundle 与 PR #3 改过的 import 流冲突 → 本任务分支基于当前
  branch HEAD（含 PR #3 全部提交），无冲突窗口。
- npm 环境缺失 → implement 阶段先 `npm install`；e2e（playwright）
  浏览器未装则跳过 e2e，以 typecheck+unit 为门槛（与 A5 一致）。

## 分支

`feat/workbench-document-coverage`，基于
`codex/hardwise-goal-workbench-intake` 当前 HEAD（含 Windows 修复与
pin-table 前端改动）。PR 目标 main，待 PR #3 合并后提（历史兼容）。
