# Hardwise Rolling Log

> Scheduled improvements queued behind specific code milestones. When the trigger ships, knock the corresponding TODO off this file and move the content to its destination (usually CLAUDE.md or docs/architecture.md).
>
> This file exists because the editorial rule on CLAUDE.md and README.md forbids "TODO: add later" placeholders — those would be temporal framing. Park the TODOs here instead.
>
> Format per entry: **Trigger** / **Where it lands** / **What to add**.

---

## Triggered by Slice 5 — KiCad schematic net parser shipping (R005 dangling-nets)

**Where it lands**: `data/checklists/sch_review.yaml` → R005 (dangling / unexpected unconnected schematic nets), R006 (通用 net 命名规则), and R007 (分类 net 命名规则).

**What to add**: 123.md 第 5 章 (脱敏后的某硬件团队原理图规范) 提炼出的 net naming convention，作为 candidate rules 待 **schematic-side** net parser 上线后才可执行。PCB-side `pcb_nets` 不能作为 pre-Layout schematic-review evidence，因为评审节点还没有 `.kicad_pcb`。

**R006 — 通用 net 命名规则**（123.md §5.1 / §5.10 / §5.12）

| 子项 | 规则 |
|---|---|
| 字符集 | `[A-Z0-9_]` only；禁止小写、特殊字符、双下划线 `_ _` |
| 后缀 | `_N` 表示低电平有效（如 `RST_N`、`CS_N`） |
| 长度 | ≤ 32 字节 |
| 地网络 | 数字 `GND` (不显示)；模拟 `AGND1/AGND2` (显示)；机壳 `EGND` (显示) |

Check 逻辑（伪代码）：`re.fullmatch(r"[A-Z0-9_]+(?<!_)(?<!__)", net_name)` 且 `len(net_name) <= 32`；不符 → `severity=medium, action=按命名规范重命名`。

**R007 — 分类 net 命名规则**（123.md §5.2–§5.9）

| 类别 | 模式 | 例 |
|---|---|---|
| 时钟 single-ended | `CLK_<freq>_<receiver>` | `CLK_33M_ICH` |
| 时钟 differential | `CLK_<freq>_<rcv>_DP[N]/DN[N]` | `CLK_100M_SATA_DP0` |
| 复位 | `RST[_T][_R]_<fn>[_N]` | `RST_PCH_PLTRST_N` |
| 电源 | `P<voltage>[_STBY/DUAL][_<rcv>]` | `P3V3_STBY`, `P12V_CPU0` |
| 总线 PCIe | `<T>_PCIE<width>_P<port>` | `CPU0_PCIE16_P0` |
| 总线 I2C | `<T>_I2C<n>_{SDA,SCL}` | `CPU0_I2C0_SDA` |
| 差分 | `_DP/_DN` 放在 net 名最后；总线时跟编号 | `SATA_DP0` |
| 串联端接后 | net 流出串阻后加 `_R`，流出耦合电容后加 `_C` | `CLK_33M_R`, `DDR_DQ0_C` |

Check 逻辑：按 prefix 路由到不同 regex；任何"看起来像但不符合"（如 `clk_33m_ich`、`CLK33M`、`POWER_5V`）→ `severity=medium, action=按分类命名规范重命名`。

**为什么不在 Slice 3 实现**：

1. 需要 KiCad schematic net parser：wire 连通、local/global label 合并、power symbol 合并、hierarchical label 跨页传播、symbol pin endpoint 映射到 `refdes/pin`；Slice 3 只做到 pin parser，Slice 5 task 3 目前只完成了 **PCB-side diagnostic parser**（读 `.kicad_pcb`），不能作为 pre-Layout 证据；
2. 公开 demo 项目 `pic_programmer` 用的是 KiCad 默认 net 命名（如 `Net-(D1-Pad1)`），不遵守 123.md 这套企业级规范，强行套用会输出大量 false positive；
3. 这两条规则的真实价值在企业级项目，pic_programmer 等公开 demo 跑不出有意义的结果，但代码逻辑可单测覆盖。

**先决条件 (planned)**：KiCad **schematic** net 解析能产出 `list[SchematicNetRecord(name, refdes_pin_list, source_labels, source_wires)]`。最小可行版本先支持同一 sheet 内 wire 连通、local/global label 合并、power symbol 合并、symbol pin endpoint 映射；hierarchical sheet 可第二步补。R005/R006/R007 只能吃这份 schematic-side 输入。

**安全边界**：R006/R007 的规则原文来自 123.md（脱敏后的某硬件团队原理图规范文件）；命名规则本身是行业通用做法（PXX 表电源、CLK_ 表时钟、差分 P/N 后缀），不携带任何具体项目代号 / 客户名 / 料号 / 内部系统名。

---

## Triggered by Day 2–3 — KiCad parser shipping

**Where it lands**: `CLAUDE.md` → new "Layout" section (between Stack and Models).

**What to add**: A directory tree like Wrench Board's, one line per directory. Should cover at minimum:

```
src/hardwise/
  adapters/          EDA boundary; one file per format. KiCad first, Cadence later.
  ingest/            File → store glue (PDF chunk, EDA → SQL).
  store/             Two stores: relational (refdes/nets/BOM/DRC) + vector (datasheet chunks).
  agent/             Tool-use loop, tier routing, prompts, tool manifest.
  guards/            Two-layer anti-hallucination: refdes guard + evidence ledger.
  memory/            Sleep Consolidator + candidate-rule pool (rules.md).
data/                Local input — KiCad projects + datasheet PDFs (gitignored except .gitkeep).
docs/                architecture.md / interview_qa.md / learning_log.md / rolling_log.md.
reports/             Generated review reports (markdown, gitignored).
```

Move the trigger off this file once shipped.

---

## Triggered by Day 4 — both stores wired up

**Where it lands**: `CLAUDE.md` → new "On-disk layout" section (after Layout).

**What to add**: Mirror Wrench Board's `memory/{device_slug}/` schema for Hardwise:

```
data/projects/{project_slug}/   # KiCad project files (input, gitignored)
data/datasheets/                # Public PDFs (input, gitignored, shared across projects)
data/hardwise.db                # SQLite — schema in src/hardwise/store/relational.py
data/chroma/                    # Chroma local persistence
reports/{project_slug}-{YYYYMMDD}.md     # Generated review report
src/hardwise/memory/rules.md             # Candidate rule pool (committed; small)
```

Document the slug rule, the timestamp format, and which files are gitignored vs committed.

---

## Triggered by Day 5 — CLI commands beyond `hello`

**Where it lands**: `CLAUDE.md` → new "CLI surface" section (after Run/test/lint).

**What to add**: Subcommand table.

```
| Command | What it does |
|---|---|
| hardwise ingest <project_path> | Parse KiCad + datasheets, populate both stores. |
| hardwise review <project_slug> | Run agent loop, write markdown report to reports/. |
| hardwise consolidate <report> | Extract candidate rules into memory/rules.md. |
| hardwise hello | Sanity check the install. |
```

Lock command names only after the third subcommand ships; renaming early is cheap, late is expensive.

---

## Triggered by Day 7 — first review report generated end-to-end

**Where it lands**: `CLAUDE.md` → new "Architectural anti-rules" subsection inside "Hard rules".

**What to add**: Concrete "do not" rules learned from running the loop in anger. Candidate items to watch for:

- "Do not let the agent generate refdes without a tool call." (You'll see it try.)
- "Do not put datasheet content in the relational DB; do not put refdes in the vector store." (The temptation is to denormalize when something is slow.)
- "Do not promote candidate rules without the human gate." (The Sleep Consolidator will look so reliable you'll want to skip review.)
- "Do not let the report exceed N pages." (Whatever N turns out to be when reviewers actually read it.)

Each anti-rule must reference a real moment when reality tried to violate it. Anti-rules pulled out of thin air are noise; anti-rules from a near-miss are gold.

---

## Discharged improvements (keep for audit)

> When an item moves out of this file, leave a one-line entry below noting where it landed.

- 2026-05-13 — "first tool registered in `agent/tools.py`" trigger landed → `CLAUDE.md` gained a "Tool manifest" section (between Models and Run/test/lint); 4 tools shipped (`list_components` / `get_component` / `get_nc_pins` / `search_datasheet`) with the `closest_matches` discriminated-union pattern replacing the original `get_net / check_bom / lookup_drc` placeholder shape. Names drifted as predicted; manifest reflects the actual Slice 3 store surface.
- 2026-05-14 — Slice 5 task 3 landed as a **scope correction**: the implemented net reader is PCB-side diagnostic infrastructure, not the schematic net parser required for pre-Layout review.
  - **Parser / `BoardRegistry.pcb_nets` / `store/relational.py pcb_nets+pcb_net_members`**: full KiCad PCB truth — 111 nets on `pic_programmer` (34 signal + 77 `unconnected-(Ref-Pad)`). Underlying layers never drop info, but this data comes from `.kicad_pcb` and is therefore **post-Layout evidence only**.
  - **CLI `inspect-kicad --net`**: now labelled `PCB-side net summary`; default view shows 34 PCB signal nets and `--all-nets` flips to the full 111 to match KiCad's PCB Net Inspector. Header prints `pcb nets: 34 signal (+77 unconnected = 111 total in PCB)` plus `source: .kicad_pcb (post-Layout fact; not pre-Layout review evidence)`.
  - Helper: `hardwise.adapters.kicad.pcb_signal_nets(pcb_nets)` — keep the unconnected-* filter KiCad/PCB-specific.
  - Test lock: parser stores `pcb_nets == 111` + 34 signal partition; SQLite round-trip 111 with GND member count = 40; CLI default vs `--all-nets` E2E asserts both source label and listing membership. `pytest -q` 144 passed; `ruff check .` clean.
  - Follow-up: add a synthetic `.kicad_pcb` unit test that explicitly lights both net syntaxes handled by `_pad_net_name()`; `pic_programmer` only gives implicit coverage for whichever KiCad version generated the fixture.
  - R005/R006/R007 remain queued above because they need a real schematic net parser: wire + local/global label + power symbol + hierarchical label + symbol pin endpoint resolution from `.kicad_sch`.
