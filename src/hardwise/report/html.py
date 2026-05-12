"""Render review findings as a self-contained HTML report."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from html import escape
from typing import Any

from hardwise.checklist.finding import Finding

_SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")
_SEVERITY_LABELS = {
    "critical": "严重",
    "high": "高风险",
    "medium": "需确认",
    "low": "低风险",
    "info": "提示",
}
_STATUS_LABELS = {"open": "待确认", "accepted": "已接受", "rejected": "已驳回", "closed": "已关闭"}
_PIN_TYPE_LABELS = {
    "passive": "无源",
    "input": "输入",
    "output": "输出",
    "bidirectional": "双向",
    "power_in": "电源输入",
    "power_out": "电源输出",
}

_STYLE = """
:root{color-scheme:light;--ink:#18201c;--muted:#64706b;--line:#d9ded6;--paper:#f7f4ec;--panel:#fffdf7;--rail:#24352f;--accent:#c4482e;--copper:#b47035;--blue:#2d6f83;--green:#4f7c58;--shadow:0 18px 50px rgba(35,44,38,.12);--mono:"SFMono-Regular","Cascadia Code","Liberation Mono",monospace;--sans:"Avenir Next","Segoe UI","Helvetica Neue",sans-serif;--serif:"Iowan Old Style","Palatino Linotype",Georgia,serif}
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(90deg,rgba(36,53,47,.06) 1px,transparent 1px),linear-gradient(0deg,rgba(36,53,47,.045) 1px,transparent 1px),var(--paper);background-size:34px 34px;color:var(--ink);font-family:var(--sans);line-height:1.45}
main{width:min(1180px,calc(100% - 32px));margin:0 auto;padding:40px 0 56px}
.sheet{background:rgba(255,253,247,.92);border:1px solid var(--line);box-shadow:var(--shadow)}
.hero{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(280px,.85fr);min-height:300px;border-bottom:1px solid var(--line)}
.title-block{position:relative;padding:38px 42px 34px;border-left:10px solid var(--rail);overflow:hidden}
.title-block:after{content:"";position:absolute;inset:auto 0 0 auto;width:44%;height:8px;background:linear-gradient(90deg,var(--accent),var(--copper),var(--blue))}
.eyebrow{margin:0 0 18px;color:var(--muted);font-family:var(--mono);font-size:12px;text-transform:uppercase}
h1{margin:0;max-width:760px;font-family:var(--serif);font-size:clamp(38px,6vw,78px);line-height:.96;font-weight:700}
.project-path{margin:24px 0 0;color:var(--muted);font-family:var(--mono);font-size:13px;overflow-wrap:anywhere}
.meta{display:grid;grid-template-columns:1fr 1fr;border-left:1px solid var(--line);background:#fbfaf4}
.metric{min-height:150px;padding:24px;border-right:1px solid var(--line);border-bottom:1px solid var(--line)}
.metric:nth-child(2n){border-right:0}
.metric span{display:block;color:var(--muted);font-family:var(--mono);font-size:11px;text-transform:uppercase}
.metric strong{display:block;margin-top:10px;font-family:var(--serif);font-size:44px;line-height:1}
.metric code{display:block;margin-top:12px;font-family:var(--mono);font-size:12px;color:var(--muted);overflow-wrap:anywhere}
.summary{display:grid;grid-template-columns:minmax(260px,.9fr) minmax(0,1.1fr);border-bottom:1px solid var(--line)}
.panel{padding:28px 34px;border-right:1px solid var(--line)}
.panel:last-child{border-right:0}
h2{margin:0 0 18px;font-size:17px;font-weight:700}
.chips{display:flex;flex-wrap:wrap;gap:10px}
.chip{display:inline-flex;align-items:center;gap:8px;min-height:34px;padding:7px 10px;border:1px solid var(--line);background:#fffaf0;font-family:var(--mono);font-size:12px}
.chip b{color:var(--ink);font-size:14px}
.sanitizer{margin:18px 0 0;color:var(--muted);font-family:var(--mono);font-size:12px}
.findings{padding:22px}
.empty{padding:36px;border:1px solid var(--line);background:#fffdf7;color:var(--muted)}
details.rule{margin:0 0 16px;border:1px solid var(--line);background:var(--panel)}
details.rule[open]{box-shadow:0 12px 26px rgba(35,44,38,.08)}
summary{display:grid;grid-template-columns:120px 1fr auto;gap:16px;align-items:center;padding:18px 22px;cursor:pointer;list-style:none;border-left:7px solid var(--rail)}
summary::-webkit-details-marker{display:none}
.rule-id{font-family:var(--mono);font-size:18px;font-weight:700}
.rule-note,.count{color:var(--muted);font-size:13px}
.count{font-family:var(--mono)}
.finding{display:grid;grid-template-columns:108px minmax(0,1fr) minmax(220px,.42fr);border-top:1px solid var(--line)}
.finding-side{padding:18px;border-right:1px solid var(--line);background:#faf7ef}
.index{display:block;margin-bottom:12px;color:var(--muted);font-family:var(--mono);font-size:12px}
.severity{display:inline-block;padding:5px 8px;border:1px solid currentColor;font-family:var(--mono);font-size:11px;text-transform:uppercase}
.severity-critical,.severity-high{color:var(--accent)}
.severity-medium{color:var(--copper)}
.severity-low{color:var(--green)}
.severity-info{color:var(--blue)}
.finding-main{padding:18px 20px;min-width:0}
.target-row{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.target{display:inline-flex;min-height:28px;align-items:center;padding:4px 8px;border:1px solid var(--line);background:#fffaf0;font-family:var(--mono);font-size:12px}
.message{margin:0 0 14px;font-size:15px}
.action{margin:0;padding-left:14px;border-left:3px solid var(--copper);color:#403a32;font-size:14px}
.evidence{padding:18px;border-left:1px solid var(--line);background:#fcfbf6}
.evidence h3{margin:0 0 10px;color:var(--muted);font-family:var(--mono);font-size:11px;text-transform:uppercase}
.token{display:block;margin:0 0 8px;padding:8px;background:#eef3f1;color:#24352f;font-family:var(--mono);font-size:12px;overflow-wrap:anywhere}
.status{margin-top:12px;color:var(--muted);font-family:var(--mono);font-size:12px}
@media(max-width:820px){main{width:min(100% - 20px,1180px);padding:16px 0 32px}.hero,.summary,.finding{grid-template-columns:1fr}.title-block{padding:28px 24px}.meta{grid-template-columns:1fr 1fr;border-left:0}.panel,.evidence{border-left:0;border-right:0}summary{grid-template-columns:1fr}}
@media print{body{background:#fff}main{width:100%;padding:0}.sheet,details.rule[open]{box-shadow:none}details.rule{break-inside:avoid}}
"""


def render(findings: list[Finding], project_meta: dict[str, Any]) -> str:
    """Return a standalone HTML document for a schematic review report."""

    project_name = str(project_meta.get("project_name", "(unknown)"))
    project_dir = str(project_meta.get("project_dir", "(unknown)"))
    components_reviewed = int(project_meta.get("components_reviewed", 0))
    rules_run = list(project_meta.get("rules_run", []))
    generated_at = str(project_meta.get("generated_at", ""))
    sanitize_note = _sanitize_note(project_meta)
    severity_counts = Counter(f.severity for f in findings)
    rule_counts = Counter(f.rule_id for f in findings)
    by_rule = _group_by_rule(findings)
    rules_text = ", ".join(rules_run) if rules_run else "(none)"
    sanitizer = f'<p class="sanitizer">{escape(sanitize_note)}</p>' if sanitize_note else ""

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Hardwise 原理图检视报告 - {escape(project_name)}</title>
  <style>{_STYLE}</style>
</head>
<body>
  <main>
    <section class="sheet" aria-label="Hardwise 原理图检视报告">
      <header class="hero">
        <div class="title-block">
          <p class="eyebrow">Hardwise 原理图检视报告</p>
          <h1>{escape(project_name)}</h1>
          <p class="project-path">{escape(project_dir)}</p>
        </div>
        <div class="meta" aria-label="检视摘要">
          <div class="metric"><span>检视意见</span><strong>{len(findings)}</strong></div>
          <div class="metric"><span>已扫描器件</span><strong>{components_reviewed}</strong></div>
          <div class="metric"><span>检查规则</span><strong>{len(rules_run)}</strong><code>{escape(rules_text)}</code></div>
          <div class="metric"><span>生成日期</span><strong>{escape(_date_label(generated_at))}</strong><code>{escape(generated_at)}</code></div>
        </div>
      </header>
      <section class="summary" aria-label="统计">
        <div class="panel"><h2>风险等级</h2>{_severity_chips(severity_counts)}</div>
        <div class="panel"><h2>规则命中</h2>{_rule_chips(rule_counts, rules_run)}{sanitizer}</div>
      </section>
      <section class="findings" aria-label="检视意见">{_findings_markup(findings, by_rule)}</section>
    </section>
  </main>
</body>
</html>
"""


def _group_by_rule(findings: list[Finding]) -> dict[str, list[Finding]]:
    by_rule: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        by_rule[finding.rule_id].append(finding)
    return by_rule


def _severity_chips(severity_counts: Counter[str]) -> str:
    chips = []
    for severity in _SEVERITY_ORDER:
        count = severity_counts.get(severity, 0)
        chips.append(
            '<span class="chip">'
            f'<span class="severity severity-{severity}">{_severity_label(severity)}</span>'
            f"<b>{count}</b></span>"
        )
    return f'<div class="chips">{"".join(chips)}</div>'


def _rule_chips(rule_counts: Counter[str], rules_run: list[str]) -> str:
    rule_ids = list(dict.fromkeys([*rules_run, *sorted(rule_counts)]))
    if not rule_ids:
        return '<div class="chips"><span class="chip"><b>0</b> 条规则</span></div>'
    chips = [
        f'<span class="chip"><span>{escape(rule_id)}</span><b>{rule_counts.get(rule_id, 0)}</b></span>'
        for rule_id in rule_ids
    ]
    return f'<div class="chips">{"".join(chips)}</div>'


def _findings_markup(findings: list[Finding], by_rule: dict[str, list[Finding]]) -> str:
    if not findings:
        return (
            '<div class="empty">'
            "0 条待确认意见。已扫描器件在当前规则集下未发现需要人工复核的问题。"
            "</div>"
        )

    sections: list[str] = []
    index = 1
    for rule_id in sorted(by_rule):
        rows = []
        for finding in by_rule[rule_id]:
            rows.append(_finding_markup(finding, index))
            index += 1
        open_attr = " open" if len(by_rule) == 1 else ""
        sections.append(
            f'<details class="rule"{open_attr}>'
            "<summary>"
            f'<span class="rule-id">{escape(rule_id)}</span>'
            '<span class="rule-note">位号已由原理图注册表校验</span>'
            f'<span class="count">{len(by_rule[rule_id])} 条意见</span>'
            "</summary>"
            f"{''.join(rows)}</details>"
        )
    return "".join(sections)


def _finding_markup(finding: Finding, index: int) -> str:
    refdes = escape(finding.refdes or "-")
    net = escape(finding.net or "-")
    action = escape(_friendly_action(finding))
    evidence = finding.evidence_tokens or ["未提供证据定位 token"]
    evidence_markup = "".join(f'<code class="token">{escape(token)}</code>' for token in evidence)
    message = escape(_friendly_message(finding))
    severity = escape(finding.severity)

    return (
        '<article class="finding">'
        f'<div class="finding-side"><span class="index">#{index:03d}</span>'
        f'<span class="severity severity-{severity}">'
        f"{_severity_label(finding.severity)}</span></div>"
        '<div class="finding-main"><div class="target-row">'
        f'<span class="target">位号：{refdes}</span>'
        f'<span class="target">网络：{net}</span></div>'
        f'<p class="message">{message}</p>'
        f'<p class="action">{action}</p></div>'
        '<aside class="evidence"><h3>证据定位</h3>'
        f'{evidence_markup}<div class="status">处理状态：{_status_label(finding.status)}</div></aside>'
        "</article>"
    )


def _date_label(value: str) -> str:
    return value[:10] if value else "-"


def _severity_label(severity: str) -> str:
    return escape(_SEVERITY_LABELS.get(severity, severity))


def _status_label(status: str) -> str:
    return escape(_STATUS_LABELS.get(status, status))


def _sanitize_note(project_meta: dict[str, Any]) -> str:
    wrapped = project_meta.get("unverified_refdes_wrapped")
    dropped = project_meta.get("findings_dropped_no_evidence")
    if wrapped is not None and dropped is not None:
        return f"位号守卫：{wrapped} 个未验证位号已标记，{dropped} 条缺少证据的意见已丢弃。"
    return str(project_meta.get("sanitize_note", ""))


def _friendly_message(finding: Finding) -> str:
    if finding.rule_id == "R001":
        return f"{finding.refdes} 的 Footprint 字段为空，可能是新器件或封装尚未分配，需要在评审时重点确认。"

    r002_missing = re.match(
        r"(?P<refdes>\S+) value field '(?P<value>[^']+)' does not declare rated voltage",
        finding.message,
    )
    if finding.rule_id == "R002" and r002_missing:
        refdes = r002_missing.group("refdes")
        value = r002_missing.group("value")
        return (
            f"{refdes} 的电容值为 {value}，但 value 字段没有标注耐压。"
            "没有耐压值就无法判断是否满足 80% 降额规则。"
        )

    r002_declared = re.match(
        r"(?P<refdes>\S+) rated voltage = (?P<voltage>\S+) V detected from value '(?P<value>[^']+)'",
        finding.message,
    )
    if finding.rule_id == "R002" and r002_declared:
        refdes = r002_declared.group("refdes")
        voltage = r002_declared.group("voltage")
        value = r002_declared.group("value")
        return (
            f"{refdes} 的 value 字段为 {value}，已识别到耐压 {voltage} V。"
            "仍需人工对照该电容所在网络的实际工作电压，确认 80% 降额是否满足。"
        )

    r003 = re.match(
        r"(?P<refdes>\S+) pin (?P<pin_number>\S+) \((?P<pin_name>.+)\) marked NC "
        r"\(type: (?P<pin_type>.+)\)\. Confirm NC handling with datasheet\.",
        finding.message,
    )
    if finding.rule_id == "R003" and r003:
        return (
            f"{r003.group('refdes')} 的 {r003.group('pin_number')} 脚"
            f"（{r003.group('pin_name')}，电气类型：{_pin_type_label(r003.group('pin_type'))}）"
            "被标为 NC。需要按 datasheet 确认该脚允许悬空，还是必须接地、上拉或接到固定电平。"
        )

    return finding.message


def _friendly_action(finding: Finding) -> str:
    if finding.rule_id == "R001":
        return "按新器件处理：复核 symbol、封装尺寸、pinout 与 datasheet 是否一致，再进入签核。"
    if finding.rule_id == "R002" and "does not declare rated voltage" in finding.message:
        return "建议在 value 字段补齐耐压，例如 100uF/25V；补齐后再按实际工作电压做降额检查。"
    if finding.rule_id == "R002" and "rated voltage =" in finding.message:
        match = re.search(r"does not exceed (?P<limit>\S+\s*V)", finding.suggested_action)
        limit = match.group("limit") if match else "耐压的 80%"
        return f"确认该电容所在网络的工作电压不超过 {limit}。"
    if finding.rule_id == "R003":
        return "打开对应 datasheet 的 pin description / NC 说明，确认该 NC 脚的推荐处理方式。"
    return finding.suggested_action or "未提供建议动作。"


def _pin_type_label(pin_type: str) -> str:
    return _PIN_TYPE_LABELS.get(pin_type, pin_type)
