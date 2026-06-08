"""Static HTML renderer for Hardwise trust dashboard summaries."""

from __future__ import annotations

from html import escape
from typing import Any

from hardwise.analytics.trust_dashboard_assets import TRUST_DASHBOARD_STYLE
from hardwise.analytics.trust_types import TrustDashboardSummary
from hardwise.trust import trust_label_text


def render_trust_dashboard_html(summary: TrustDashboardSummary) -> str:
    """Render a portable static Trust & Coverage dashboard."""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Hardwise Trust & Coverage Dashboard</title>
  <style>{TRUST_DASHBOARD_STYLE}</style>
</head>
<body>
  <main class="shell">
    <header class="hero">
      <div>
        <p class="eyebrow">Hardwise Analytics</p>
        <h1>Trust & Coverage Dashboard</h1>
        <p class="lede">{escape(summary.caveat)}</p>
      </div>
      <div class="stamp">
        <span>Generated</span>
        <strong>{escape(summary.generated_at)}</strong>
      </div>
    </header>
    {_eval_section(summary)}
    {_validation_section(summary)}
    {_trace_section(summary)}
    {_source_section(summary)}
  </main>
</body>
</html>
"""


def _eval_section(summary: TrustDashboardSummary) -> str:
    health = summary.eval_health
    project_status = f"{health.projects_passed}/{health.projects_total}"
    guard_class = "ok" if health.guardrail_status == "pass" else "warn"
    return f"""
    <section class="band">
      <div class="section-head">
        <div>
          <p class="eyebrow">Eval Pack Health</p>
          <h2>{escape(health.manifest_name)}</h2>
        </div>
        <span class="pill {guard_class}">guardrail {escape(health.guardrail_status)}</span>
      </div>
      <div class="cards">
        {_card("Projects Passed", project_status, f"{health.projects_failed} failed")}
        {_card("Components", health.components_total, f"{health.nc_pins_total} NC pins")}
        {_card("Findings", health.findings_total, "deterministic checks")}
        {_card("Refdes Wrapped", health.unverified_refdes_wrapped, "must stay at 0")}
        {_card("Evidence Drops", health.findings_dropped_no_evidence, "must stay at 0")}
      </div>
      <div class="split">
        {_bar_table("Findings By Rule", health.findings_by_rule)}
        {_bar_table("Findings By Decision", health.findings_by_decision)}
      </div>
      {_comparison_block(summary)}
    </section>
"""


def _comparison_block(summary: TrustDashboardSummary) -> str:
    comparison = summary.comparison
    if comparison is None:
        state = summary.sources["comparison"]
        return f'<p class="note">Comparison: {escape(state.status)}. {escape(state.message)}</p>'
    klass = "ok" if comparison.status == "passed" else "warn"
    rows = "".join(
        f"<li>{escape(item)}</li>"
        for item in (comparison.regressions + comparison.improvements + comparison.observations)[:8]
    )
    if not rows:
        rows = "<li>No deltas recorded.</li>"
    return f"""
      <div class="callout {klass}">
        <strong>Baseline comparison: {escape(comparison.status)}</strong>
        <ul>{rows}</ul>
      </div>
"""


def _validation_section(summary: TrustDashboardSummary) -> str:
    coverage = summary.validation_coverage
    if not coverage.available:
        return _unavailable_section("Validation Coverage", coverage.source.message)
    return f"""
    <section class="band">
      <div class="section-head">
        <div>
          <p class="eyebrow">Validation Coverage</p>
          <h2>{escape(coverage.project_name or "Project index")}</h2>
        </div>
        <span class="pill">static index JSON</span>
      </div>
      <div class="cards">
        {_card("Components", coverage.components_in_design, f"{coverage.bom_matched} BOM matched")}
        {_card(
            "Validated",
            coverage.validated_components,
            f"{coverage.coverage_percent:.1f}% coverage",
        )}
        {_card("Manual", coverage.manual_components, f"{coverage.manual_percent:.1f}% remaining")}
        {_card("PASS", coverage.pass_warn_error.get("PASS", 0), "component verdicts")}
        {_card("WARN", coverage.pass_warn_error.get("WARN", 0), "component verdicts")}
        {_card("ERROR", coverage.pass_warn_error.get("ERROR", 0), "component verdicts")}
      </div>
      <div class="split">
        {_bar_table("Match Status", coverage.match_status_counts)}
        {_bar_table("Document Coverage", coverage.document_status_counts)}
      </div>
      {_gap_table(coverage.top_profile_gaps)}
      <p class="note">{escape(coverage.scope or "Scope caveat was not present in the index.")}</p>
    </section>
"""


def _trace_section(summary: TrustDashboardSummary) -> str:
    trace = summary.trace_health
    if not trace.available:
        return _unavailable_section("Trust Trace", trace.source.message)
    note_rows = "".join(f"<li>{escape(note)}</li>" for note in trace.notes)
    return f"""
    <section class="band">
      <div class="section-head">
        <div>
          <p class="eyebrow">Trust Trace</p>
          <h2>Tool-backed evidence trail</h2>
        </div>
        <span class="pill">rows {trace.rows_read}</span>
      </div>
      <div class="cards">
        {_card("Review Runs", trace.review_runs, f"{trace.review_findings_total} findings")}
        {_card("Workbench Turns", trace.workbench_turns, "ChatResponse traces")}
        {_card("Vector Runs", trace.vector_enabled_runs, "datasheet search enabled")}
        {_card("Wrapped Refdes", trace.unverified_refdes_wrapped, "guard activity")}
        {_card("Evidence Drops", trace.findings_dropped_no_evidence, "ledger activity")}
      </div>
      {_bar_table("Trust Tier Counts", _trust_labels(trace.trust_tier_counts))}
      {_trace_examples(trace.examples)}
      {f'<ul class="notes">{note_rows}</ul>' if note_rows else ''}
    </section>
"""


def _source_section(summary: TrustDashboardSummary) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{escape(name)}</td>"
        f"<td><span class=\"status {escape(state.status)}\">{escape(state.status)}</span></td>"
        f"<td>{escape(state.path or '-')}</td>"
        f"<td>{escape(state.message)}</td>"
        "</tr>"
        for name, state in summary.sources.items()
    )
    return f"""
    <section class="band">
      <div class="section-head">
        <div>
          <p class="eyebrow">Sources</p>
          <h2>Machine-readable inputs only</h2>
        </div>
      </div>
      <table>
        <thead><tr><th>Input</th><th>Status</th><th>Path</th><th>Note</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
"""


def _unavailable_section(title: str, message: str) -> str:
    return f"""
    <section class="band muted">
      <div class="section-head">
        <div>
          <p class="eyebrow">Unavailable</p>
          <h2>{escape(title)}</h2>
        </div>
      </div>
      <p class="note">{escape(message)}</p>
    </section>
"""


def _card(label: str, value: Any, sub: str) -> str:
    return (
        '<div class="card">'
        f"<span>{escape(str(label))}</span>"
        f"<strong>{escape(str(value))}</strong>"
        f"<small>{escape(str(sub))}</small>"
        "</div>"
    )


def _bar_table(title: str, values: dict[str, int]) -> str:
    rows = []
    max_value = max(values.values(), default=0)
    for key, value in sorted(values.items()):
        width = 0 if max_value <= 0 else max(4, int((value / max_value) * 100))
        rows.append(
            "<tr>"
            f"<td>{escape(str(key))}</td>"
            f"<td><div class=\"bar\"><i style=\"width:{width}%\"></i></div></td>"
            f"<td class=\"num\">{value}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="3">No rows.</td></tr>')
    return (
        '<div class="panel">'
        f"<h3>{escape(title)}</h3>"
        "<table><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def _gap_table(gaps: list[dict[str, Any]]) -> str:
    if not gaps:
        return '<p class="note">No profile gap groups recorded.</p>'
    rows = "".join(
        "<tr>"
        f"<td>{escape(str(gap.get('refdes_count', 0)))}</td>"
        f"<td>{escape(str(gap.get('match_status', '-')))}</td>"
        f"<td>{escape(str(gap.get('identity', '-')))}</td>"
        f"<td>{escape(str(gap.get('identity_kind', '-')))}</td>"
        f"<td>{escape(', '.join(str(item) for item in gap.get('refdes_sample', [])))}</td>"
        f"<td>{escape(str(gap.get('reason', '-')))}</td>"
        "</tr>"
        for gap in gaps
    )
    return (
        '<div class="panel full"><h3>Top Profile Gaps</h3><table>'
        "<thead><tr><th>Count</th><th>Status</th><th>Identity</th><th>Kind</th>"
        "<th>Refdes Sample</th><th>Reason</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def _trace_examples(examples: list[Any]) -> str:
    if not examples:
        return '<p class="note">No workbench trace examples were present.</p>'
    rows = "".join(
        "<tr>"
        f"<td>{escape(example.label)}</td>"
        f"<td>{escape(example.tool)}</td>"
        f"<td>{escape(example.summary)}</td>"
        f"<td>{escape(', '.join(example.evidence) or '-')}</td>"
        f"<td>{example.wrapped}</td>"
        "</tr>"
        for example in examples
    )
    return (
        '<div class="panel full"><h3>Trace Examples</h3><table>'
        "<thead><tr><th>Tier</th><th>Tool</th><th>Summary</th><th>Evidence</th>"
        "<th>Wrapped</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def _trust_labels(values: dict[str, int]) -> dict[str, int]:
    return {
        trust_label_text("l1"): values.get("l1", 0),
        trust_label_text("l2"): values.get("l2", 0),
        trust_label_text("l3"): values.get("l3", 0),
    }
