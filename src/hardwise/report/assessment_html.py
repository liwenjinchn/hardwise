"""Canonical axes for legacy static HTML report readers."""

from html import escape

from hardwise.validation.types import ValidationReport


def assessment_table(report: ValidationReport) -> str:
    rows = [
        '<section class="section" data-section="assessment-contract">',
        "<h3>检查结果与严重度</h3>",
        "<p>结果、严重度与证据性质分别记录；人工处理不改变机器结果。</p>",
        "<table><thead><tr><th>检查</th><th>结果</th><th>严重度</th><th>证据性质</th><th>规则版本</th><th>需复核</th><th>不适用原因</th></tr></thead><tbody>",
    ]
    for item in [*report.pin_results, *report.component_checks]:
        name = getattr(item, "check", None) or f"pin:{item.pin_number}"
        rows.append(
            "<tr>"
            + "".join(
                f"<td>{escape(str(value))}</td>"
                for value in (
                    name,
                    item.result,
                    item.severity,
                    item.evidence_kind,
                    item.rule_version,
                    "需复核" if item.needs_review else "-",
                    item.not_applicable_reason or "-",
                )
            )
            + "</tr>"
        )
    if not report.pin_results and not report.component_checks:
        rows.append('<tr><td colspan="7">未评估：没有可执行检查。</td></tr>')
    rows.append("</tbody></table></section>")
    return "".join(rows)
