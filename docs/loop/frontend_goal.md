# Hardwise 自主循环目标契约 — 前端加固轨

> 本文件是无人值守循环的**唯一指令源**。每次迭代开始时:先重读本文件,再读
> `docs/loop/journal.md` 最后 3 条,然后自主选择本迭代的最高杠杆项。
> 这里只给目标范围和验收标准,不给具体任务清单——任务由循环自己拆。
>
> 期限:一期 7 天。期满或触发停止条件后,停止迭代,在 journal 写期末自检,
> 等待人工验收。

## 目标(高维):workbench 前端从"手工冒烟"变为"机器可验收"

现状(`docs/workbench_spa_handoff.md` 为准):功能面已主动关死("polish
only",backlog 全 Done 或 Defer);`frontend/workbench` 零测试(package.json
只有 tsc + build);行为验证靠手工浏览器冒烟;`src/App.tsx` 1356 行,违反
AGENTS.md ~300 行文件守卫。

目标范围,按依赖顺序:

1. **测试基建从零到一**:vitest 组件测试 + Playwright E2E,把 handoff 的
   手工冒烟清单变成自动化断言——组件队列点击(Q12/U8/U12)联动详情与证据
   列、Copilot 未知位号 `U999 → ⟨?U999⟩`、Prep Packet 预览可开、1440x900 与
   760x900 双分辨率无横向溢出。E2E 后端用
   `serve-workbench tests/fixtures/allegro/mixed_controller_power_stage.net
   tests/fixtures/allegro/mixed_controller_power_stage_bom.csv --fake-ai`。
2. **测试保护下拆分巨石**:App.tsx 拆到单文件 ≈≤300 行,纯结构性重构,
   行为不变,由第 1 步的测试守住。
3. (仅当 1、2 完成后)同等保护标准下的小幅 polish;**不加新功能、不重
   设计视觉**。

## 验收标准(机器可验;期末逐条核)

1. Playwright E2E 覆盖上述手工冒烟清单全部条目,且可用一条命令本地重跑。
2. 拆出的组件有 vitest 覆盖;`App.tsx` 及新文件均 ≈≤300 行。
3. 每个落盘 commit 满足:`npm --prefix frontend/workbench run build`(含
   typecheck)绿 + 新增测试命令绿 + `uv run pytest -q` 全绿 +
   `uv run ruff check .` 干净(离线 `--ai-snapshot` 路径由 pytest 守住,
   不回归)。
4. 期末 `git diff main...HEAD` 只触及 `frontend/workbench/`、`docs/loop/`、
   `docs/learning_log.md`,以及为接 E2E 必需的最小测试胶水。

## 迭代纪律

- 一次迭代 = 选项 → 实现 → 验证 → **绿则 commit,不绿则丢弃改动**回到上个
  绿点,两种结局都写 journal。
- commit 信息沿用仓库惯例(`test(workbench): ...` / `refactor(workbench): ...`)。
- 惊奇/坑写 `docs/learning_log.md`(Symptom / Root cause / Fix / Takeaway)。
- journal 每条格式:`日期时间 | 选了什么 | 结果(commit hash 或丢弃原因) |
  下一步意图`。

## 调度规则

- 严格按目标顺序 1 → 2 → 3,前项验收不达不进后项。
- 同一难点耗超约 4 小时或连续 3 次迭代无绿色 commit → journal 标记
  `STUCK`,换同目标内的另一个切入点;无切入点可换 → 停止等人工。

## 红线(任何一条都不可越;越线 = 立即停止并在 journal 标记 RED)

1. `docs/workbench_spa_handoff.md` "Implementation Boundaries" 全文有效:
   不改 deterministic PASS/WARN/ERROR 逻辑;不把外部 risk hints 混入
   deterministic verdicts;不向浏览器暴露 API key / 模型凭据;Refdes Guard
   保持可见且被测;普通 `design-validator-ui` 与 risk-hints 路径保持可用;
   `--ai-snapshot` 保持走 SPA 离线快照路径;不提交本地截图。
2. 依赖变更仅限测试工具白名单:vitest / @testing-library/* / playwright
   及其类型包,只进 devDependencies;其余依赖增删 → journal 标记 `ASK`。
3. 不加新功能、不做视觉重设计;Defer 清单(PLM/供应链/计分等)永不实现。
4. 绝不 `git push` / 创建 PR / 任何对外发布动作。
5. 不改 README、docs/ 公开叙事文档、AGENTS.md、CLAUDE.md(`docs/loop/` 和
   `docs/learning_log.md` 除外);不动 `src/hardwise/`(除非 E2E 必需的最小
   测试胶水,且 pytest 全绿)。
6. 需要真实 API key 或网络外呼的验证(playwright 浏览器二进制首次下载除外)
   → 不做,标记 `ASK`。

## 停止条件

- 验收标准 1–3 全部自检通过(写期末自检后停止);
- 或 7 天期满;
- 或 STUCK 无切入点 / 触发 RED / 累计 3 个 ASK 未决。

## 期末人工验收方式(供循环自检对齐)

- 本地起 `serve-workbench --fake-ai`,一条命令跑 E2E,看冒烟清单替代成立。
- journal 自证每个 commit 绿;人工抽查重跑 build + pytest。
- diff 范围审计(验收标准 4)。
