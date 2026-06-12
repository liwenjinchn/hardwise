# 调研：工作台规格书功能为何不可见（2026-06-12 主会话排查结论）

> 本文件是 S1 的事实基础，implement/check 子代理直接引用，不需重新排查。

## 三个断点（已逐一核实）

### 断点 1：demo 入口从不传 `--document-index`

- `serve-workbench`（cli.py ~1493）与 `design-validator-ui`（cli.py ~1321）
  都有 `--document-index` 选项，帮助文本完整。
- README 行 55 / 131 / 141 / 312 / 318 的 demo 命令、
  `scripts/start_hardwise_workbench.command` 启动脚本：全部没传。
- 不传 → `workbench/context.py:144-146` 跳过
  `match_documents_to_bom(...)` → `document_report=None` →
  `view_model.py:1163-1165 _document_view()` 返回
  `DocumentCoverageView(status="not_configured",
  reason="No document index was provided.")`。

### 断点 2：前端几乎不渲染

- 后端形状齐全：`view_model.py:300` 详情含 `document` 完整对象；
  `view_model.py:448` 器件行含 document status；`view_model.py:1275`
  有"资料索引"标签；`server.py:227` 有
  `/api/workbench/profile-gaps/{group_id}/datasheet-candidates`
  候选搜索接口（datasheets.com provider，需 `DATASHEETS_API_KEY`）。
- 前端 `frontend/workbench/src/types.ts` 类型契约已存在
  （`DocumentCoverageView`、`document_index_enabled`、`document_status`）。
- 但唯一消费点是 `views/review/DetailColumn.tsx:108`：
  `<InfoCell label="文档索引" value={documentStatusLabel(...)} />`，
  纯状态文本；title/url/source/reason/candidates 全部未渲染；
  候选搜索接口零调用（已 grep 构建产物确认 0 命中）。

### 断点 3：下载被人工审批前置（设计如此，S2 才改）

CLI 四步管线：`search-datasheets-com` / `build-document-index-candidates`
→ 人工把 CSV 行标 `approved` → `fetch-approved-documents`（只下
approved 行，SHA 寻址缓存，`documents/cache.py`）→
`draft-datasheet-profile`（needs_review 草稿）。
S1 不动这条管线。

## 实现要用的关键事实

- 前端源码：`frontend/workbench/`（React 19 + Vite 7 + TS5，
  `npm run build` 输出 `../../src/hardwise/workbench/static`，
  构建产物按现状提交进 git；有 vitest 单测与 playwright e2e）。
- demo BOM（`tests/fixtures/allegro/mixed_controller_power_stage_bom.csv`）
  真实料号：U1=L7805(ST)、U12=XL1509-12E1(XLSEMI)、U3=EG2132(EG)、
  U8=STM32G030C8T6(ST)、D1=MBRA210LT3G(Onsemi)、D5=1N4007W、
  Q12=SS8050、Q1/Q2=JMTK3005A；其余为 fixture 假料号（CAP-100N、
  RES-* 等，保持无文档即可）。
- 索引 CSV 解析：`documents/index.py`；列名宽容，现有样例
  `data/datasheets/mpq8626-approved-docs.csv`
  （MPN,Manufacturer,Title,URL,ReviewStatus,Source,LicenseNote）。
- 匹配：`documents/matcher.py match_documents_to_bom` — MPN 精确优先，
  part-like value 兜底，可选 manufacturer 收窄；状态枚举
  matched / no_result / ambiguous / manual_needed。
- 信任边界：索引 CSV 即"已审核"边界（AGENTS.md：仅公开来源）；
  `documents/cache.py` 刚修过 Windows 盘符 bug（194be33），单字母
  scheme 按本地路径处理——写 URL 核验脚本时无需绕路。

## S2/S3 方向记录（用户 2026-06-12 口头决策，停放 rolling_log）

- 自动放行从宽：主要风险是"找错规格书"（错料号匹配），不是"规格书
  内容不可信"；工程师确认量尽量少。
- 放行判据基线：MPN 归一化精确匹配 + 唯一无歧义命中 → 自动放行；
  多候选 / 模糊命中 / 仅 value 兜底命中 → 工程师确认队列。
- S2 落地时用用户的真实项目跑批校准，输出
  "自动放行 N / 需确认 M / 未命中 K"。
- 闭源演进：provider 接口（datasheets_com.py 同形状）换 PLM——按料号
  搜索、取附件规格书；状态枚举沿用。
