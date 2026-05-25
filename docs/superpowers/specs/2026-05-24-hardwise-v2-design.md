# Hardwise V2 — Component-centric, datasheet-driven schematic review

> Design spec for the V2 pivot. Produced via `superpowers:brainstorming` on 2026-05-24.
>
> **Next step:** an implementation plan should be derived from this doc via `superpowers:writing-plans`. The plan, not this spec, decomposes V2.1–V2.5 into ordered tasks.
>
> **Audience:** future Claude sessions executing V2, and the project author reviewing intent before code lands.

---

## 0. TL;DR

V1 已 ship: 5 mechanisms (Refdes Guard / Evidence Ledger / Sleep Consolidator / Tiered Routing / Prompt Caching) + R001-R003 跑通 KiCad pic_programmer (28 findings / 163 tests pass)。

V1 三个不满 (作者自诊断,不情绪化):

1. **平台错配** — 跑 KiCad,DJI 用 Allegro。
2. **per-rule 视角导致信噪比差** — 22 条 R003 NC findings 看起来"很多"但其实是 connector 噪音。
3. **视角错** — Report 是 rule-driven (按规则展开 findings),应该是 component-centric (以器件为主体,规则只是器件的属性)。

V2 三轴回应:

| 轴 | 做什么 | 落到代码 |
|---|---|---|
| 范式 | rule-driven → datasheet-driven | 新 `DatasheetProfile` + δ hybrid 抽表 + DS001 示例 check |
| 数据模型 | flat Finding list → Component 一等公民 | 新 `ir/` 模块 + 3 dataclass (Component / Pin / Net) + per-component check protocol |
| 架构 | KiCad-only → EDA-agnostic IR | 新 `adapters/allegro_netlist.py` 验证 IR 抽象,KiCad 是 reference impl |

V2 工期: 8-12 天 (Standard scope = B)。Slack 2-4 天 → 打磨 + demo 视频。

---

## 1. Context & motivation

### 1.1 V1 现状

- 主 demo `hardwise review data/projects/pic_programmer --rules R001,R002,R003` 跑通 28 findings,无 guardrail failure。
- Public smoke: 5 repos / 16 projects / 1707 components / 437 findings / 0 failures。
- `midpoint_review.md` (2026-05-16) 已盖章 "MVP 收束、停止扩张" — V2 必须明确说自己不是回到扩张模式。

### 1.2 V2 与 midpoint_review.md 的关系

midpoint_review 锁的是: 不再加新 rule、不再扩 corpus、不再做 product entry。

V2 不违反这些边界:

- V2 **不新增 active rule** (R004/R005/R006/R007 仍 V3+)。
- V2 引入的 DS001 是 **"datasheet-driven check 范式示例"**,不是 R004。其身份是"展示 V2 datasheet-driven 模式怎么落",不是开启 rule 扩张 sprint。
- V2 **不扩 corpus** — demo 仍 pic_programmer。
- V2 是**架构重构**,把现有 anti-hallucination + evidence 资产重新组织成 component-centric 视角。这是 midpoint_review 内部的合法演进。

V2 ship 后需在 `midpoint_review.md` 追加一节 "V2 关系说明",明确这一点。

### 1.3 Prior art 与边界

V2 借鉴的两个外部 reference,在 Credits 里同等抬载:

| Reference | 借的什么 | 不借的什么 |
|---|---|---|
| **erc.eda** | Component-centric 报告 6 节模板 + per-pin 4 象限 + ✅/⚠️/🔴 三态判定 + 左器件树/右详细报告 UI 布局 | 任何代码 (闭源)、纯 LLM 评审路径 (Hardwise 走 deterministic-first) |
| **Wrench Board** | 两层 refdes sanitizer 架构思想 | 代码 (NOASSERTION license)、多 agent 分解、boardview canvas、Managed Agents runtime |

Hardwise V2 与 erc.eda 的 4 轴差异化:

1. **Auditability** — 每条 finding 带 evidence token,可追溯。
2. **Anti-hallucination by design** — 两层 refdes guard 让"编位号"在结构上走不通。
3. **EDA-agnostic IR** — KiCad + Allegro netlist 两个 working adapter (V1 只有 KiCad)。
4. **Memory consolidation** — Sleep Consolidator 把 finding pattern 沉淀成 candidate rule (human gate)。

---

## 2. Locked design decisions

| ID | 决策 | 选项 |
|---|---|---|
| V2-D1 | V2 scope cut | **B Standard**: IR refactor + per-component checks + 1-IC RAG + Allegro netlist adapter。Net-level → V3。 |
| V2-D2 | IR shape | **A 分层 + 3 dataclass**: 新 `ir/` 在 `adapters/` 上层。Component / Pin / Net。Connection/Property 内嵌为 tuple/dict,不独立。 |
| V2-D3 | Check protocol | **M Per-component flip**: `ComponentCheck = (Component, Design) -> list[Finding]`。R001/R002/R003 outer loop 外提。 |
| V2-D4 | Datasheet model | **δ Hybrid**: 安全数据 (abs_max / recommended) 走 profile JSON;软文本 (pin function 描述) 走 search_datasheet RAG。 |
| V2-D5 | Demo IC + project | **L7805 on pic_programmer**: U3,datasheet 已 ingest,3 pins → 12-cell 4-quadrant report。 |
| V2-D6 | Second EDA adapter | **Allegro 第三方 ASCII netlist** (`$PACKAGES + $NETS` 段)。EDIF / IPC-2581 / EasyEDA Pro → V3+。 |
| V2-D7 | README opener | **R 问题领讲**: hardware-engineer 痛点 → 解法 → 三轴差异化 → Credits 同等抬载 erc.eda + Wrench Board。 |

---

## 3. Architecture

### 3.1 Module layout (V2 新/改)

```
src/hardwise/
  ir/                          # 新增
    __init__.py
    types.py                   # Pin / Component / Net / Design  (~150 lines)
    build.py                   # build_design() 聚合         (~80 lines)
    profile.py                 # DatasheetProfile + JSON I/O    (~60 lines)
  
  adapters/
    base.py                    # 不动 (ComponentRecord / BoardRegistry 保留)
    kicad.py                   # 不动
    kicad_pins.py              # 不动
    allegro_netlist.py         # 新增  (~250 lines)
  
  checklist/
    protocols.py               # 新增 ComponentCheck + CheckSpec (~50 lines)
    finding.py                 # 不动 (Finding / EvidenceStep 已存在,DR-009)
    loader.py                  # 不动 (RuleSpec yaml loader)
    checks/
      r001_*.py                # 改: outer loop 提出去 (~20 行 diff)
      r002_*.py                # 改: 同上
      r003_*.py                # 改: 同上
      ds001_vin_abs_max.py     # 新增 (datasheet-driven check 示例)
  
  report/
    markdown.py                # 不动 (V1 rule-driven 报告继续可用,默认开关)
    html.py                    # 不动
    component_centric.py       # 新增 6 节 markdown 渲染 (~200 lines)
    component_centric_html.py  # 新增 HTML 左树/右报告 (~180 lines)
  
  cli.py                       # 改: ingest-datasheet 加 --extract-profile flag
                                #     review 加 --report-style component-centric flag
                                #     review 自动认 Allegro netlist (kicad project 目录 vs .net 文件)
```

### 3.2 IR types — 最终形状

```python
# ir/types.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional
from hardwise.checklist.finding import Finding
from hardwise.ir.profile import DatasheetProfile


@dataclass
class Pin:
    number: str                   # "1", "A2"
    name: str                     # "VCC", "GND", "Vin"
    electrical_type: str          # 'power_in' / 'passive' / 'input' / 'output' / 'nc' / ...
    is_nc: bool                   # schematic NC flag
    net: Optional[str] = None     # net 名 (Allegro netlist 必填,KiCad pre-Layout 暂为 None)
    datasheet_function: Optional[str] = None       # 软文本检查阶段填
    findings: list[Finding] = field(default_factory=list)


@dataclass
class Component:
    refdes: str                   # 主键
    value: str                    # schematic value field
    package: Optional[str] = None
    part_number: Optional[str] = None              # 从 value 或 datasheet parse
    manufacturer: Optional[str] = None
    datasheet_path: Optional[str] = None
    datasheet_profile: Optional[DatasheetProfile] = None
    pins: list[Pin] = field(default_factory=list)
    properties: dict[str, str | None] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    decision: Optional[Literal['pass', 'warn', 'fail']] = None
    
    def pin_by_number(self, number: str) -> Optional[Pin]:
        return next((p for p in self.pins if p.number == number), None)
    
    def pin_by_name(self, name: str) -> Optional[Pin]:
        return next((p for p in self.pins if p.name == name), None)


@dataclass
class Net:
    name: str
    nodes: list[tuple[str, str]]              # (refdes, pin_number)
    is_power_rail: bool = False
    voltage_hint: Optional[float] = None      # V3 power rail audit 会用


@dataclass
class Design:
    components: dict[str, Component]          # refdes -> Component
    nets: dict[str, Net]
    project_path: Path
    source_eda: Literal['kicad', 'allegro_netlist']
    
    @property
    def refdes_set(self) -> set[str]:
        """Refdes Guard 兼容入口 — 不破坏 V1 BoardRegistry.refdes_set 的调用方式"""
        return set(self.components.keys())
```

**关键不变量:**

- Refdes Guard 通过 `Design.refdes_set` 拿到注册 refdes 集合 (语义与 `BoardRegistry.refdes_set` 等价)。
- Finding 模型完全不动 (DR-008 + DR-009 锁的形状)。
- `decision` 字段映射: `pass` → `✅ PASS`,`warn` → `⚠️ WARN`,`fail` → `🔴 FAIL`。

### 3.3 IR build flow

```python
# ir/build.py
def build_design(
    registry: BoardRegistry,
    pin_records: list[NcPinRecord],
    nets: Optional[dict[str, Net]] = None,
) -> Design:
    """KiCad 入口: 聚合 BoardRegistry + NcPinRecord -> Design"""
    components = {}
    for record in registry.components:
        pins = [_build_pin_from_nc(p) for p in pin_records if p.refdes == record.refdes]
        components[record.refdes] = Component(
            refdes=record.refdes,
            value=record.value,
            package=record.footprint,
            datasheet_path=record.datasheet,
            pins=pins,
            datasheet_profile=_try_load_profile(record),
        )
    return Design(
        components=components,
        nets=nets or {},
        project_path=registry.project_path,
        source_eda='kicad',
    )


def build_design_from_netlist(
    registry: AllegroNetlistRegistry,
) -> Design:
    """Allegro netlist 入口: 聚合 netlist 解析结果 -> Design"""
    ...
```

Datasheet profile 加载策略: V2.4 之前 `_try_load_profile()` 返回 None;V2.4 之后查 `data/datasheet_profiles/<part>.json`,有则加载,无则保持 None (DS001 check 自动跳过该 component)。

### 3.4 Allegro netlist adapter (V2.5)

**Format chosen:** Cadence 第三方 ASCII netlist (`$PACKAGES` / `$NETS` 两段)。

公开规范来源: Cadence Allegro PCB Editor user guide (第三方 netlist export 选项)。格式示例:

```
$PACKAGES
  ! 'C0805' ! C0805 ; C1 C2 C3
  ! 'SOIC8' ! SOIC8 ; U1 U2
$NETS
  'VCC' ; U1.8 C1.1 C2.1
  'GND' ; U1.4 C1.2 C2.2 C3.2
$END
```

**Parser shape:**

```python
# adapters/allegro_netlist.py
@dataclass
class AllegroPackage:
    package_name: str          # e.g. "C0805"
    device_name: str
    refdes_list: list[str]

@dataclass
class AllegroNet:
    name: str
    nodes: list[tuple[str, str]]   # (refdes, pin_number)

@dataclass
class AllegroNetlistRegistry:
    packages: list[AllegroPackage]
    nets: list[AllegroNet]
    source_file: Path
    refdes_set: set[str]           # 全 (refdes) 集合,Refdes Guard 兼容入口

def parse_allegro_netlist(path: Path) -> AllegroNetlistRegistry: ...
```

**V2 不做的事:**

- 不解析 .brd (二进制,业界无解,且 schematic-review 用不到)。
- 不解析 EDIF / IPC-2581 / OrCAD .DSN (V3+ adapter,文档化为扩展点)。
- 不做 datasheet 自动关联 (Allegro netlist 不带 datasheet 路径;V2 demo 仍用 pic_programmer 走 KiCad 路径)。

**Fixture:** 需在 GitHub 找一个 public Cadence Allegro project 的第三方 netlist 文件作 test fixture (BeagleBone / Pine64 / 某 open-hardware 项目)。如果找不到合规 fixture,手写一个最小合成 fixture (5-10 components,3 nets),并在 spec 注明 fixture 不来自真实板子。

### 3.5 Check protocol

```python
# checklist/protocols.py
from typing import Callable, Literal, Optional
from dataclasses import dataclass
from hardwise.ir.types import Component, Design
from hardwise.checklist.finding import Finding, Severity

ComponentCheck = Callable[[Component, Design], list[Finding]]


@dataclass
class CheckSpec:
    check_id: str                              # "R001" / "DS001"
    severity_default: Severity
    fn: ComponentCheck
    applies_to: Optional[Callable[[Component], bool]] = None
    description: str = ""
```

**R001 改造前后对比 (示意):**

```python
# 改造前 (V1):
def check_r001(registry: BoardRegistry, rule_spec: RuleSpec) -> list[Finding]:
    findings = []
    for c in registry.components:
        if not c.footprint:
            findings.append(Finding(rule_id="R001", refdes=c.refdes, ...))
    return findings

# 改造后 (V2):
def check_r001(c: Component, d: Design) -> list[Finding]:
    if c.package:
        return []
    return [Finding(rule_id="R001", refdes=c.refdes, ...)]

R001_SPEC = CheckSpec(
    check_id="R001",
    severity_default="medium",
    fn=check_r001,
    description="新建器件候选识别 (footprint 字段为空作为弱信号)",
)
```

**Runner (cli.py review 改造):**

```python
for component in design.components.values():
    for spec in active_specs:
        if spec.applies_to and not spec.applies_to(component):
            continue
        findings = spec.fn(component, design)
        component.findings.extend(findings)
        for f in findings:
            if f.pin_number:
                pin = component.pin_by_number(f.pin_number)
                if pin:
                    pin.findings.append(f)
        # decision 滚动逻辑: 任何 likely_issue -> component.decision = 'fail'
        # 否则任何 reviewer_to_confirm -> 'warn',否则 'pass'
        _roll_up_decision(component)
```

**R003 connector aggregation:** V1 的 connector NC 聚合逻辑作为 ComponentCheck 内的 post-process,行为 100% 保留 (V2.2 gate: pic_programmer 上输出仍 28 findings)。

### 3.6 Datasheet profile (δ hybrid)

**Schema:**

```python
# ir/profile.py
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json

@dataclass
class DatasheetProfile:
    part_number: str
    abs_max: dict[str, float | str]               # {'vin': 35.0, 'iout': 1.5, 'tj': 150}
    recommended: dict[str, float | str]           # {'vin_min': 7.0, 'vin_max': 25.0}
    pin_function: dict[str, str]                  # {'1': 'Vin (Input)', '2': 'GND', ...}
    evidence: dict[str, str]                      # {'abs_max.vin': 'datasheet:l78.pdf#p2'}
    extracted_at: str                             # ISO 8601
    extracted_model: str                          # 'mimo-v2.5'
    schema_version: str = "v1"
    
    @classmethod
    def load(cls, path: Path) -> 'DatasheetProfile':
        return cls(**json.loads(path.read_text()))
    
    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.__dict__, indent=2, ensure_ascii=False))
```

**Storage location:** `data/datasheet_profiles/<datasheet_basename>.json` (e.g. `data/datasheet_profiles/l78.json` from `data/datasheets/l78.pdf`)。git-tracked (作为 demo 资产)。

**Component → Profile lookup:** Component 的 `datasheet_path` (parsed 自 KiCad schematic property) 取 basename + 去后缀 → 拼到 profile 目录。例: `Component.datasheet_path = "datasheets/l78.pdf"` → 查 `data/datasheet_profiles/l78.json`。Profile 文件不存在 → `Component.datasheet_profile = None` → DS001 自动跳过该 component。不依赖 part_number 字段 (避免 schematic value 与 datasheet part_number 不一致问题,如 schematic value="7805" vs datasheet part_number="L7805")。

**V2 承诺的字段范围:** `abs_max` + `recommended` + `pin_function` 三块。其他字段 (application_circuit / thermal / packaging) → V3 候补,写到 `docs/rolling_log.md`。

**Extraction prompt (草稿):**

```
You are extracting structured electrical limits from a datasheet for use in 
automated schematic review.

Read the following datasheet text and return a JSON object matching this schema:
{
  "part_number": "<exact part number>",
  "abs_max": { "vin": <V>, "iout": <A>, "tj": <°C>, ... },
  "recommended": { "vin_min": <V>, "vin_max": <V>, ... },
  "pin_function": { "<pin_number>": "<one-line function description>" },
  "evidence": { "<json_path>": "datasheet:<filename>#p<N>" }
}

Rules:
- All numeric values in SI units (V, A, °C).
- If a value spans a range, use the most conservative (smaller for max, larger for min).
- Every numeric field MUST have a corresponding "evidence" entry citing the page.
- If a field is unknown, omit it. Do not guess.
- Output JSON only, no prose.

Datasheet text:
{chunks}
```

**Extraction failure handling:** profile.json 不写,DS001 check 跳过该 component。CLI 打印 warning,不 fail review。

**L7805 profile 预期内容 (V2.4 验收标准):**

```json
{
  "part_number": "L7805",
  "abs_max": {
    "vin": 35.0,
    "iout": 1.5,
    "tj": 150,
    "power_dissipation": "internally limited"
  },
  "recommended": {
    "vin_min": 7.0,
    "vin_max": 25.0,
    "iout_typ": 0.5
  },
  "pin_function": {
    "1": "Vin (Input)",
    "2": "GND (Ground)",
    "3": "Vout (5V Output)"
  },
  "evidence": {
    "abs_max.vin": "datasheet:l78.pdf#p2",
    "abs_max.iout": "datasheet:l78.pdf#p3",
    "abs_max.tj": "datasheet:l78.pdf#p2",
    "recommended.vin_min": "datasheet:l78.pdf#p4",
    "recommended.vin_max": "datasheet:l78.pdf#p4"
  },
  "extracted_at": "2026-05-2X T HH:MM:SS Z",
  "extracted_model": "mimo-v2.5",
  "schema_version": "v1"
}
```

### 3.7 DS001 check (datasheet-driven 示例)

```python
# checklist/checks/ds001_vin_abs_max.py
def check_ds001(c: Component, d: Design) -> list[Finding]:
    if not c.datasheet_profile:
        return []
    vin_max = c.datasheet_profile.abs_max.get('vin')
    if vin_max is None:
        return []
    vin_pin = c.pin_by_name('Vin') or c.pin_by_name('VIN') or c.pin_by_number('1')
    if not vin_pin:
        return []
    
    applied = _estimate_net_voltage(vin_pin.net, d)   # V2 简化: 启发式,V3 上 power rail audit
    if applied is None:
        return [_finding(c, 'reviewer_to_confirm', 
                         "无法从 schematic 推断 Vin 实际电压,需 reviewer 手动确认 ≤ %.1fV" % vin_max)]
    if applied > vin_max:
        return [_finding(c, 'likely_issue', 
                         "Vin=%.1fV 超过 abs max %.1fV,FAIL" % (applied, vin_max))]
    if applied > 0.8 * vin_max:
        return [_finding(c, 'reviewer_to_confirm',
                         "Vin=%.1fV 接近 abs max %.1fV (>80%%),reviewer 确认 derating" % (applied, vin_max))]
    return [_finding(c, 'likely_ok',
                     "Vin=%.1fV 在 abs max %.1fV 内 (<80%%),余量充足" % (applied, vin_max))]


def _finding(c, decision, message):
    return Finding(
        rule_id="DS001",
        severity="high" if decision == 'likely_issue' else "medium",
        refdes=c.refdes,
        message=message,
        decision=decision,
        evidence_chain=[
            EvidenceStep(source='datasheet', claim=f"abs_max.vin = {c.datasheet_profile.abs_max['vin']}V",
                         token=c.datasheet_profile.evidence['abs_max.vin']),
            EvidenceStep(source='eda', claim=f"Vin pin connected to net",
                         token=f"sch:{c.refdes}#pin1"),
        ],
        suggested_action="确认 application 电源轨电压,必要时调整 LDO 选型",
    )
```

**`_estimate_net_voltage` 启发式 (V2):**

1. 如果 net 名包含 "+5V" / "+3V3" / "VBUS" 等正则匹配的电压字符串 → 返回该电压。
2. 否则 → None (DS001 给 reviewer_to_confirm)。

V3 升级方向: power rail tracing (LDO/buck 输出 → 下游 net 电压传播)。不在 V2 范围。

### 3.8 Report 6 节 + per-pin 4 象限

每个 Component 输出 6 节,§5 内部 per-pin 4 象限。Markdown 模板:

```markdown
## U3 — L7805

### §1 基本信息
| 字段 | 值 |
|---|---|
| Refdes | U3 |
| Value | 7805 |
| Package | TO-220 |
| Part Number | L7805 (from datasheet) |
| Manufacturer | STMicroelectronics |
| Datasheet | `datasheet:l78.pdf` |

### §2 型号核对
✅ Schematic value `"7805"` matches datasheet L7805 family.
- Evidence: `sch:pic_programmer.kicad_sch#U3` + `datasheet:l78.pdf#p1`

### §3 引脚功能与连接关系
| Pin | Schematic name | Datasheet function | Net | NC |
|---|---|---|---|---|
| 1 | Vin | Vin (Input) | +12V | |
| 2 | GND | GND (Ground) | GND | |
| 3 | Vout | Vout (5V Output) | +5V | |

### §4 引脚一致性
- Pin 1 schematic `"Vin"` ≈ datasheet `"Vin (Input)"` ✅
- Pin 2 schematic `"GND"` ≈ datasheet `"GND (Ground)"` ✅
- Pin 3 schematic `"Vout"` ≈ datasheet `"Vout (5V Output)"` ✅

### §5 综合合规性 (per-pin 4 象限)

#### Pin 1 (Vin)
| 象限 | 状态 | 说明 | Evidence |
|---|---|---|---|
| a. 连接逻辑 | ✅ | 上游有 0.33uF 输入旁路 cap | `sch:...#C1` |
| b. 电气余量 | ⚠️ | Vapplied=+12V, Vrec_max=25V, Vabs_max=35V (DS001) | `datasheet:l78.pdf#p2,p4` |
| c. 外围器件 | ✅ | 输入 cap 0.33uF 符合 datasheet 推荐 | `datasheet:l78.pdf#p15` |
| d. 综合判定 | ⚠️ | 余量充足,reviewer 确认 application 不超 25V | |

#### Pin 2 (GND)
...

### §6 综合总结
**Decision: ⚠️ WARN**
- 🔴 严重错误: 0
- ⚠️ 设计错误: 0
- 💡 建议: 1 (Vin 边际确认)
- ❓ 数据缺失: 0
- ✨ 设计亮点: bypass cap 拓扑符合 application circuit
```

**HTML 渲染** (`report/component_centric_html.py`): 左侧 Component 树 (refdes 按 prefix 分组 U/C/R/D/J/...,内层按字典序),右侧详细报告,erc.eda 风格 layout。

**与 V1 报告共存:** V1 `report/markdown.py` (rule-driven) 保留可用,通过 `--report-style classic` 触发。新 `component-centric` 是 V2 默认。

---

## 4. Implementation slicing

V2 拆 5 个 sub-slice,每个独立 commit,每个结束跑通 `uv run pytest -q && uv run ruff check .`。Sub-slice 之间 commit boundary 严格按模块切 (CLAUDE.md 提交卫生)。

### V2.1 — IR foundation (1.5 天)

**新增:**
- `src/hardwise/ir/__init__.py`
- `src/hardwise/ir/types.py` (Pin / Component / Net / Design,无 DatasheetProfile 字段填值 — V2.4 才接)
- `src/hardwise/ir/build.py` (`build_design(registry, pin_records)`)
- `tests/ir/test_types.py` (3+ test: Pin/Component/Design 构造 + Design.refdes_set 兼容)
- `tests/ir/test_build.py` (1 test: pic_programmer → Design.components 长度 = 121)

**改动:** 无 (cli.py / runner.py / report 全不动 — V2.1 只引入新类型,旧路径不感知)。

**Gate:** Design 持有 pic_programmer 121 components × pins;V1 全部 163 tests 不退化。

### V2.2 — Per-component check flip (1.5 天)

**新增:**
- `src/hardwise/checklist/protocols.py` (ComponentCheck + CheckSpec)
- `tests/checklist/test_protocols.py` (4+ test: ComponentCheck 签名 + applies_to 过滤 + Runner outer loop + findings attach to component/pin)

**改动:**
- `checks/r001_*.py`、`checks/r002_*.py`、`checks/r003_*.py`: outer loop 外提,每个文件 ~20 行 diff,加 `R00X_SPEC` 导出。
- `cli.py:review`: 改 runner,用 `build_design()` + per-component check 循环。
- `checks/__init__.py`: 注册 CheckSpec 列表 (替代当前的函数列表)。

**Gate:** `hardwise review data/projects/pic_programmer --rules R001,R002,R003` 输出 finding 数与 V1 一致 (28 findings),0 guardrail failure;163+4 tests pass。

**回归 lock:** 在 `tests/e2e/` 写一个 snapshot test pin 住 V1 输出的 28 findings 列表 (rule_id + refdes 集合),任何后续 sub-slice 改动这一数必须显式 update snapshot 并写 learning_log。

### V2.3 — Component-centric report (2 天)

**新增:**
- `src/hardwise/report/component_centric.py` (markdown 6 节模板,~200 行)
- `src/hardwise/report/component_centric_html.py` (左树右报告 HTML)
- `tests/report/test_component_centric.py` (snapshot test: pic_programmer 应输出 N 个 Component 节,每节有 §1-§6 头)

**改动:**
- `cli.py:review`: 加 `--report-style {classic, component-centric}`,默认 `component-centric`。
- `report/__init__.py`: dispatch by style。

**Gate:** 默认 `hardwise review` 输出 component-centric 报告,121 components 全列;`--report-style classic` 仍出 V1 报告;HTML 双格式同步。

### V2.4 — Datasheet profile + DS001 (2-3 天)

**新增:**
- `src/hardwise/ir/profile.py` (DatasheetProfile dataclass + load/save)
- `src/hardwise/checklist/checks/ds001_vin_abs_max.py` (示例 datasheet-driven check)
- `data/datasheet_profiles/l78.json` (V2.4 验收时由 extract-profile 抽出,文件名 = datasheet basename)
- `tests/ir/test_profile.py` (3+ test: JSON round-trip + l78.json fixture load)
- `tests/checklist/test_ds001.py` (4+ test: profile 缺失跳过 + Vin 超 abs_max → fail + 0.8-1.0× → warn + <0.8× → pass)

**改动:**
- `cli.py:ingest-datasheet`: 加 `--extract-profile` flag,触发 LLM 抽表写 JSON。
- `cli.py:review`: 自动 load `data/datasheet_profiles/<part>.json` 填到 `Component.datasheet_profile`。
- `ir/build.py:_try_load_profile()`: 实现 (V2.1 stub → V2.4 真实)。

**Gate:**
1. `hardwise ingest-datasheet data/datasheets/l78.pdf --part-ref U3 --extract-profile` 产 `data/datasheet_profiles/l78.json`,abs_max.vin = 35.0 (±0.5 容差) 且 evidence 指向 `l78.pdf#p2`。
2. `hardwise review data/projects/pic_programmer --rules R001,R002,R003,DS001` 在 U3 上出 DS001 finding (decision = `reviewer_to_confirm` — 因为 pic_programmer 没声明 net 电压)。
3. U3 的 component-centric 报告 §5 Vin 行 4 象限显示 b 列 ⚠️ + DS001 evidence chain。

### V2.5 — Allegro netlist adapter (2-3 天)

**新增:**
- `src/hardwise/adapters/allegro_netlist.py` (parser + AllegroNetlistRegistry,~250 行)
- `src/hardwise/ir/build.py:build_design_from_netlist()` (~40 行 addition)
- `tests/adapters/test_allegro_netlist.py` (4+ test: $PACKAGES + $NETS parse + edge cases)
- Fixture: `tests/adapters/fixtures/sample_allegro.net` (公开来源或最小合成)

**改动:**
- `cli.py:review`: 输入路径检测 — 目录 → KiCad 路径;`.net` 文件 → Allegro netlist 路径。
- `cli.py:inspect-kicad`: 重命名 `inspect-eda`,通用化 (或保留 inspect-kicad 加新 inspect-allegro)。

**Gate:**
1. `hardwise review path/to/sample.net --rules R001,R002` (R003 暂跳过 — Allegro netlist 不带 NC 信息) 跑通,产 component-centric 报告。
2. Refdes Guard 在 Allegro netlist 上同样工作 (registry 验证 + sanitizer)。
3. `adapters/allegro_netlist.py` 4+ unit test 覆盖 (a) 标准 fixture parse、(b) 缺 $NETS 段、(c) 缺 $PACKAGES 段、(d) refdes_set 完整性。

**Scope safety:** V2.5 如果 4h 卡住 (parser 装不上 / fixture 找不到) → 退到 V2.0-4 ship,文档化 Allegro 为 V2.5+ stretch goal,B scope 退到 A scope (不影响 V2 主体上线)。

---

## 5. Test strategy

### 5.1 V1 回归保护

- V1 现有 163 fast tests + 7 slow tests 全部保留,V2 不允许 V1 测试失败。
- 新增 e2e snapshot test: `tests/e2e/test_v2_finding_count.py` — pin 住 pic_programmer 输出的 28 findings (rule_id + refdes set + decision set)。任何 sub-slice diff 改动该数必须显式 update。

### 5.2 V2 新增测试目标

| Sub-slice | 新增测试数 | 关键覆盖 |
|---|---|---|
| V2.1 | 5+ | Pin/Component/Net 构造、Design.refdes_set 兼容、build_design 121-comp、Finding attachment edge cases |
| V2.2 | 4+ | ComponentCheck 签名、applies_to 过滤、outer loop 行为、R001/R002/R003 改造后等价 |
| V2.3 | 4+ | Component-centric markdown snapshot、HTML snapshot、style switch、空 finding 时 6 节仍渲染 |
| V2.4 | 7+ | Profile JSON round-trip、L7805 fixture、DS001 三态 (pass/warn/fail)、profile 缺失跳过、extract-profile CLI |
| V2.5 | 4+ | Allegro netlist parse、build_design_from_netlist、Refdes Guard 兼容、review CLI 入口检测 |

V2 close 时 fast tests: 163 baseline + ~24 new = ~187。

### 5.3 Linting + format

每个 sub-slice 结束跑 `uv run ruff check . && uv run ruff format --check .`,必须 clean。

---

## 6. Out of scope — V3 候补

明确不在 V2 范围,写到 `docs/rolling_log.md` V3 触发条件:

- **Net-level review** (cross-component / power rail audit) — 需要 schematic-side net parser;midpoint_review 已 defer。
- **R004 I2C 地址冲突** — 跨器件 net-aware check。
- **R005 dangling nets** — net parser 依赖。
- **R006/R007 net naming** — net parser 依赖。
- **Profile schema 扩展** — V2 只承诺 abs_max + recommended + pin_function 三块。其他字段 (application_circuit / thermal / packaging / typical_current) → V3。
- **DS00X 其他 datasheet-driven check** — V2 只 ship DS001 一个示例。DS002+ 需要 V3 决定 schema 扩展后再加。
- **Allegro .brd binary parse** — 业界无解,Hardwise 不碰。
- **EDIF / IPC-2581 / OrCAD .DSN adapter** — 文档化为扩展点;Allegro netlist 是 V2 的"第二个 EDA"代表。
- **EasyEDA Pro adapter** — Q7 提到过的选项,V3+。
- **GitHub Action / PR comment bot / Web UI** — midpoint_review 已锁。
- **多 IC datasheet 同时 profile** — V2 只验证 L7805。Profile 路径走通后,加 IC 是用户行为不是开发任务。
- **Profile cache invalidation** — V2 profile 一旦写就用,无 hash-check 自动重抽。手动 `--re-extract` 在 V3 加。

---

## 7. README rewrite (V2 ship 后)

V2 implementation 走完后,0.5-1 天预算重写 `README.md`,结构按 V2-D7 R 锁定:

```markdown
# Hardwise

> A hardware schematic review agent built around two questions:
> what is the model allowed to say, and where does the evidence come from.

## §1 为什么
- 硬件 schematic review 里,一个 refdes 写错能带中千元级 BOM 损失。
- LLM 默认状态会自由生成 U999 这种不存在的位号。
- 反幻觉不能靠提示模型"别编" — 必须在结构上让"编"走不通。

## §2 Hardwise 怎么做
- Component-centric report (6 节模板,per-pin 4 象限)。
- 两层 Refdes Guard (tool 层 + sanitizer 层)。
- Datasheet-driven check (结构化 profile + deterministic 比对)。

## §3 三轴差异化
1. **Auditability** — 每条 finding 带 evidence token chain,可溯源。
2. **Anti-hallucination by design** — 两层 refdes guard 让"编"在结构上走不通。
3. **EDA-agnostic IR** — KiCad + Allegro netlist 共享同一 IR,新 EDA 是一个新文件。

## §4 Demo
[L7805 on pic_programmer 命令行 + 截图 + 视频]

## §5 Architecture
引到 `docs/architecture.md`。

## §6 Five mechanisms
Refdes Guard / Evidence Ledger / Sleep Consolidator / Tiered Routing / Prompt Caching。

## §Credits
- [erc.eda](https://erc.eda) — 报告 6 节结构与 per-pin 4 象限模板取经于此。
- [Wrench Board](https://github.com/Junkz3/wrench-board) — sanitizer 两层架构启发于此 (代码独立实现)。
```

中英文双版 (`README.md` + `README.zh-CN.md`) 同步。

---

## 8. Open follow-ups (V3 触发)

1. **Profile schema v2** — 加 application_circuit / thermal / packaging 字段。触发条件: 第二颗 demo IC (LT1373 或 switching reg) 加进 V3 时。
2. **Power rail tracing** — `_estimate_net_voltage` 启发式升级为 LDO/buck 输出 → 下游 net 电压传播。触发条件: net-level review 启动。
3. **R004 reactivation** — schematic-side net parser ship 后。
4. **第三个 EDA adapter** — EDIF 2.0.0 或 IPC-2581 (XML, Cadence 官方推动)。触发条件: 实际投递场景需要 OrCAD 兼容。
5. **Profile cache invalidation** — datasheet 文件 hash 比对,变更自动重抽。
6. **Sleep Consolidator V2** — 从纯统计聚合升级为 pattern extraction (rolling_log 已记)。

---

## 9. References

- `CLAUDE.md` — 项目硬规则,V2 不破坏其中任何条目。
- `docs/PLAN.md` — V1 slice 路径 + DR-001 to DR-009。V2 不替换 PLAN.md,在 PLAN.md 最后增加 "V2 pivot" 章节引到本 spec。
- `docs/architecture.md` — V2 ship 后 → v0.7,加 `ir/` 章节 + Component-centric report 章节。
- `docs/midpoint_review.md` — V2 ship 后追加 "V2 关系说明",声明 V2 不违反收束边界。
- `docs/review_node.md` — schematic-review node 定义,V2 不改 node 锚点。
- erc.eda — 报告结构 prior art。
- Wrench Board — sanitizer 架构 prior art (NOASSERTION license,仅借鉴思想)。

---

## 10. Change log

- 2026-05-24 — Initial spec,via `superpowers:brainstorming`。锁定 V2-D1 to V2-D7。
