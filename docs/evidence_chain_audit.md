# 证据链边界说明

> 首次梳理：2026-05-31。2026-06-05 在 d3a/d3b 验证器迁移合入 `main` 后复核
> （器件档案从 C4 集合增长到 25 个）。
> 2026-06-18 追加 U12 / XL1509 公开 PDF ingest、retrieval、Workbench trace 冒烟。
> 2026-06-19 台账对账：档案增长到 30 个（新增 5 个 audited、尚未检索冒烟）。
>
> 目的：把"真实入库/检索/AI 引用证明过的"与"人工审核过的结构化档案出处"
> 分开。

## 摘要

Hardwise 目前有两条完整冒烟过的规格书检索链：

```text
data/datasheets/l78.pdf
  -> ingest/pdf.py
  -> store/vector.py (Chroma, 157 块)
  -> query-datasheet / search_datasheet
  -> AI 回答引用 l78.pdf 第 4 页

public XLSEMI XL1509-EN.pdf -> /tmp/xl1509.pdf
  -> ingest/pdf.py
  -> store/vector.py (Chroma, 38 块)
  -> query-datasheet / search_datasheet
  -> Workbench Copilot trace 引用 xl1509.pdf 第 11 页和第 9 页
```

结构化器件档案里的其它 `datasheet:<part>.pdf#pN` 引用大多仍是人工审核过的
档案出处。它们是有用的 L1 确定性验证器证据，但除非对应的公开 PDF 已入库并
查询过，否则不应被描述成实时 Chroma 检索。

## 冒烟命令

### L78 / KiCad ask

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

### XL1509 / U12 Workbench trace

```bash
curl -L --fail --output /tmp/xl1509.pdf \
  http://www.xlsemi.com/datasheet/XL1509-EN.pdf

uv run hardwise ingest-datasheet \
  /tmp/xl1509.pdf \
  --part-ref XL1509-12E1 \
  --persist-dir /tmp/hardwise-xl1509-evidence

uv run hardwise query-datasheet \
  "XL1509-12 output 12V feedback inductor 68uH 150uH" \
  --top-k 8 \
  --persist-dir /tmp/hardwise-xl1509-evidence

uv run hardwise query-datasheet \
  "Schottky Diode Selection Table XL1509 1N5821" \
  --top-k 8 \
  --persist-dir /tmp/hardwise-xl1509-evidence

uv run hardwise serve-workbench \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --fake-ai \
  --document-index data/document_indexes/mixed_controller_power_stage_docs.csv \
  --vector \
  --persist-dir /tmp/hardwise-xl1509-evidence \
  --port 58306

curl -s http://127.0.0.1:58306/api/workbench/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"datasheet XL1509-12 output 12V feedback inductor 68uH 150uH evidence","selected_refdes":"U12","history":[]}'

curl -s http://127.0.0.1:58306/api/workbench/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"datasheet Schottky Diode Selection Table XL1509 1N5821 evidence","selected_refdes":"U12","history":[]}'
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

XL1509 公开 PDF 验证为 13 页，SHA-256：

```text
d0226589787aa1ec629f0a1365aec4e017799ae79594891fa48f7733b4c1ebc2
```

`ingest-datasheet` 为 `part_ref=XL1509-12E1` 创建了 38 个分块。

固定 12 V 输出 / 电感问题的 `query-datasheet` 命中包括：

```text
[xl1509.pdf p11 part=XL1509-12E1] Typical System Application for 12V Version ... L1 68uH/2A ... D1 1N5821 ...
[xl1509.pdf p7 part=XL1509-12E1] Fixed Output Voltage Versions ...
[xl1509.pdf p8 part=XL1509-12E1] Selecting the Inductor ... 12V ... 68 ... 150 ...
[xl1509.pdf p5 part=XL1509-12E1] XL1509-12 Electrical Characteristics ... VOUT ... 12 ...
```

Schottky / freewheel diode 问题的 `query-datasheet` 命中包括：

```text
[xl1509.pdf p9 part=XL1509-12E1] Schottky Diode Selection Table ... 1N5820 ... 1N5821 ... 1N5822 ...
```

Workbench fake-AI 服务经由真实 Runner、真实工具和真实 Refdes Guard 返回 HTTP 200。
针对 U12 的两个目标问题，trace 至少包含 L2 检索证据：

```text
search_datasheet -> L2 evidence: datasheet:xl1509.pdf#p11, datasheet:xl1509.pdf#p7, datasheet:xl1509.pdf#p5
search_datasheet -> L2 evidence: datasheet:xl1509.pdf#p9, datasheet:xl1509.pdf#p2
```

U12 的确定性器件验证由 CLI 报告单独复核，继续保持 `ERROR`，并把两条器件级错误
绑定到更精确的档案证据页：

```text
Buck 电感 -> L1=6.8 uH below 68 uH -> datasheet:xl1509.pdf#p8
Buck 续流二极管 -> D5=1N4007W not Schottky -> datasheet:xl1509.pdf#p9
```

## 证据分类

| 证据类别 | 例子 | 当前状态 | 表述规则 |
|---|---|---|---|
| 实时检索证据 | `search_datasheet` 返回的 `[l78.pdf p4 part=L7805]`、`[xl1509.pdf p11 part=XL1509-12E1]` | 已由上面的冒烟证明 | 可以说"入库 -> 检索 -> AI/Workbench 引用" |
| 审核档案出处 | `l78.json` 里的 `datasheet:l78.pdf#p4`、`xl1509.json` 里的 `datasheet:xl1509.pdf#p8/#p9` | 人工审核过的结构化档案事实；其中 L78 和 XL1509 已有额外检索冒烟 | 可以说 L1 档案证据；只有单独冒烟后才提 Chroma 检索 |
| 审核出处、PDF 未本地入库 | `datasheet:mpq8626.pdf#p1`、`datasheet:bas316.pdf#p2`、`datasheet:stm32g030.pdf#p33`（完整列表见下方档案台账） | 在当前仓库状态下只是档案证据 | 不暗示实时检索；称为人工审核过的公开档案证据 |
| 覆盖/排序产物 | C3/C4 `recommend-next-family` 输出行 | 规划辅助 | 作为支撑材料，不作为 AI 能力的主张 |

## 当前本地 PDF 清单

只有 `data/datasheets/l78.pdf` 在 repo 工作区本地暂存（已 gitignore）。
XL1509 这次 proof 使用 `/tmp/xl1509.pdf` 和一次性的 `/tmp/hardwise-xl1509-*`
向量库；PDF 没有提交到 repo，也没有放进 `data/datasheets/`。不存在已提交的
Chroma 库（`data/chroma/` 不存在且已 gitignore）。

## 测试门禁边界

`uv run pytest -q` 默认带 `-m 'not slow'`（见 `pyproject.toml`），会**排除** 7 个
slow 测试——其中 `tests/store/test_vector.py` 的 4 个正是真实 Chroma 入库→检索
集成（招牌的规格书检索路径），另 3 个是 Postgres round-trip。所以默认绿灯的
“NNN passed” 并不覆盖实时向量检索；要端到端跑这条链，用
`uv run pytest -m slow`（需安装 `chromadb`）。这与上文“只有 L78 / XL1509 端到端
冒烟过”一致：默认快测试集证明确定性逻辑，真检索集成单独按需运行。

## 完整档案台账（2026-06-19 复核，30 个档案，全部 `review_status: ready`）

两个档案有真实 PDF 检索冒烟支撑；其余是人工审核过的公开档案证据。

| 类别 | 数量 | 档案 |
|---|---|---|
| **真实 PDF 检索冒烟支撑** | 2 | `l78.json`（`l78.pdf` p3/p4/p6）、`xl1509.json`（`xl1509.pdf` p5/p8/p9/p11） |
| **审核出处、尚未检索冒烟**（`datasheet:<file>.pdf#pN`） | 26 | `1n4007w`、`2n3904`、`74lv165`、`bas316`、`connector_2x5`、`eg2132`、`ina180a1`、`irf540n`、`jmtk3005a`、`l2n7002klt1g`、`lm393`、`lmv358`、`ln2312lt1g`、`mbra210lt3g`、`mmbt3904`、`mpq8626`、`pca9548a`、`pca9617a`、`pe537ba`、`sd103aws_7_f`、`sm340af`、`smbj24ca`、`ss34`、`ss8050`、`stm32g030c8t6`、`tlv9062` |
| **非 PDF 出处**（构造即合成） | 2 | `1_5smc15a`（`datasheet:..._product_page#...`）、`ltst-c190kgkt`（`public_profile:...#...`） |

> 2026-06-19 对账：`data/datasheet_profiles/` 实际 30 个档案。相对 2026-06-05
> 复核新增 5 个 audited（尚未检索冒烟）档案——`1n4007w`、`jmtk3005a`、
> `mbra210lt3g`、`pe537ba`、`ss8050`，均带 `datasheet:<file>.pdf#pN` 审核出处，
> 归入"审核出处、尚未检索冒烟"类，不暗示实时检索。

26 个尚未检索冒烟档案使用的 `datasheet:<file>#pN` 字符串形态，与
`ingest/pdf.py:evidence_token()` 为实时检索分块生成的形态**完全相同**。这个
共享形态正是过度声称的风险点：脱离证据类别展示出处，会被读成实时检索。
目前只有 L78 和 XL1509 端到端冒烟过。首次梳理之后加入的 d3a/d3b 器件族（`mpq8626`、
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

> L78 和 XL1509 有完整的入库/检索/AI 或 Workbench 引用冒烟；其它 28 个档案
> 是人工审核过的公开档案证据，进入确定性验证器，但不能说成实时 Chroma 检索。
