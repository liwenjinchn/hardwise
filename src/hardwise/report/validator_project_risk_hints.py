"""Append-only renderer for externally supplied, refdes-anchored hints."""

from __future__ import annotations

from html import escape

from hardwise.adapters.base import BoardRegistry, ComponentRecord
from hardwise.guards.refdes import sanitize_text
from hardwise.ir.types import Design
from hardwise.report.component_validation_details import evidence_chips_html
from hardwise.validation.risk_hints import RiskHint, RiskHintReport


def render_project_risk_hints(report: RiskHintReport | None, design: Design) -> str:
    """Render caller-provided accepted hints without changing local results."""

    if report is None:
        body = (
            '<p class="scope">'
            "未提供外部提示报告；本地 PASS/WARN/ERROR 结论不受影响。"
            "</p>"
        )
        return _section(body)

    registry = _registry_from_design(design)
    rows = [
        _hint_card(_sanitize_hint(hint, registry))
        for hint in sorted(report.accepted, key=lambda item: item.input_index)
    ]
    if not rows:
        rows.append('<p class="muted">-</p>')

    rejected_summary = ""
    if report.rejected_count:
        rejected_summary = (
            '<p class="scope">'
            f"已跳过 {report.rejected_count} 条无法安全锚定的外部提示。"
            "</p>"
        )

    body = (
        '<p class="scope">'
        "本节仅展示调用方提供并已通过位号锚定的外部提示；不会改变本地 PASS/WARN/ERROR 结论。"
        "</p>"
        '<div class="gap-list">'
        f"{''.join(rows)}"
        "</div>"
        f"{rejected_summary}"
    )
    return _section(body)


def _section(body: str) -> str:
    return (
        '<section class="section table-section" data-section="external-hints">'
        '<div class="section-head"><h3>外部提示附录</h3><span class="pill">只读</span></div>'
        f"{body}"
        "</section>"
    )


def _hint_card(hint: RiskHint) -> str:
    return (
        '<div class="gap-card">'
        f"<strong>{escape(hint.refdes)} · {escape(hint.title)}</strong>"
        f"<p>{escape(hint.body)}</p>"
        f'<p class="evidence">{_source_html(hint)}</p>'
        "</div>"
    )


def _source_html(hint: RiskHint) -> str:
    if not hint.source:
        return '<span class="muted">-</span>'
    return evidence_chips_html([hint.source], refdes=hint.refdes)


def _sanitize_hint(hint: RiskHint, registry: BoardRegistry) -> RiskHint:
    title, _title_wrapped = sanitize_text(hint.title, registry)
    body, _body_wrapped = sanitize_text(hint.body, registry)
    source, _source_wrapped = sanitize_text(hint.source or "", registry)
    return hint.model_copy(
        update={
            "title": title,
            "body": body,
            "source": source or None,
        }
    )


def _registry_from_design(design: Design) -> BoardRegistry:
    components = [
        ComponentRecord(
            refdes=component.refdes,
            value=" ".join(
                item
                for item in (
                    component.value,
                    component.part_number,
                    component.manufacturer,
                )
                if item
            ),
            footprint=component.package or component.properties.get("Footprint") or "",
            datasheet=component.datasheet_path or "",
            source_file=design.project_path,
            source_kind=design.source_eda,
        )
        for component in design.components.values()
    ]
    return BoardRegistry(project_dir=design.project_path, components=components)
