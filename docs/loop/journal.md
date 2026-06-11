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


