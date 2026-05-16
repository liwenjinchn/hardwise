"""HTML rendering for Hardwise Eval Pack summaries."""

from __future__ import annotations

from typing import Any


def render_eval_html(summary: Any) -> str:
    """Render a small self-contained eval summary."""

    rows = "\n".join(_render_result_row(r) for r in summary.results)
    guardrail_section = _render_guardrail_section(summary.unverified_refdes_samples)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Hardwise Eval Summary</title>
  <style>
    body {{ margin: 0; font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #17211c; background: #f7f8f6; }}
    header {{ padding: 32px 40px 22px; background: #10231d; color: #f4f7f2; }}
    h1 {{ margin: 0 0 8px; font-size: 30px; letter-spacing: 0; }}
    main {{ padding: 28px 40px 44px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 24px; }}
    .metric {{ background: white; border: 1px solid #d9dfd7; border-radius: 8px; padding: 14px; }}
    .metric span {{ display: block; color: #5f6d65; font-size: 12px; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #d9dfd7; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid #e6ebe4; text-align: left; vertical-align: top; }}
    th {{ background: #edf2ec; font-size: 12px; color: #435047; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }}
    .ok {{ color: #17693b; font-weight: 700; }}
    .bad {{ color: #9b2c2c; font-weight: 700; }}
  </style>
</head>
<body>
  <header>
    <h1>Hardwise Eval Summary</h1>
    <div>{summary.manifest_name} · {summary.generated_at}</div>
  </header>
  <main>
    <section class="grid">
      <div class="metric"><span>Repos</span><strong>{summary.repos_total}</strong></div>
      <div class="metric"><span>Projects Passed</span><strong>{summary.projects_passed}/{summary.projects_total}</strong></div>
      <div class="metric"><span>Components</span><strong>{summary.components_total}</strong></div>
      <div class="metric"><span>NC Pins</span><strong>{summary.nc_pins_total}</strong></div>
      <div class="metric"><span>Findings</span><strong>{summary.findings_total}</strong></div>
      <div class="metric"><span>Refdes Wrapped</span><strong>{summary.unverified_refdes_wrapped}</strong></div>
    </section>
    <table>
      <thead>
        <tr><th>Repo</th><th>Project</th><th>Status</th><th>Components</th><th>NC Pins</th><th>Findings</th><th>Rules</th><th>Error</th></tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
    {guardrail_section}
  </main>
</body>
</html>
"""


def _render_result_row(result: Any) -> str:
    status_class = "ok" if result.status == "passed" else "bad"
    rules = ", ".join(f"{k}:{v}" for k, v in sorted(result.findings_by_rule.items()))
    return (
        "<tr>"
        f"<td><code>{_esc(result.repo)}</code></td>"
        f"<td><code>{_esc(result.project_dir)}</code></td>"
        f"<td class=\"{status_class}\">{_esc(result.status)}</td>"
        f"<td>{result.components}</td>"
        f"<td>{result.nc_pins}</td>"
        f"<td>{result.findings_total}</td>"
        f"<td>{_esc(rules)}</td>"
        f"<td>{_esc(result.error or '')}</td>"
        "</tr>"
    )


def _render_guardrail_section(samples: list[str]) -> str:
    if not samples:
        return ""
    items = "\n".join(f"<li><code>{_esc(sample)}</code></li>" for sample in samples)
    return f"""
    <section>
      <h2>Guardrail Samples</h2>
      <ul>{items}</ul>
    </section>
"""


def _esc(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
