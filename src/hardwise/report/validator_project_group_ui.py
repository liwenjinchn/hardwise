"""HTML fragments for grouped component coverage in project validator UI."""

from __future__ import annotations

from html import escape

from hardwise.report.validator_ui import _status_class
from hardwise.validation.component_groups import ProjectComponentGroup


def component_group_table(groups: list[ProjectComponentGroup]) -> str:
    """Render grouped component rows for the left rail."""

    rows = [
        '<table id="component-index">',
        "<thead><tr><th>位号</th><th>Identity</th><th>Family</th><th>Docs</th></tr></thead><tbody>",
    ]
    for group in groups:
        rows.append(
            f'<tr class="component-row" data-row-ref="{escape(group.group_id)}">'
            f'<td class="ref">{escape(", ".join(group.refdes_sample))}'
            f'<span class="sub">{group.refdes_count} refs</span></td>'
            f"<td>{escape(group.identity or '-')}"
            f'<span class="sub">{escape(group.identity_kind)} · {escape(group.profile_status)}</span></td>'
            f"<td>{escape(group.suggested_family)}</td>"
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
            f"<td>{escape(group.identity_kind)}</td>"
            f"<td>{escape(group.suggested_family)}</td>"
            f"<td>{escape(group.profile_status)}</td>"
            f"<td>{document_status_cell(group)}</td>"
            "</tr>"
        )
    if len(groups) > limit:
        rendered.append(
            "<tr>"
            f"<td>+{len(groups) - limit}</td>"
            '<td colspan="6">More component groups are available in the markdown/JSON index.</td>'
            "</tr>"
        )
    if not rendered:
        rendered.append(
            "<tr><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>"
        )
    return "".join(rendered)


def document_status_cell(group: ProjectComponentGroup) -> str:
    """Render document status plus selected document link, when available."""

    status = escape(group.document_status)
    status_class = _coverage_status_class(group.document_status)
    status_chip = f'<span class="status {status_class}">{status}</span>'
    if group.document_title and group.document_url:
        return (
            f'{status_chip}<a class="sub" href="{escape(group.document_url)}">'
            f"{escape(group.document_title)}</a>"
        )
    if group.document_reason:
        return status_chip + f'<span class="sub">{escape(group.document_reason)}</span>'
    return status_chip


def _coverage_status_class(status: str) -> str:
    if status in {"ambiguous", "manual_needed"}:
        return "warn"
    if status == "matched":
        return "pass"
    if status == "not_requested":
        return "pending"
    return _status_class(status)
