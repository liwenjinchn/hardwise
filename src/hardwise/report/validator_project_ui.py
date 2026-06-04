"""Render project-level validator workbenches, including zero-profile gaps."""

from __future__ import annotations

from collections import Counter
from html import escape
from pathlib import Path

from hardwise.bom.types import BomMatchReport, sort_refdes_key
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.report.component_validation_details import trust_label_html
from hardwise.report.validator_multi_ui import (
    ValidatorUiResult,
    _detail_panels,
    _issue_first,
    _status_counts,
    _validated_cards,
)
from hardwise.report.ui_terms import identity_kind_label, reason_label, status_label
from hardwise.report.validator_multi_ui_assets import MULTI_UI_SCRIPT, MULTI_UI_STYLE
from hardwise.report.validator_project_group_ui import (
    component_group_table,
    component_group_table_rows,
)
from hardwise.report.validator_ui import _status_class
from hardwise.validation.project_index import (
    ProjectValidationGapGroup,
    ProjectValidationIndex,
    ProjectValidationRow,
    profile_gap_groups,
)

GAP_ROW_LIMIT = 50


def render_project_workbench(
    design: Design,
    index: ProjectValidationIndex,
    *,
    project_name: str,
    netlist_source: Path,
    bom_report: BomMatchReport | None = None,
    generated_at: str = "",
    copilot_html: str = "",
) -> str:
    """Return a static project workbench for validated and no-profile rows."""

    results = [
        ValidatorUiResult(
            validation=row.validation,
            profile_path=Path(row.profile_path or row.validation.profile_part_number),
            profile=DatasheetProfile.load(Path(row.profile_path)) if row.profile_path else None,
        )
        for row in index.validated_rows
        if row.validation is not None
    ]
    ordered = _issue_first(results)
    components = sorted(design.components.values(), key=lambda c: sort_refdes_key(c.refdes))
    validated = {item.validation.refdes: item for item in ordered}
    counts = _status_counts(ordered)
    active_refdes = ordered[0].validation.refdes if ordered else ""
    rail_count = len(index.component_groups) if index.component_groups else len(components)

    copilot_block = f"{copilot_html}" if copilot_html else ""

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Hardwise 原理图检验工具 - {escape(project_name)}</title>
  <style>{MULTI_UI_STYLE}</style>
</head>
<body>
  <main>
    <section class="app" aria-label="Hardwise 本地原理图检验工具">
      <header class="topbar">
        <div class="brand">
          <p class="eyebrow">Hardwise / 原理图检验工具</p>
          <h1>{escape(project_name)}</h1>
          <p class="source">{escape(str(netlist_source))}</p>
        </div>
        <div class="summary" aria-label="验证摘要">
          <div class="metric"><span>器件</span><strong>{len(components)}</strong></div>
          <div class="metric"><span>BOM 匹配</span><strong>{index.bom_matched}</strong></div>
          <div class="metric"><span>已验证</span><strong>{len(ordered)}</strong></div>
          <div class="metric"><span>待器件档案</span><strong>{len(index.manual_rows)}</strong></div>
          <div class="metric pass"><span>PASS</span><strong>{counts["PASS"]}</strong></div>
          <div class="metric warn"><span>WARN</span><strong>{counts["WARN"]}</strong></div>
          <div class="metric error"><span>ERROR</span><strong>{counts["ERROR"]}</strong></div>
        </div>
      </header>
      <section class="workspace">
        <div class="left-stack" aria-label="器件与验证摘要">
          <aside class="rail" aria-label="器件">
            <div class="rail-head">
              <div class="section-title">
                <h2>器件</h2>
                <span class="count">{rail_count}</span>
              </div>
              <input class="filter" data-filter placeholder="按位号过滤..." type="search">
            </div>
            <div class="table-wrap">{_rail_table(components, validated, active_refdes, index, bom_report)}</div>
          </aside>
          <aside class="verify" aria-label="验证">
            <div class="verify-head">
              <div class="section-title">
                <h2>验证</h2>
                <span class="pill">{_verify_pill(ordered)}</span>
              </div>
              <p class="source">验证完成 · PASS/WARN/ERROR={counts["PASS"]}/{counts["WARN"]}/{counts["ERROR"]}</p>
            </div>
            <div class="verified-list">{_verify_list(ordered, active_refdes, index)}</div>
          </aside>
        </div>
        <section class="detail" aria-label="验证报告">
          {_detail_area(design, ordered, active_refdes, generated_at, index)}
        </section>
      </section>
    </section>
  </main>{copilot_block}
  <script>{MULTI_UI_SCRIPT}</script>
</body>
</html>
"""


def _rail_table(
    components: list[Component],
    validated: dict[str, ValidatorUiResult],
    active_refdes: str,
    index: ProjectValidationIndex,
    bom_report: BomMatchReport | None,
) -> str:
    if index.component_groups:
        return component_group_table(index.component_groups, validated_refdes=set(validated))
    return _component_table(components, validated, active_refdes, index, bom_report)


def _component_table(
    components: list[Component],
    validated: dict[str, ValidatorUiResult],
    active_refdes: str,
    index: ProjectValidationIndex,
    bom_report: BomMatchReport | None,
) -> str:
    rows_by_refdes = {row.refdes: row for row in index.rows}
    bom_matched = set(bom_report.matched_refdes) if bom_report else set()
    rows = [
        '<table id="component-index">',
        "<thead><tr><th>位号</th><th>描述</th><th>器件</th><th>器件档案</th></tr></thead><tbody>",
    ]
    for component in components:
        row = rows_by_refdes.get(component.refdes)
        item = validated.get(component.refdes)
        status = _row_status(component, row, item, bom_matched)
        status_class = _coverage_status_class(status)
        active = " active" if component.refdes == active_refdes else ""
        rows.append(
            f'<tr class="component-row{active}" data-row-ref="{escape(component.refdes)}">'
            f'<td class="ref">{escape(component.refdes)}</td>'
            f"<td>{escape(component.value or '-')}</td>"
            f"<td>{escape(component.part_number or component.value or '-')}"
            f'<span class="sub">{len(component.pins)} pins · {escape(status)}</span>'
            f"{_row_trust(item)}</td>"
            f'<td><span class="status {status_class}">{escape(status_label(status))}</span>'
            f"{_row_reason(row)}</td>"
            "</tr>"
        )
    rows.append("</tbody></table>")
    return "".join(rows)


def _row_status(
    component: Component,
    row: ProjectValidationRow | None,
    item: ValidatorUiResult | None,
    bom_matched: set[str],
) -> str:
    if item is not None:
        return item.validation.status
    if row is not None:
        return row.match_status
    if component.refdes in bom_matched:
        return "manual_needed"
    return "no_result"


def _row_reason(row: ProjectValidationRow | None) -> str:
    if row is None or not row.reason:
        return ""
    return f'<span class="sub">{escape(row.reason)}</span>'


def _row_trust(item: ValidatorUiResult | None) -> str:
    return trust_label_html("l1") if item is not None else trust_label_html("l3")


def _coverage_status_class(status: str) -> str:
    if status in {"ambiguous", "manual_needed"}:
        return "warn"
    return _status_class(status)


def _verify_pill(results: list[ValidatorUiResult]) -> str:
    return "验证完成" if results else "档案缺口"


def _verify_list(
    results: list[ValidatorUiResult],
    active_refdes: str,
    index: ProjectValidationIndex,
) -> str:
    cards = [_coverage_summary(index)]
    if results:
        cards.append(_validated_cards(results, active_refdes))
    else:
        cards.append(_gap_group_cards(profile_gap_groups(index)))
    return "".join(cards)


def _coverage_summary(index: ProjectValidationIndex) -> str:
    counts = Counter(row.match_status for row in index.rows)
    return (
        '<div class="coverage-grid">'
        f"{_coverage_card('matched', counts['matched'])}"
        f"{_coverage_card('generic_passive', counts['generic_passive'])}"
        f"{_coverage_card('no_result', counts['no_result'])}"
        f"{_coverage_card('ambiguous', counts['ambiguous'])}"
        f"{_coverage_card('manual_needed', counts['manual_needed'])}"
        "</div>"
    )


def _coverage_card(label: str, count: int) -> str:
    tier = "l1" if label in {"matched", "generic_passive"} else "l3"
    return (
        f'<div class="gap-card"><strong>{escape(status_label(label))}</strong>{trust_label_html(tier)}'
        f"<p>{count} 个位号</p></div>"
    )


def _gap_group_cards(groups: list[ProjectValidationGapGroup]) -> str:
    rendered = ['<div class="gap-list">']
    for group in groups[:GAP_ROW_LIMIT]:
        rendered.append(
            '<div class="gap-card">'
            f"<strong>{group.refdes_count} · {escape(group.identity)}</strong>"
            f'{trust_label_html("l3")}'
            f"<p>{escape(status_label(group.match_status))} / {escape(identity_kind_label(group.identity_kind))}</p>"
            f"<p>{escape(', '.join(group.refdes_sample))}</p>"
            f"<p>{escape(reason_label(group.reason))}</p>"
            "</div>"
        )
    if len(groups) > GAP_ROW_LIMIT:
        rendered.append(
            '<div class="gap-card">'
            f"<strong>还有 {len(groups) - GAP_ROW_LIMIT} 个器件组</strong>"
            "<p>完整覆盖清单可在 Markdown/JSON 索引中查看。</p>"
            "</div>"
        )
    rendered.append("</div>")
    return "".join(rendered)


def _detail_area(
    design: Design,
    results: list[ValidatorUiResult],
    active_refdes: str,
    generated_at: str,
    index: ProjectValidationIndex,
) -> str:
    if results:
        return _detail_panels(design, results, active_refdes, generated_at)
    return _coverage_detail(index, generated_at)


def _coverage_detail(index: ProjectValidationIndex, generated_at: str) -> str:
    return (
        "<article>"
        '<div class="detail-head"><div class="detail-title">'
        '<h2>器件档案覆盖缺口 <span class="pending status">已验证 0</span> '
        f"{trust_label_html('l3')}</h2>"
        "<p>没有器件进入确定性 PASS/WARN/ERROR 检验，因为 BOM 身份还没有匹配到本地结构化器件档案。</p>"
        "</div></div>"
        '<div class="kpis">'
        f'<div class="kpi"><span>器件</span><strong>{index.components_in_design}</strong></div>'
        f'<div class="kpi"><span>BOM 匹配</span><strong>{index.bom_matched}</strong></div>'
        f'<div class="kpi"><span>已验证</span><strong>{len(index.validated_rows)}</strong></div>'
        f'<div class="kpi"><span>待人工确认</span><strong>{len(index.manual_rows)}</strong></div>'
        '<div class="kpi"><span>PASS</span><strong>0</strong></div>'
        '<div class="kpi"><span>WARN</span><strong>0</strong></div>'
        '<div class="kpi"><span>ERROR</span><strong>0</strong></div>'
        "</div>"
        '<section class="section table-section"><div class="section-head"><h3>器件组覆盖</h3></div>'
        "<table><thead><tr><th>数量</th><th>位号样例</th><th>BOM 身份</th><th>身份类型</th><th>类别</th><th>器件档案</th><th>资料</th><th>可信度</th></tr></thead><tbody>"
        f"{component_group_table_rows(index.component_groups, limit=GAP_ROW_LIMIT)}"
        "</tbody></table></section>"
        '<section class="section table-section"><div class="section-head"><h3>器件档案缺口分组</h3></div>'
        "<table><thead><tr><th>数量</th><th>状态</th><th>可信度</th><th>BOM 身份</th><th>身份类型</th><th>位号样例</th><th>原因</th></tr></thead><tbody>"
        f"{_gap_group_table_rows(profile_gap_groups(index))}"
        "</tbody></table></section>"
        '<section class="section"><div class="section-head"><h3>范围边界</h3></div>'
        '<p class="scope">这是原理图侧的覆盖检查结果；不会把缺少器件档案的行转换成电气判断。</p>'
        '<ul class="boundary-list">'
        f"<li>生成时间：{escape(generated_at or '-')}</li>"
        f"<li>器件档案目录：<code>{escape(index.profiles_dir)}</code></li>"
        "<li>允许输入：原理图导出的 Allegro/Telesis/PST 网表拓扑、原理图 BOM 身份，以及公开结构化器件档案事实。</li>"
        "<li>不包含：.brd、boardview/板图、布局、走线、PCB 几何、在线供应商查询、PLM、生命周期、价格与库存。</li>"
        "</ul></section>"
        "</article>"
    )


def _gap_group_table_rows(groups: list[ProjectValidationGapGroup]) -> str:
    rendered = []
    for group in groups[:GAP_ROW_LIMIT]:
        rendered.append(
            "<tr>"
            f"<td>{group.refdes_count}</td>"
            f"<td>{escape(status_label(group.match_status))}</td>"
            f"<td>{trust_label_html('l3')}</td>"
            f"<td>{escape(group.identity)}</td>"
            f"<td>{escape(identity_kind_label(group.identity_kind))}</td>"
            f"<td>{escape(', '.join(group.refdes_sample))}</td>"
            f"<td>{escape(reason_label(group.reason))}</td>"
            "</tr>"
        )
    if not rendered:
        rendered.append(
            "<tr><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>"
        )
    return "".join(rendered)
