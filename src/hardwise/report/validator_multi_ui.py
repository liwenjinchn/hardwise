"""Render a product-like static validator UI for multiple component validations."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
from urllib.parse import quote

from hardwise.bom.types import BomMatchReport, sort_refdes_key
from hardwise.ir.types import Component, Design
from hardwise.report.component_validation_markdown import render as render_validation_markdown
from hardwise.report.validator_multi_ui_assets import MULTI_UI_SCRIPT, MULTI_UI_STYLE
from hardwise.report.validator_multi_ui_sections import (
    basic_info,
    compliance_checks,
    connectivity_table,
    model_check,
    pin_summary,
    scope_panel,
    summary,
    topology_panel,
)
from hardwise.report.validator_ui import _match_summary, _status_class
from hardwise.validation.types import ComponentValidation, ValidationReport


@dataclass(frozen=True)
class ValidatorUiResult:
    """One validated component rendered in the batch UI."""

    validation: ValidationReport
    profile_path: Path


def render(
    design: Design,
    results: list[ValidatorUiResult],
    *,
    project_name: str,
    netlist_source: Path,
    bom_report: BomMatchReport | None = None,
    generated_at: str = "",
) -> str:
    """Return a standalone static HTML validator UI for multiple reports."""

    if not results:
        raise ValueError("at least one validation result is required")

    ordered = _issue_first(results)
    active_refdes = ordered[0].validation.refdes
    components = sorted(design.components.values(), key=lambda c: sort_refdes_key(c.refdes))
    validated = {item.validation.refdes: item for item in ordered}
    counts = _status_counts(ordered)

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
          <div class="metric"><span>已验证</span><strong>{len(ordered)}</strong></div>
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
            <input class="filter" data-filter placeholder="按位号、描述、MPN 过滤..." type="search">
          </div>
          <div class="table-wrap">{_component_table(components, validated, active_refdes, bom_report)}</div>
        </aside>
        <aside class="verify" aria-label="验证">
          <div class="verify-head">
            <div class="section-title">
              <h2>验证</h2>
              <span class="pill">{_match_summary(bom_report)}</span>
            </div>
            <p class="source">验证完成 · PASS/WARN/ERROR={counts["PASS"]}/{counts["WARN"]}/{counts["ERROR"]}</p>
          </div>
          <div class="verified-list">{_validated_cards(ordered, active_refdes)}</div>
        </aside>
        <section class="detail" aria-label="验证报告">
          {_detail_panels(design, ordered, active_refdes, generated_at)}
        </section>
      </section>
    </section>
  </main>
  <script>{MULTI_UI_SCRIPT}</script>
</body>
</html>
"""


def _issue_first(results: list[ValidatorUiResult]) -> list[ValidatorUiResult]:
    rank = {"ERROR": 0, "WARN": 1, "PASS": 2}
    return sorted(results, key=lambda item: (rank[item.validation.status], item.validation.refdes))


def _status_counts(results: list[ValidatorUiResult]) -> dict[str, int]:
    return {
        "PASS": sum(item.validation.status == "PASS" for item in results),
        "WARN": sum(item.validation.status == "WARN" for item in results),
        "ERROR": sum(item.validation.status == "ERROR" for item in results),
    }


def _component_table(
    components: list[Component],
    validated: dict[str, ValidatorUiResult],
    active_refdes: str,
    bom_report: BomMatchReport | None,
) -> str:
    rows = [
        '<table id="component-index">',
        "<thead><tr><th>位号</th><th>描述 / MPN</th><th>引脚</th><th>状态</th></tr></thead><tbody>",
    ]
    matched = set(bom_report.matched_refdes) if bom_report else set()
    for component in components:
        item = validated.get(component.refdes)
        status = item.validation.status if item else ("Matched" if component.refdes in matched else "Profile needed")
        status_class = _status_class(status) if item else "pending"
        active = " active" if component.refdes == active_refdes else ""
        rows.append(
            f'<tr class="component-row{active}" data-row-ref="{escape(component.refdes)}">'
            f'<td class="ref">{escape(component.refdes)}</td>'
            f"<td>{escape(component.value or '-')}<span class=\"sub\">{escape(component.part_number or '-')}</span></td>"
            f"<td>{len(component.pins)}</td>"
            f'<td><span class="status {status_class}">{escape(status)}</span></td>'
            "</tr>"
        )
    rows.append("</tbody></table>")
    return "".join(rows)


def _validated_cards(results: list[ValidatorUiResult], active_refdes: str) -> str:
    cards = []
    for item in results:
        validation = item.validation
        active = " active" if validation.refdes == active_refdes else ""
        cards.append(
            f'<button class="device-card{active}" data-select-ref="{escape(validation.refdes)}" type="button">'
            '<div class="device-line">'
            f'<span class="device-title">{escape(validation.refdes)}</span>'
            f'<span class="status {_status_class(validation.status)}">{escape(validation.status)}</span>'
            "</div>"
            f'<p class="device-meta">{escape(validation.component_value)} · {escape(validation.profile_part_number)}</p>'
            f"{_issue_list(validation.component_checks)}"
            "</button>"
        )
    return "".join(cards)


def _issue_list(checks: list[ComponentValidation]) -> str:
    issues = [check for check in checks if check.status != "PASS"]
    if not issues:
        return '<p class="device-meta">未发现确定性外围/拓扑问题。</p>'
    rendered = ['<div class="issue-list">']
    for check in issues[:3]:
        rendered.append(
            '<div class="issue">'
            f"<strong>{escape(check.refdes or check.check)} · {escape(check.status)}</strong>"
            f"<span>{escape(check.summary)}</span>"
            "</div>"
        )
    rendered.append("</div>")
    return "".join(rendered)


def _detail_panels(
    design: Design,
    results: list[ValidatorUiResult],
    active_refdes: str,
    generated_at: str,
) -> str:
    return "".join(
        _detail_panel(design, item, active_refdes, generated_at) for item in results
    )


def _detail_panel(
    design: Design,
    item: ValidatorUiResult,
    active_refdes: str,
    generated_at: str,
) -> str:
    validation = item.validation
    component = design.components[validation.refdes]
    counts = validation.counts_by_status
    component_counts = validation.component_counts_by_status
    markdown = render_validation_markdown(validation, profile_path=item.profile_path)
    download_href = "data:text/markdown;charset=utf-8," + quote(markdown)
    active = " active" if validation.refdes == active_refdes else ""
    return f"""
    <article class="panel{active}" data-panel="{escape(validation.refdes)}">
      <div class="detail-head">
        <div class="detail-title">
          <h2>{escape(validation.refdes)} <span class="{_status_class(validation.status)} status">综合判定 {escape(validation.status)}</span></h2>
          <p>{escape(component.value or "-")} / MPN {escape(component.part_number or "-")} / profile {escape(validation.profile_part_number)}</p>
        </div>
        <div class="actions">
          <a class="button" download="{escape(validation.refdes)}-component-validation.md" href="{download_href}">下载报告</a>
          <a class="button secondary" href="#component-index">器件</a>
        </div>
      </div>
      <div class="kpis">
        <div class="kpi"><span>PASS pins</span><strong>{counts["PASS"]}</strong></div>
        <div class="kpi"><span>WARN pins</span><strong>{counts["WARN"]}</strong></div>
        <div class="kpi"><span>ERROR pins</span><strong>{counts["ERROR"]}</strong></div>
        <div class="kpi"><span>PASS checks</span><strong>{component_counts["PASS"]}</strong></div>
        <div class="kpi"><span>WARN checks</span><strong>{component_counts["WARN"]}</strong></div>
        <div class="kpi"><span>ERROR checks</span><strong>{component_counts["ERROR"]}</strong></div>
      </div>
      {pin_summary(validation)}
      {basic_info(component, validation)}
      {model_check(validation)}
      {connectivity_table(validation)}
      {compliance_checks(validation)}
      {topology_panel(component, design)}
      {summary(validation)}
      {scope_panel(generated_at, item.profile_path)}
    </article>
    """
