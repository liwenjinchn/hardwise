# Hardwise 自主循环目标契约 — 后端双轨

> 本文件是无人值守循环的**唯一指令源**。每次迭代开始时:先重读本文件,再读
> `docs/loop/journal.md` 最后 3 条,然后自主选择本迭代的最高杠杆项。
> 这里只给目标范围和验收标准,不给具体任务清单——任务由循环自己拆。
>
> 期限:一期 7 天(/loop 循环任务自动过期即期满)。期满或触发停止条件后,
> 停止迭代,在 journal 写期末自检,等待人工验收。

## 目标 A(高维):Allegro 侧网络级确定性检查从 0 到有

`src/hardwise/adapters/allegro_pst.py` 已解析 pstxnet 网络+引脚端点,
`src/hardwise/adapters/allegro_netlist.py` 已解析 Telesis 连接关系——原理图侧
网络事实已经存在,但仓库中没有任何网络级确定性检查消费它。

目标范围:让悬空网络 / 单端点网络 / 电源轨识别 / NC 引脚与网络冲突这一类
**R004/R005 式网络级检查**在公开/合成 Allegro fixture 上产出带证据出处的
findings,并接入现有 report / workbench 通路。具体做哪几类检查、什么顺序、
怎么建模,由循环自行判断杠杆。

## 目标 B(高维):unknown 器件的确定性分类显著提高

压力测试结论:主板样例板 unknown 1118 位号 / 957 组,"主要是导入/分类工作"。
仓库内没有那两块板的导出(它们只在本机 /tmp),所以本轨道的工作面是:

- 用 refdes 前缀 + BOM 身份 + pstchip 属性等**确定性证据**做器件族分类;
- 自建带已知真值的合成 fixture 来度量和回归分类能力;
- 器件档案产物只进 `ReviewStatus=candidate` 草稿队列,**永不写 ready**。

## 验收标准(机器可验;期末逐条核)

1. 每个新检查有独立 rule ID(不与既有 R001–R003 / 验证器族冲突),每条
   finding 带 source token(沿用既有证据 token 形态)。
2. `tests/fixtures/allegro/mixed_controller_power_stage.net` + BOM 等公开
   fixture 上,新检查产出**可断言的确定结果**(测试里写死期望行数/内容)。
3. 分类器有黄金测试集;合成 fixture 上 unknown 计数下降在测试中可复现断言。
4. 每个落盘的 commit 都满足:`uv run pytest -q` 全绿 + `uv run ruff check .`
   干净;新代码有自己的测试。
5. 期末 `git diff main...HEAD -- README.md docs/`(除 `docs/loop/`)为空。

## 迭代纪律

- 一次迭代 = 选项 → 实现 → 验证 → **绿则 commit,不绿则丢弃改动**(`git
  checkout -- .` / `git clean -fd` 回到上个绿点),两种结局都写 journal。
- commit 信息沿用仓库惯例(`feat(validation): ...` / `test(adapters): ...`)。
- 文件守卫:新文件 ~300 行内;越界就拆。
- 惊奇/坑照 AGENTS.md 纪律写 `docs/learning_log.md`(Symptom / Root cause /
  Fix / Takeaway)。
- journal 每条格式:`日期时间 | 轨道 | 选了什么 | 结果(commit hash 或丢弃
  原因) | 下一步意图`。

## 调度规则

- 双轨并行持有,单迭代只做一轨。
- 一轨连续 3 次迭代无绿色 commit,或在同一难点上耗超约 4 小时 → 强制切换
  另一轨,并在 journal 标记 `STUCK`。
- 两轨都 STUCK → 停止,journal 写明卡点,等人工。

## 红线(任何一条都不可越;越线 = 立即停止并在 journal 标记 RED)

1. 只用仓库内公开/合成 fixture 或自建合成数据;**绝不引用、模拟、重建任何
   公司内部硬件数据**,合成 fixture 的真值必须在测试中自我说明。
2. 绝不 `git push` / 创建 PR / 任何对外发布动作。
3. 不改 README、docs/ 公开叙事文档、AGENTS.md、CLAUDE.md(`docs/loop/` 和
   `docs/learning_log.md` 除外)。
4. 不改既有 deterministic verdict(PASS/WARN/ERROR)语义;新检查只新增。
5. 器件档案 ReviewStatus 永不写 ready;"人工审核"状态只能由人写。
6. 不加 Wrench Board 被拒功能;不进 `.brd` / boardview / placement / routing
   / PCB geometry / PLM / 价格 / 供应链范围(AGENTS.md 边界)。
7. 依赖增删、单迭代删除 >100 行既有代码、需要真实 API key 或网络外呼的
   验证 → 不做,journal 标记 `ASK` 等人工。

## 停止条件

- 验收标准 1–4 全部自检通过(写期末自检后停止);
- 或 7 天期满;
- 或双轨 STUCK / 触发 RED / 累计 3 个 ASK 未决。

## 期末人工验收方式(供循环自检对齐)

- journal 自证每个 commit 绿;人工抽查重跑 `uv run pytest -q`。
- 验收标准逐条在 fixture 上跑命令验证断言。
- 红线审计:diff 范围检查 + grep 不出 ready 写入。
