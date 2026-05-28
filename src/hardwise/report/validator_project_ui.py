"""Render project-level validator workbenches, including zero-profile gaps."""

from __future__ import annotations

from collections import Counter
from html import escape
from pathlib import Path

from hardwise.bom.types import BomMatchReport, sort_refdes_key
from hardwise.ir.types import Component, Design
from hardwise.report.validator_multi_ui import (
    ValidatorUiResult,
    _detail_panels,
    _issue_first,
    _status_counts,
    _validated_cards,
)
from hardwise.report.validator_multi_ui_assets import MULTI_UI_SCRIPT, MULTI_UI_STYLE
from hardwise.report.validator_ui import _status_class
from hardwise.validation.project_index import ProjectValidationIndex, ProjectValidationRow

GAP_ROW_LIMIT = 50


def render_project_workbench(
    design: Design,
    index: ProjectValidationIndex,
    *,
    project_name: str,
    netlist_source: Path,
    bom_report: BomMatchReport | None = None,
    generated_at: str = "",
) -> str:
    """Return a static project workbench for validated and no-profile rows."""

    results = [
        ValidatorUiResult(validation=row.validation, profile_path=Path(row.profile_path))
        for row in index.validated_rows
        if row.validation is not None and row.profile_path is not None
    ]
    ordered = _issue_first(results)
    components = sorted(design.components.values(), key=lambda c: sort_refdes_key(c.refdes))
    validated = {item.validation.refdes: item for item in ordered}
    counts = _status_counts(ordered)
    active_refdes = ordered[0].validation.refdes if ordered else ""

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Hardwise Validator UI - {escape(project_name)}</title>
  <style>{MULTI_UI_STYLE}</style>
</head>
<body>
  <main>
    <section class="app" aria-label="Hardwise local validator UI">
      <header class="topbar">
        <div class="brand">
          <p class="eyebrow">Hardwise / 设计验证器</p>
          <h1>{escape(project_name)}</h1>
          <p class="source">{escape(str(netlist_source))}</p>
        </div>
        <div class="summary" aria-label="验证摘要">
          <div class="metric"><span>器件</span><strong>{len(components)}</strong></div>
          <div class="metric"><span>BOM matched</span><strong>{index.bom_matched}</strong></div>
          <div class="metric"><span>已验证</span><strong>{len(ordered)}</strong></div>
          <div class="metric"><span>待 profile</span><strong>{len(index.manual_rows)}</strong></div>
          <div class="metric pass"><span>PASS</span><strong>{counts["PASS"]}</strong></div>
          <div class="metric warn"><span>WARN</span><strong>{counts["WARN"]}</strong></div>
          <div class="metric error"><span>ERROR</span><strong>{counts["ERROR"]}</strong></div>
        </div>
      </header>
      <section class="workspace">
        <aside class="rail" aria-label="器件">
          <div class="rail-head">
            <div class="section-title">
              <h2>器件</h2>
              <span class="count">{len(components)}</span>
            </div>
            <input class="filter" data-filter placeholder="按位号过滤..." type="search">
          </div>
          <div class="table-wrap">{_component_table(components, validated, active_refdes, index, bom_report)}</div>
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
        <section class="detail" aria-label="验证报告">
          {_detail_area(design, ordered, active_refdes, generated_at, index)}
        </section>
      </section>
    </section>
  </main>
  <script>{MULTI_UI_SCRIPT}</script>
</body>
</html>
"""


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
        "<thead><tr><th>位号</th><th>描述</th><th>器件</th><th>Profile</th></tr></thead><tbody>",
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
            f'<span class="sub">{len(component.pins)} pins · {escape(status)}</span></td>'
            f'<td><span class="status {status_class}">{escape(_row_label(status))}</span>'
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


def _row_label(status: str) -> str:
    return {
        "matched": "已匹配",
        "no_result": "待 profile",
        "manual_needed": "需确认",
        "ambiguous": "多候选",
    }.get(status, status)


def _coverage_status_class(status: str) -> str:
    if status in {"ambiguous", "manual_needed"}:
        return "warn"
    return _status_class(status)


def _verify_pill(results: list[ValidatorUiResult]) -> str:
    return "验证完成" if results else "Profile gap"


def _verify_list(
    results: list[ValidatorUiResult],
    active_refdes: str,
    index: ProjectValidationIndex,
) -> str:
    cards = [_coverage_summary(index)]
    if results:
        cards.append(_validated_cards(results, active_refdes))
    else:
        cards.append(_gap_cards(index.manual_rows))
    return "".join(cards)


def _coverage_summary(index: ProjectValidationIndex) -> str:
    counts = Counter(row.match_status for row in index.rows)
    return (
        '<div class="coverage-grid">'
        f"{_coverage_card('matched', counts['matched'])}"
        f"{_coverage_card('no_result', counts['no_result'])}"
        f"{_coverage_card('ambiguous', counts['ambiguous'])}"
        f"{_coverage_card('manual_needed', counts['manual_needed'])}"
        "</div>"
    )


def _coverage_card(label: str, count: int) -> str:
    return (
        f'<div class="gap-card"><strong>{escape(label)}</strong><p>{count} component rows</p></div>'
    )


def _gap_cards(rows: list[ProjectValidationRow]) -> str:
    rendered = ['<div class="gap-list">']
    for row in rows[:GAP_ROW_LIMIT]:
        rendered.append(
            '<div class="gap-card">'
            f"<strong>{escape(row.refdes)} · {escape(row.match_status)}</strong>"
            f"<p>{escape(row.part_number or row.bom_value or '-')}</p>"
            f"<p>{escape(row.reason)}</p>"
            "</div>"
        )
    if len(rows) > GAP_ROW_LIMIT:
        rendered.append(
            '<div class="gap-card">'
            f"<strong>+{len(rows) - GAP_ROW_LIMIT} more</strong>"
            "<p>Full coverage rows are available in the markdown/JSON index.</p>"
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
        '<h2>Profile coverage gap <span class="pending status">validated 0</span></h2>'
        "<p>No component received deterministic PASS/WARN/ERROR because no BOM identity matched a local structured profile.</p>"
        "</div></div>"
        '<div class="kpis">'
        f'<div class="kpi"><span>Components</span><strong>{index.components_in_design}</strong></div>'
        f'<div class="kpi"><span>BOM matched</span><strong>{index.bom_matched}</strong></div>'
        f'<div class="kpi"><span>Validated</span><strong>{len(index.validated_rows)}</strong></div>'
        f'<div class="kpi"><span>Manual</span><strong>{len(index.manual_rows)}</strong></div>'
        '<div class="kpi"><span>PASS</span><strong>0</strong></div>'
        '<div class="kpi"><span>WARN</span><strong>0</strong></div>'
        '<div class="kpi"><span>ERROR</span><strong>0</strong></div>'
        "</div>"
        '<section class="section table-section"><div class="section-head"><h3>Profile Gap Rows</h3></div>'
        "<table><thead><tr><th>Refdes</th><th>Status</th><th>BOM value</th><th>MPN</th><th>Reason</th></tr></thead><tbody>"
        f"{_gap_table_rows(index.manual_rows)}"
        "</tbody></table></section>"
        '<section class="section"><div class="section-head"><h3>Scope Boundary</h3></div>'
        '<p class="scope">This workbench is a schematic-side coverage artifact. It does not convert no-profile rows into electrical judgements.</p>'
        '<ul class="boundary-list">'
        f"<li>Generated at: {escape(generated_at or '-')}</li>"
        f"<li>Profiles dir: <code>{escape(index.profiles_dir)}</code></li>"
        "<li>Allowed inputs: schematic-exported Allegro/Telesis/PST topology, schematic BOM identity, and public structured profile facts.</li>"
        "<li>Out of scope: .brd, boardview, placement, routing, PCB geometry, live supplier lookup, PLM, lifecycle, pricing, and availability.</li>"
        "</ul></section>"
        "</article>"
    )


def _gap_table_rows(rows: list[ProjectValidationRow]) -> str:
    rendered = []
    for row in rows[:GAP_ROW_LIMIT]:
        rendered.append(
            "<tr>"
            f'<td class="ref">{escape(row.refdes)}</td>'
            f"<td>{escape(row.match_status)}</td>"
            f"<td>{escape(row.bom_value or '-')}</td>"
            f"<td>{escape(row.part_number or '-')}</td>"
            f"<td>{escape(row.reason)}</td>"
            "</tr>"
        )
    if not rendered:
        rendered.append("<tr><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>")
    return "".join(rendered)
