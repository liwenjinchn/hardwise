"""Self-contained, read-only HTML evidence report for a revision comparison."""

from __future__ import annotations

import base64
from html import escape

from hardwise.revision.models import (
    ComparisonResult,
    Observation,
    RevisionView,
    SourceEvidence,
)

_STATUS = {
    "differences": "观察到源数据差异",
    "no_observed_difference": "未观察到源数据差异",
    "needs_review": "存在未知或冲突，需复查",
}
_KIND = {
    "component_added": "器件新增",
    "component_removed": "器件移除",
    "attribute_changed": "属性变化",
    "connection_changed": "连接变化",
    "net_renamed": "网络改名",
}
_STATE = {"known": "已声明", "missing": "缺失 / 未声明", "ambiguous": "冲突 / 不唯一"}
_SIDE = {"before": "改版前", "after": "改版后", "both": "前后两版"}


def _text(value: object) -> str:
    return escape(str(value), quote=True)


def _evidence(items: tuple[SourceEvidence, ...]) -> str:
    if not items:
        return '<p class="muted">未提供源定位</p>'
    return (
        '<ul class="evidence">'
        + "".join(
            f"<li><b>{_text(item.file)}</b> · {_text(item.locator)}"
            f"<br><span>SHA-256</span> <code>{_text(item.sha256)}</code></li>"
            for item in items
        )
        + "</ul>"
    )


def _observation(value: Observation | None) -> str:
    if value is None:
        return '<p class="muted">无对应记录；不推断未声明引脚状态</p>'
    values = "<br>".join(_text(item) for item in value.values) or "（无声明值）"
    return (
        f'<p class="state">{_text(_STATE[value.state])}</p>'
        f'<p class="values">{values}</p>{_evidence(value.evidence)}'
    )


def _sources(view: RevisionView, side: str) -> str:
    rows = "".join(
        f"<tr><td>{_text(item.role)}</td><td>{_text(item.file)}</td>"
        f"<td>{item.size_bytes}</td><td><code>{_text(item.sha256)}</code></td></tr>"
        for item in view.sources
    )
    return (
        f"<section><h3>{_text(side)} · {_text(view.label)}</h3>"
        f"<p>{view.component_count} 个器件 · {view.net_count} 个网络 · "
        f"{view.bom_row_count} 行 BOM</p>"
        '<div class="scroll"><table><thead><tr><th>来源角色</th><th>文件名</th>'
        "<th>字节数</th><th>SHA-256（完整）</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div></section>"
    )


def _networks(view: RevisionView, side: str) -> str:
    networks = []
    for network in view.networks:
        endpoints = "".join(
            f"<tr><td>{_text(endpoint.refdes)}</td><td>{_text(endpoint.pin)}</td></tr>"
            for endpoint in network.endpoints
        )
        state = "存在冲突 / 不唯一" if network.ambiguous else "源文件声明"
        networks.append(
            f'<details class="network"><summary>{_text(network.name)} · '
            f"{len(network.endpoints)} 个端点 · {state}</summary>"
            "<table><thead><tr><th>位号</th><th>引脚</th></tr></thead>"
            f"<tbody>{endpoints}</tbody></table>{_evidence(network.evidence)}</details>"
        )
    content = "".join(networks) or '<p class="muted">无已声明网络</p>'
    return f"<section><h3>{_text(side)} · {_text(view.label)}</h3>{content}</section>"


def render_comparison_html(result: ComparisonResult) -> str:
    """Render full source evidence without external assets, APIs or executable data."""
    summary = result.summary
    metrics = (
        ("器件新增", summary.added),
        ("器件移除", summary.removed),
        ("属性变化", summary.attribute_changes),
        ("连接变化", summary.connection_changes),
        ("网络改名", summary.net_renames),
        ("变化器件", summary.changed_components),
        ("待澄清项", summary.unresolved),
        ("未观察到变化的器件", summary.unchanged_components),
    )
    cards = "".join(
        f'<div class="metric"><strong>{count}</strong><span>{label}</span></div>'
        for label, count in metrics
    )
    changes = []
    for change in result.changes:
        related = "、".join(_text(refdes) for refdes in change.related_refdes[:50]) or "无列出位号"
        changes.append(
            '<article class="change">'
            f"<h3>{_text(_KIND[change.kind])} · {_text(change.refdes)}"
            f"{' · 引脚 ' + _text(change.pin) if change.pin is not None else ''}</h3>"
            f'<p class="muted">{_text(change.id)} · 字段 {_text(change.field)}</p>'
            f"<p>{_text(change.explanation)}</p>"
            '<div class="versions"><section><h4>改版前</h4>'
            f"{_observation(change.before)}</section><section><h4>改版后</h4>"
            f"{_observation(change.after)}</section></div>"
            f'<p class="related">直接同网器件：{related}。共 {change.related_count} 个；'
            "此处最多显示 50 个，完整端点见下方网络清单。仅为复查线索，不代表电气影响。</p>"
            "</article>"
        )
    change_html = "".join(changes) or (
        '<p class="muted">未列出确定差异；请结合未知项和比较边界解读，这不是电气正确性结论。</p>'
    )
    issues = (
        "".join(
            '<article class="issue">'
            f"<h3>{_text(_SIDE[issue.side])} · {_text(issue.code)}"
            f"{' · ' + _text(issue.refdes) if issue.refdes is not None else ''}</h3>"
            f"<p>{_text(issue.explanation)}</p>{_evidence(issue.evidence)}</article>"
            for issue in result.issues
        )
        or '<p class="muted">未列出未知项；比较范围之外的内容仍未评价。</p>'
    )
    # Preserve the boundary meaning without using a positive whole-board verdict label.
    scope = "".join(
        f"<li>{_text(item.replace('整板安全', '整板电气表现'))}</li>" for item in result.scope
    )
    # Base64 is inert in an attribute, including when JSON contains </script> or quotes.
    payload = base64.b64encode(result.model_dump_json(indent=2).encode("utf-8")).decode("ascii")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Hardwise · 改版对比报告</title>
<style>
:root{{color-scheme:light;font-family:system-ui,-apple-system,sans-serif;color:#1f2937;background:#f4f5f7}}
*{{box-sizing:border-box}}body{{margin:0}}main{{max-width:1200px;margin:auto;padding:40px 24px}}
header{{border-top:5px solid #245b58;padding:24px 0}}h1{{margin:8px 0;font-size:32px}}
h2{{margin:36px 0 16px}}h3{{margin-top:0;font-size:17px}}h4{{margin:0 0 8px}}
p,li{{line-height:1.65;overflow-wrap:anywhere}}.muted,.evidence{{color:#5b6575;font-size:13px}}
.status{{font-size:20px;color:#245b58}}.download{{display:inline-block;padding:10px 16px;
background:#245b58;color:white;border-radius:6px;text-decoration:none}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}
.metric,.change,.issue,.sources,.networks,.boundary{{background:white;border:1px solid #dce1e5;
border-radius:8px;padding:20px;margin-bottom:12px}}.metric strong{{display:block;font-size:27px}}
.metric span{{font-size:13px}}.versions{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
.versions>section{{min-width:0}}.values{{white-space:pre-wrap}}.state{{font-weight:600}}
.related{{font-size:13px;border-top:1px solid #e5e7eb;padding-top:12px}}
code{{font-size:12px;overflow-wrap:anywhere;white-space:normal}}.evidence{{padding-left:20px}}
.evidence li{{margin-bottom:8px}}table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{text-align:left;vertical-align:top;padding:9px;border-bottom:1px solid #e5e7eb;
overflow-wrap:anywhere}}th{{background:#f4f5f7}}.scroll{{overflow-x:auto}}
summary{{cursor:pointer;overflow-wrap:anywhere;padding:12px 0}}.network{{border-bottom:1px solid #e5e7eb}}
.boundary{{border-left:4px solid #b17a25}}footer{{margin-top:28px;color:#5b6575;font-size:12px}}
@media(max-width:700px){{main{{padding:24px 16px}}.versions{{grid-template-columns:1fr}}
.metrics{{grid-template-columns:repeat(2,1fr)}}}}
@media print{{:root{{background:white}}main{{padding:0}}.download{{display:none}}
details::details-content{{display:block}}.change{{break-inside:avoid}}}}
</style>
</head>
<body><main>
<header><p>HARDWISE / REVISION COMPARISON</p><h1>改版前后，对照源文件</h1>
<p class="status">{_text(_STATUS[result.status])}</p>
<p>单文件只读离线报告 · 无 AI · 未评价电气正确性</p>
<p class="muted">比较 ID：{_text(result.comparison_id)}<br>
合同：{_text(result.schema_version)} · 输入：{_text(result.input_format)} ·
电气判定：{_text(result.electrical_verdict)}</p>
<a class="download" download="hardwise-comparison.json" href="data:application/json;base64,{payload}">下载完整比较 JSON</a>
</header>
<h2>变化摘要</h2><div class="metrics">{cards}</div>
<h2>未知、冲突与比较边界</h2><div class="boundary"><ul>{scope}</ul></div>{issues}
<h2>源文件与完整哈希</h2><div class="sources">
{_sources(result.before, "改版前")}{_sources(result.after, "改版后")}</div>
<h2>逐项前后对照</h2>{change_html}
<h2>完整网络端点</h2><p>每版网络在此集中列出一次，不在每条变化中重复展开。</p>
<div class="networks">{_networks(result.before, "改版前")}{_networks(result.after, "改版后")}</div>
<footer>仅记录输入声明的差异；未声明不等于开路，未观察到差异不等于设计已经验证。</footer>
</main></body></html>"""
