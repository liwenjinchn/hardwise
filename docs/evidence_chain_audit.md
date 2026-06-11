# 证据链边界说明

> 首次梳理：2026-05-31。2026-06-05 在 d3a/d3b 验证器迁移合入 `main` 后复核
> （器件档案从 C4 集合增长到 25 个）。
>
> 目的：把"真实入库/检索/AI 引用证明过的"与"人工审核过的结构化档案出处"
> 分开。

## 摘要

Hardwise 目前有一条完整冒烟过的规格书检索链：

```text
data/datasheets/l78.pdf
  -> ingest/pdf.py
  -> store/vector.py (Chroma, 157 块)
  -> query-datasheet / search_datasheet
  -> AI 回答引用 l78.pdf 第 4 页
```

结构化器件档案里的其它 `datasheet:<part>.pdf#pN` 引用大多是人工审核过的
档案出处。它们是有用的 L1 确定性验证器证据，但除非对应的公开 PDF 已本地
入库并查询过，否则不应被描述成实时 Chroma 检索。

## 冒烟命令

```bash
rm -rf /tmp/hardwise-evidence-audit

uv run hardwise ingest-datasheet \
  data/datasheets/l78.pdf \
  --part-ref L7805 \
  --persist-dir /tmp/hardwise-evidence-audit

uv run hardwise query-datasheet \
  "absolute maximum input voltage" \
  --top-k 3 \
  --persist-dir /tmp/hardwise-evidence-audit

uv run hardwise ask \
  data/projects/pic_programmer \
  "请先用 search_datasheet 查询 L7805 absolute maximum input voltage，再回答 U3 的 Vin absolute maximum 来自哪一页；如果没有检索证据就明确说没有。" \
  --vector \
  --persist-dir /tmp/hardwise-evidence-audit \
  --max-iterations 4 \
  --trace
```

## 实测输出

`ingest-datasheet` 为 `part_ref=L7805` 创建了 157 个分块。

`query-datasheet` 返回的第一名命中：

```text
1. [l78.pdf p4 part=L7805] L78 Maximum ratings ... Absolute maximum ratings ... 35...
```

`hardwise ask --vector` 发起了两次工具调用：

```text
1. search_datasheet({"part_ref": "L7805", "query": "L7805 absolute maximum input voltage", "top_k": 5}) -> hits=5
2. get_component({"refdes": "U3"}) -> status=found
```

最终回答引用了 `l78.pdf` 第 4 页，并报告了 35 V 绝对最大输入电压这条事实。
这证明：在配置了向量库的前提下，AI 可以引用检索到的规格书证据。

轨迹同时报告了 `unverified refdes wrapped: 4`，因为 `L78`、`L7805` 这类
长得像料号的字符串会命中保守的位号正则。板上对象 `U3` 始终是台账校验过的；
这种包裹是料号在展示层的已知取舍，不是规格书检索的失败。

## 证据分类

| 证据类别 | 例子 | 当前状态 | 表述规则 |
|---|---|---|---|
| 实时检索证据 | `search_datasheet` 返回的 `[l78.pdf p4 part=L7805]` | 已由上面的冒烟证明 | 可以说"入库 -> 检索 -> AI 引用" |
| 审核档案出处 | `l78.json` 里的 `datasheet:l78.pdf#p4` | 人工审核过的结构化档案事实 | 可以说 L1 档案证据；只有单独冒烟后才提 Chroma 检索 |
| 审核出处、PDF 未本地入库 | `datasheet:mpq8626.pdf#p1`、`datasheet:bas316.pdf#p2`、`datasheet:stm32g030.pdf#p33`（完整列表见下方档案台账） | 在当前仓库状态下只是档案证据 | 不暗示实时检索；称为人工审核过的公开档案证据 |
| 覆盖/排序产物 | C3/C4 `recommend-next-family` 输出行 | 规划辅助 | 作为支撑材料，不作为 AI 能力的主张 |

## 当前本地 PDF 清单

只有 `data/datasheets/l78.pdf` 在本地暂存（已 gitignore）。不存在已提交或
本地的 Chroma 库（`data/chroma/` 不存在且已 gitignore）；L78 冒烟入库到
一次性的 `--persist-dir`。其它每个档案引用的公开规格书出处，其 PDF 都不在
`data/datasheets/` 下，也没有入库到任何 Chroma 库。

## 完整档案台账（2026-06-05 复核，25 个档案，全部 `review_status: ready`）

一个档案有真实 PDF 支撑；其余是人工审核过的公开档案证据。

| 类别 | 数量 | 档案 |
|---|---|---|
| **真实 PDF 支撑**（PDF 在本地 + 实时检索冒烟过） | 1 | `l78.json`（`l78.pdf` p3/p4/p6） |
| **审核出处、无本地 PDF**（`datasheet:<file>.pdf#pN`，PDF 不在本地） | 22 | `2n3904`、`74lv165`、`bas316`、`connector_2x5`、`eg2132`、`ina180a1`、`irf540n`、`l2n7002klt1g`、`lm393`、`lmv358`、`ln2312lt1g`、`mmbt3904`、`mpq8626`、`pca9548a`、`pca9617a`、`sd103aws_7_f`、`sm340af`、`smbj24ca`、`ss34`、`stm32g030c8t6`、`tlv9062`、`xl1509` |
| **非 PDF 出处**（构造即合成） | 2 | `1_5smc15a`（`datasheet:..._product_page#...`）、`ltst-c190kgkt`（`public_profile:...#...`） |

22 个审核出处档案使用的 `datasheet:<file>#pN` 字符串形态，与
`ingest/pdf.py:evidence_token()` 为实时检索分块生成的形态**完全相同**。这个
共享形态正是过度声称的风险点：脱离证据类别展示出处，会被读成实时检索。
只有 L78 端到端冒烟过。首次梳理之后加入的 d3a/d3b 器件族（`mpq8626`、
`pca9548a`、`pca9617a`、`ln2312lt1g`、`l2n7002klt1g`、`sd103aws_7_f`、
`sm340af`、`74lv165`、`1_5smc15a` 等）是人工审核过的公开档案证据，不是实时
检索——与最初 C4 集合遵守同一条规则。

## 对叙事的含义

先讲信任架构：

```text
位号防护 + 证据台账 + L1 确定性验证器 + 结构化工具
```

再用覆盖闭环做支撑证明：

```text
C3 排序 -> C4 器件族切片 -> 人工行变成确定性行
```

不要只用覆盖数字开头，也不要说每个档案出处都来自实时检索。最强且诚实的
说法是：

> L78 有完整的入库/检索/AI 引用冒烟；其它 24 个档案（C4 器件族加 d3a/d3b
> 新增）是人工审核过的公开档案证据，进入确定性验证器。
