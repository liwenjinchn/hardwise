"""Trust analytics CLI commands."""

from __future__ import annotations

from pathlib import Path

import typer

commands = typer.Typer()


@commands.command(name="trust-dashboard")
def trust_dashboard(
    eval_summary: Path = typer.Option(
        Path("reports/eval/eval-summary.json"),
        "--eval-summary",
        help="Eval Pack summary JSON produced by `hardwise eval`.",
    ),
    validation_index: Path | None = typer.Option(
        None,
        "--validation-index",
        help="Project validation index JSON produced by `design-validator-ui --index-json`.",
    ),
    trace: Path | None = typer.Option(
        None,
        "--trace",
        help="Optional review trace JSONL or workbench ChatResponse JSON/JSON array.",
    ),
    comparison: Path | None = typer.Option(
        None,
        "--comparison",
        help="Optional eval comparison JSON produced by `hardwise eval --baseline`.",
    ),
    output: Path = typer.Option(
        Path("reports/trust-dashboard.html"),
        "--output",
        "-o",
        help="Output static HTML dashboard path.",
    ),
    json_output: Path | None = typer.Option(
        None,
        "--json-output",
        help="Optional JSON summary output path.",
    ),
) -> None:
    """Render a static Trust & Coverage dashboard from machine-readable artifacts."""
    import json

    from hardwise.analytics.trust_dashboard import (
        TrustDashboardError,
        build_trust_dashboard_summary,
    )
    from hardwise.analytics.trust_dashboard_html import render_trust_dashboard_html

    try:
        summary = build_trust_dashboard_summary(
            eval_summary_path=eval_summary,
            validation_index_path=validation_index,
            trace_path=trace,
            comparison_path=comparison,
        )
    except TrustDashboardError as e:
        typer.echo(f"error: trust dashboard failed: {e}", err=True)
        raise typer.Exit(1) from e

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_trust_dashboard_html(summary), encoding="utf-8")
    if json_output is not None:
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(
            json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    validation_state = summary.validation_coverage.source.status
    trace_state = summary.trace_health.source.status
    typer.echo(
        f"trust-dashboard: {output} "
        f"(eval={summary.eval_health.projects_passed}/{summary.eval_health.projects_total}, "
        f"validation={validation_state}, trace={trace_state})"
    )
    if json_output is not None:
        typer.echo(f"trust-dashboard-json: {json_output}")


def register_commands(app: typer.Typer) -> None:
    """Register this command group on the root CLI app."""
    app.registered_commands.extend(commands.registered_commands)
