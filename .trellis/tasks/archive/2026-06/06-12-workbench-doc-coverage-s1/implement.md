# Implement — Workbench 规格书覆盖 S1

> 执行清单按序推进；每步完成后勾选。验证命令在每段末尾。

## 0. 准备

- [x] 从 `codex/hardwise-goal-workbench-intake` HEAD 切分支
      `feat/workbench-document-coverage`
- [x] `cd frontend/workbench && npm install`（如 node_modules 缺失）
      （node_modules 已存在，无需安装）

## 1. demo 资料索引 CSV

- [x] 逐条核验候选 URL（WebFetch / curl HEAD）：
      L7805(ST)、XL1509-12E1(XLSEMI)、EG2132(EG micro)、
      STM32G030C8T6(ST)、MBRA210LT3G(onsemi)、1N4007W、SS8050、JMTK3005A
- [x] 核验结论写 `research/url-verification.md`（每条：URL / HTTP 状态 /
      是否收录 / 理由）——收录 4 条，排除 4 条（onsemi 403 反爬、
      Rectron/UTC 路径不可发现、JMTK3005A 无可核验来源）
- [x] 写 `data/document_indexes/mixed_controller_power_stage_docs.csv`
      （列：MPN,Manufacturer,Title,URL,ReviewStatus,Source,LicenseNote；
      仅收录核验通过的料号）
- [x] 验证：`uv run hardwise serve-workbench
      tests/fixtures/allegro/mixed_controller_power_stage.net
      tests/fixtures/allegro/mixed_controller_power_stage_bom.csv
      --fake-ai --document-index
      data/document_indexes/mixed_controller_power_stage_docs.csv
      --dry-run` 成功（A1）——输出 document-index=on matched=4, no_result=11

## 2. demo 入口接线

- [x] `scripts/start_hardwise_workbench.command` 追加 `--document-index`
      （Windows 侧 `start_hardwise_workbench.ps1` 同步，保持双启动器等价）
- [x] README 全部 demo 命令块同步（README.md 5 处 + README.zh-CN.md 5 处）；
      补覆盖状态语义说明（双语各一段）
- [x] 验证：脚本内命令手工跑一遍 `--dry-run` 等价形式（mode=real，
      document-index=on matched=4）

## 3. 前端渲染

- [x] `DetailColumn.tsx`：资料索引块（徽标+标题+来源+外链+reason）
      —— 新增 `DocumentCoverageSection`，外链 `target="_blank" rel="noreferrer"`
- [x] 器件列表行：document_status 小徽标（`not_configured` 时隐藏）
- [x] `documentStatusLabel` 状态枚举补全（no_result/ambiguous/manual_needed）
      + 新增 `documentStatusGroup` 复用语义色
- [x] `testing/fixtures.ts` 补 document 样例（`makeDocument`）；
      `views.test.tsx` 补 matched / no_result 渲染断言 + 队列徽标断言；
      `format.test.ts` 补标签/分组断言
- [x] 验证：`npm run typecheck && npm run test:unit`（58 passed）

## 4. 构建 + 端到端确认

- [x] `npm run build`（输出到 src/hardwise/workbench/static，删旧增新：
      index-BEWCDZjX.js / index-Dn2THNGX.css）
- [x] live 模式确认（A2）：`--dry-run` 等价验证 matched=4；浏览器人工
      复核交给主会话（实现侧已用快照 HTML 验证同一 view model 渲染）
- [x] 快照模式确认（A3）：`design-validator-ui --ai-snapshot
      --document-index ... --output /tmp/s1-check.html`——HTML 内含
      matched 标题与 4×matched / 21×no_result 的 document_status
- [x] Python 测试如对 CLI 帮助文本/快照有断言则同步修正（全绿，无需修正）

## 5. 文档与停放

- [x] `docs/rolling_log.md` 新增条目："规格书自动获取 S2/S3"——
      S2：候选发现→自动下载（needs_review 默认态）→宽松自动放行
      （MPN 精确唯一命中即放行，含真实项目校准跑批：自动放行 N /
      需确认 M / 未命中 K 统计）；S3：工作台确认队列（复用 pin-table
      L1 review task 形状）；记录用户判断——主要风险是"找错规格书"
      而非"规格书内容不可信"，工程师确认量要尽量少；闭源时 provider
      换 PLM 按料号取附件
- [x] `docs/learning_log.md` 一条：功能存在但 demo 不可见的过程教训
      （Symptom/Root cause/Fix/Takeaway）

## 6. 收尾门槛

- [x] `uv run pytest -q` 全绿（671 passed, 7 deselected）
- [x] `uv run ruff check .` 干净
- [x] `npm run typecheck && npm run test:unit` 干净
- [ ] 提交拆分：feat(workbench) 前端+bundle / feat(documents 或 data)
      索引 CSV+入口 / docs(...) 文档（按域分仓，遵守 AGENTS.md 提交纪律）
      ——留给主会话执行（implement 代理不做 git commit）
- [x] 不 push（等用户授权）

## 回滚点

- CSV 与入口接线（步骤 1-2）独立可回滚，不影响现有行为。
- 前端改动回滚 = revert 源码 + 重新 build 一次旧 bundle。
