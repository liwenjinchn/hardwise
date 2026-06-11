# 自主循环 Journal — loop/backend-allegro

> 每次迭代追加一条,格式:
> `日期时间 | 轨道(A/B) | 选了什么 | 结果(commit hash 或丢弃/STUCK/RED/ASK 原因) | 下一步意图`
>
> 本文件 + git log 是期末人工验收的主要材料。不删改旧条目。

## 迭代记录

- 2026-06-11 | A | 首个网络级检查 `net_single_endpoint`(`validation/nets.py` + 6 测试):勘察确认 Design.nets 已有 (refdes,pin) 端点但零消费方;单端点网络报保守 WARN + `netlist:<file>#net=<NAME>` 证据 token;公开 fixture 真值锁定(mixed_controller_power_stage.net → ADC_POT/PWM1L 恰 2 条,pst → 0 条) | 绿 44eed81(604 passed,ruff 干净) | 下一步:CLI/report 接入 net 检查结果(让 finding 进现有报告通路),之后考虑电源轨识别(Net.is_power_rail 预留字段)
- 2026-06-11 | A | net 检查接入报告通路:ProjectValidationIndex 加 net_checks 字段(builder 用网表 basename 做 token 标签,绝对路径不进 token),markdown 报告加 Net Checks 节(有发现出表格/无发现出明示行),组件级 totals 不动 | 绿 8fc1a5f(607 passed,ruff 干净);一次测试断言过宽返工(发现既有行为:report 头部对仓库外路径显示绝对路径,系 display_path 既有语义,非本迭代引入,已收窄断言并注释) | 下一步:workbench 状态/UI 暴露 net_checks(view_model/server,涉及前端展示的部分留给前端轨),或先做电源轨识别充实检查族
- 2026-06-11 | A | workbench 状态层暴露 net_checks:WorkbenchState 加 net_checks(NetCheckView 镜像 CheckView 风格,l1 证据视图);evidence 分类器新认 `netlist:` scheme → design_source(与 sch/bom/drc/rule 同族);/api/workbench/state 与离线 snapshot 自动携带;SPA 渲染明确留给前端轨(API 契约先行,前端循环可消费 `state.net_checks`) | 绿 51b854d(609 passed,ruff 干净) | 下一步:电源轨识别(消费 Net.is_power_rail/voltage_hint 预留字段,复用 pins.is_ground_net/_voltage_from_net_name),让 net 检查族从 1 个长到 2-3 个;A 轨连续 3 迭代绿,暂不切 B
- 2026-06-11 | A | 检查族第 2 个:`design_missing_ground_net`(设计级缺地检查,WARN,token `netlist:<file>#nets=<count>`,空网表不判)。**计划修正**:勘察发现电源轨识别已被既有设施覆盖大半——POWER_NET_PATTERN(topology_tools)+ _voltage_from_net_name(pins)+ prep_summaries 候选电源网络草稿已存在,且 voltage_for_net 动态回退使 is_power_rail tagging 功能惰性,做了就是重复造;改做缺地检查(导出完整性真实信号,零重复)。公开 fixture 真值:2n3904_bjt_emitter_reference.net → 缺地 + 3 单端点;既有合成测试补 GND 网保持单一断言意图 | 绿 c2d38c0(612 passed,ruff 干净) | 下一步:切 B 轨开工(A 轨 4 连绿,检查族已 2 个 + 双通路接入,边际杠杆下降;B 轨黄金测试集是验收 #3 唯一缺口)——先勘察 component_identity.py/component_groups.py 既有分类逻辑,确定 unknown 分类的工作面和度量基线
- 2026-06-11 | - | **ASK #1**:迭代 4 提交后发现工作树出现非循环产生的改动——README.md / README.zh-CN.md / docs/demo_recording_script.md / docs/rolling_log.md(README 开头叙事段重写 + rolling_log +47 行),全部属于红线 #3 公开叙事文档,且出现在 loop/backend-allegro 检出上(语义上属于 main)。循环不提交、不丢弃这些文件,等人工处置。**安全调整**:此后所有"不绿则丢弃"一律限定到本迭代明确触碰的路径(git checkout -- <具体文件>),永不全局丢弃,避免误毁外部编辑 | 未决 | 人工处置前 B 轨开工照常,但 commit 一律显式列路径
- 2026-06-11 | B | B 轨第一刀:器件族分类扩容。基线实测:12 个真实形态(Y 晶振/F 保险丝/SW 开关/K 继电器/T 变压器/BT 电池/RP 排阻/VT/VD/IC 位号)11/12 落 unknown。新增 crystal/fuse/switch/relay/transformer/battery 六族(标准位号前缀 + 保守文本 token),既有族补 RP/RA/VT/VD/IC 前缀与 CHOKE/SCHOTTKY/RECTIFIER token;FAMILY_LABELS 补中文标签;黄金测试集 26 例锁定(unknown 12→0,既有分类回归锁死,子串陷阱防护:button cell→battery、gold contact→connector)。motor_sensor_controller fixture 两颗晶振 MPN 从 unknown 组迁入 crystal 组(verdict 无变化,纯分类分组迁移,CLI 测试断言同步) | 绿 3ee6411(638 passed,ruff 干净);commit 显式列路径绕开 ASK #1 外来文件 | 下一步:B 轨第二刀——unknown 计数下降的 index 级断言(合成 netlist+BOM fixture 走 build_project_validation_index,锁 gap group unknown 计数),或 pstchip JEDEC_TYPE 属性信号接入分类(勘察 allegro_pst properties 流到 BomItem/identity 的通路是否存在)
- 2026-06-11 | B | B 轨第二刀:index 级 unknown 下降断言落地——合成板(crystal/fuse/switch/ic/cap + 真不可识别 module)走完整 build_project_validation_index 通路,断言 unknown 组恰 1 个(改造前应为 4 个);**验收 #3 两个子项(黄金测试集 + 合成 fixture unknown 计数可复现断言)全部闭合**。顺带观察到既有怪癖:passive-value 正则宽松到把 "25MHz Crystal" 认成 passive_value identity(组身份取 value 而非 MPN,family 判定不受影响)——列为后续候选,不在本迭代修 | 绿 0dc7163(639 passed,ruff 干净);一次断言返工(identity 键假设 MPN,实测为 value,已注释说明) | 下一步:pstchip JEDEC_TYPE/properties 信号接入分类通路勘察;或回 A 轨把 net 检查族做到第 3 个(如电源轨名但零电压可解析的命名审查);ASK #1 仍未决

## 期末自检(2026-06-11,迭代 7 — 停止条件触发:验收标准 1–4 全部自检通过)

| 验收项 | 验证命令/方式 | 结果 |
|---|---|---|
| #1 独立 rule ID + source token | `nets.py` 含 `net_single_endpoint` / `design_missing_ground_net`;token 形态 `netlist:<file>#net=<NAME>` / `#nets=<count>`,经 evidence 分类器归 design_source | ✓ |
| #2 公开 fixture 可断言结果 | mixed_controller_power_stage(2 单端点)、pst(0)、2n3904_bjt_emitter_reference(缺地+3)真值写死;`pytest -k fixture` 3 passed | ✓ |
| #3 黄金测试集 + unknown 下降断言 | test_component_identity.py 27 passed:12 真实形态 unknown 11/12→0;index 级合成板 unknown 组 4→1 | ✓ |
| #4 每 commit 全绿 | journal 逐迭代自证;终态 `uv run pytest -q` **639 passed**(基线 598,+41),`ruff check` 干净 | ✓ |
| #5 公开叙事 diff 为空 | `git diff main...HEAD -- README.md ... docs/ :(exclude)docs/loop/*` → 空;"ready" 写入 grep 仅命中契约规则自身文本 | ✓ |

**交付摘要**:A 轨——网络级检查族从 0 到 2(`net_single_endpoint` / `design_missing_ground_net`),贯通 markdown 报告 + workbench API + 离线 snapshot,evidence 分类器学会 `netlist:` scheme;B 轨——器件族分类 +6 族(crystal/fuse/switch/relay/transformer/battery)+5 前缀映射,黄金测试集 26 例 + index 级断言。功能提交 5 个,全部绿;ASK 1 个未决(外来叙事编辑,等人工);RED 0;STUCK 0。

**未尽事项(下期候选)**:pstchip 属性信号接入分类;net 检查族第 3 个;passive-value 正则宽松怪癖;SPA 渲染 net_checks(归前端轨);ASK #1 处置。

**循环停止**。等待人工验收(验收方式见契约末节)。

---

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






