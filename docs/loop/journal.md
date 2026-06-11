# 自主循环 Journal — loop/workbench-hardening

> 每次迭代追加一条,格式:
> `日期时间 | 选了什么 | 结果(commit hash 或丢弃/STUCK/RED/ASK 原因) | 下一步意图`
>
> 本文件 + git log 是期末人工验收的主要材料。不删改旧条目。

## 迭代记录

- 2026-06-11 13:50 | 目标1首项:Playwright E2E 基建,把 handoff 手工冒烟清单
  全部条目(Q12/U8/U12 队列联动、U999→⟨?U999⟩、Prep Packet 预览、1440x900+
  760x900 无溢出)变成 5 条自动化断言;webServer 拉起 serve-workbench
  --fake-ai;一条命令 `npm --prefix frontend/workbench run test:e2e` 重跑 |
  commit 2e8e86c(E2E 5/5 绿 + pytest 598 绿 + ruff 干净;static 产物
  rebuild 哈希不变,src/hardwise 零改动) | 下一步:vitest 组件测试基建
  (目标1收尾),为目标2拆 App.tsx 做准备;候选切入点:formatSummary/
  状态标签纯函数与 StatusBadge/TrustBadge 等叶子组件先行测试

- 2026-06-11 14:06 | 目标1收尾:vitest 基建(node 环境,include 限
  src/**/*.test.*,与 Playwright 的 e2e/ 互不抢);导出 App.tsx 12 个纯函数
  并写 21 条单测(formatSummary 正则翻译含捕获组、queueSubtitle 拼装、
  evidenceNodeKind 三分类、各 label 映射与 fallback);新命令
  `npm --prefix frontend/workbench run test:unit` | commit 3cbd624
  (unit 21 绿 + E2E 5 绿 + pytest 598 绿 + ruff 干净;export 被
  tree-shaking,bundle 字节级不变) | 目标1两翼齐备,自检验收标准1已达。
  下一步进目标2:第一刀把已测纯函数挪到 src/lib/format.ts、
  StatusBadge/TrustBadge 等叶子组件挪到 src/components/,App.tsx 改 import,
  E2E+unit 守行为。注意:拆出组件的 vitest 需要 DOM 环境,jsdom 不在依赖
  白名单——届时优先用已测纯函数+E2E 覆盖,或标 ASK 问 jsdom

- 2026-06-11 14:26 | 目标2第一刀:纯函数→src/lib/format.ts(单测随迁为
  format.test.ts),9 个叶子组件(Metric/StatusBadge/TrustBadge/StatusIcon/
  VerdictBanner/InfoCell/EvidenceToken/EvidenceCard/CheckCard)→
  src/components/ui.tsx(命名对齐参考原型 ui.jsx);App.tsx 1356→1121 行,
  顺手删 countTaskEvidence 死代码 | commit 8bf41c6(typecheck+unit 21+
  E2E 5+pytest 598+ruff 全绿) | 关键决策:bundle 哈希首次变化,按验收4
  的 diff 范围,E2E 在新构建上验证后恢复 static 产物到 HEAD 再 commit;
  张力已记 learning_log(66a7af0),期末人工验收时统一刷新产物。
  下一步:继续拆 App.tsx——视图层切片,候选:Header+ImportView+ParseView
  →一个文件或各自文件,CopilotPanel、FindingsView+ExportView、
  TaskQueueColumn/DetailColumn/EvidenceColumn(Review 三栏)分批;每刀
  保持 ≤300 行/文件、全链绿

- 2026-06-11 14:45 | 目标2第二刀:非 Review 视图整体迁出 src/views/
  (nav.ts 承载 ViewId+NAV_ITEMS 防循环依赖;Header/ImportView+UploadSlot/
  ParseView/CopilotPanel/FindingsView/ExportView 原样搬移);App.tsx
  1121→619 行,清理无用 icon/api/type imports | commit 8a3c2bb(typecheck+
  unit 21+E2E 5+pytest 598+ruff 全绿;static 按产物策略恢复 HEAD) |
  下一步:最后一刀拆 Review 三栏——TaskQueueColumn+FILTERS、DetailColumn、
  EvidenceColumn+RiskHintsPanel → src/views/review/,App.tsx 应落到
  ≤300 行,验收标准2即自检达成;之后做期中盘点(各文件行数+四条验收
  逐条核)再决定是否进目标3 polish

- 2026-06-11 15:02 | 目标2最后一刀:Review 三栏迁出 src/views/review/
  (TaskQueueColumn+FILTERS / DetailColumn 含 prep packet 接线 /
  EvidenceColumn+私有 RiskHintsPanel);App.tsx 619→218 行,三刀合计
  1356→218 | commit dee10db(typecheck+unit 21+E2E 5+pytest 598+ruff
  全绿;static 恢复 HEAD) | 行数全景:循环触及的所有文件 ≤218 行;
  预存 types.ts 398 行——非 App.tsx 非新文件,判定在验收2范围外,留给
  人工决定。下一步:补验收2的"拆出组件有 vitest 覆盖"缺口——用
  react-dom/server renderToStaticMarkup 在 node 环境测 components/ui 与
  关键 views(零新依赖,绕开 jsdom 白名单问题),然后做期中盘点逐条核
  验收 1-4

- 2026-06-11 15:18 | 验收2收口:renderToStaticMarkup(node 环境零新依赖,
  绕开 jsdom 白名单)给全部拆出组件补 vitest——testing/fixtures.ts 共享
  构造器、ui.test.tsx 9 个原语、views.test.tsx 9 个视图初始渲染,
  format.test.ts 去重;单测 21→50 | commit 73e0906(unit 50+E2E 5+
  pytest 598+ruff 全绿) | 盘点后触发停止条件,见下方期末自检

## 期末自检(2026-06-11 15:20,迭代 6 后触发停止条件)

**结论:验收标准 1-4 全部通过;按停止条件第 1 条停止迭代,等待人工验收。**

1. **E2E 覆盖手工冒烟清单 ✅** — `npm --prefix frontend/workbench run
   test:e2e` 一条命令:build → Playwright webServer 拉起
   `serve-workbench --fake-ai` → 5 条断言对应 handoff 清单全部条目
   (Q12/U8/U12 队列联动详情+证据列、U999→⟨?U999⟩、Q12 Prep Packet
   预览、1440x900 与 760x900 无横向溢出)。最近一跑 5/5(10.5s)。
2. **拆出组件 vitest 覆盖 + 行数守卫 ✅** — 50 条单测覆盖
   lib/format(21)、components/ui 全部 9 原语(13)、全部 9 个拆出
   视图(16);App.tsx 1356→218 行,循环触及文件最大 218 行,全部
   ≤300。注:预存 types.ts 398 行,非 App.tsx 非新文件,判定在范围外,
   留人工裁决。
3. **每个落盘 commit 全链绿 ✅** — 6 次迭代 6 个实质 commit
   (2e8e86c→3cbd624→8bf41c6→8a3c2bb→dee10db→73e0906),每个都在
   build(含 typecheck)+ 新增测试 + pytest 598 + ruff 干净下落盘;
   零丢弃、零 STUCK/RED/ASK。离线 --ai-snapshot 路径由既有 pytest
   守住,无回归。
4. **diff 范围 ✅** — `git diff main...HEAD --name-only`(26 个文件)
   仅触及 frontend/workbench/**、docs/loop/**、docs/learning_log.md;
   src/hardwise/ 零改动(E2E 复用既有 serve-workbench,未需测试胶水)。

**留给人工验收的事项**:
- 已提交的 SPA 构建产物(src/hardwise/workbench/static/)按产物策略
  未刷新(详见 learning_log 2026-06-11 条目);合并时建议补一个独立
  build commit 刷新产物。
- types.ts(398 行,预存)是否拆分,人工决定。
- 依赖新增仅 @playwright/test 与 vitest(白名单内,devDependencies);
  Playwright chromium 二进制属契约允许的首次下载。
- 目标 3(polish)未启动:停止条件先于其触发,且无明确 polish 诉求。






