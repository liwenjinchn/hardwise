"""HTML fragments for grouped component coverage in project validator UI."""

from __future__ import annotations

from html import escape

from hardwise.report.component_validation_details import trust_label_html
from hardwise.report.ui_terms import (
    family_label,
    identity_kind_label,
    reason_label,
    status_label,
)
from hardwise.report.validator_ui import _status_class
from hardwise.validation.component_groups import ProjectComponentGroup


def component_group_table(groups: list[ProjectComponentGroup]) -> str:
    """Render grouped component rows for the left rail."""

    rows = [
        '<table id="component-index">',
        "<thead><tr><th>位号</th><th>BOM 身份</th><th>类别</th><th>资料</th></tr></thead><tbody>",
    ]
    for group in groups:
        rows.append(
            f'<tr class="component-row" data-row-ref="{escape(group.group_id)}">'
            f'<td class="ref">{escape(", ".join(group.refdes_sample))}'
            f'<span class="sub">{group.refdes_count} 个位号</span></td>'
            f"<td>{escape(group.identity or '-')}"
            f'<span class="sub">{escape(identity_kind_label(group.identity_kind))} · '
            f"{escape(status_label(group.profile_status))}</span>"
            f"{_group_trust(group)}</td>"
            f"<td>{escape(family_label(group.suggested_family))}</td>"
            f"<td>{document_status_cell(group)}</td>"
            "</tr>"
        )
    rows.append("</tbody></table>")
    return "".join(rows)


def component_group_table_rows(
    groups: list[ProjectComponentGroup],
    *,
    limit: int,
) -> str:
    """Render grouped component rows for the detail table."""

    rendered = []
    for group in groups[:limit]:
        rendered.append(
            "<tr>"
            f"<td>{group.refdes_count}</td>"
            f"<td>{escape(', '.join(group.refdes_sample))}</td>"
            f"<td>{escape(group.identity or '-')}</td>"
            f"<td>{escape(identity_kind_label(group.identity_kind))}</td>"
            f"<td>{escape(family_label(group.suggested_family))}</td>"
            f"<td>{escape(status_label(group.profile_status))}</td>"
            f"<td>{document_status_cell(group)}</td>"
            f"<td>{_group_trust(group)}</td>"
            "</tr>"
        )
    if len(groups) > limit:
        rendered.append(
            "<tr>"
            f"<td>+{len(groups) - limit}</td>"
            '<td colspan="7">更多器件组可在 Markdown/JSON 索引中查看。</td>'
            "</tr>"
        )
    if not rendered:
        rendered.append(
            "<tr><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>"
        )
    return "".join(rendered)


def document_status_cell(group: ProjectComponentGroup) -> str:
    """Render document status plus selected document link, when available."""

    status = escape(status_label(group.document_status))
    status_class = _coverage_status_class(group.document_status)
    status_chip = f'<span class="status {status_class}">{status}</span>'
    if group.document_title and group.document_url:
        return (
            f'{status_chip}<a class="sub" href="{escape(group.document_url)}">'
            f"{escape(group.document_title)}</a>"
        )
    if group.document_reason:
        return status_chip + f'<span class="sub">{escape(reason_label(group.document_reason))}</span>'
    return status_chip


def _group_trust(group: ProjectComponentGroup) -> str:
    return trust_label_html(
        "l1" if group.profile_status in {"matched", "generic_passive"} else "l3"
    )


def _coverage_status_class(status: str) -> str:
    if status in {"ambiguous", "manual_needed"}:
        return "warn"
    if status == "matched":
        return "pass"
    if status == "not_requested":
        return "pending"
    return _status_class(status)
