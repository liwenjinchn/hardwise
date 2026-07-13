"""Eval Pack CLI command registration."""

from __future__ import annotations

from pathlib import Path

import typer


def register_eval_commands(app: typer.Typer) -> None:
    """Register public-corpus eval commands on the root CLI app."""

    @app.command(name="eval")
    def eval_pack(
        manifest: Path = typer.Option(
            Path("eval/manifest.yaml"),
            "--manifest",
            help="Eval manifest YAML.",
        ),
        projects_root: Path = typer.Option(
            Path("eval/projects"),
            "--projects-root",
            help="Directory containing checked-out public eval repos.",
        ),
        output_dir: Path = typer.Option(
            Path("reports/eval"),
            "--output-dir",
            help="Directory for eval-summary.json/html.",
        ),
        download: bool = typer.Option(
            False,
            "--download/--no-download",
            help="Clone missing repos from the manifest at their pinned commits.",
        ),
        limit_projects: int | None = typer.Option(
            None,
            "--limit-projects",
            help="Stop after N discovered project directories. Useful while iterating.",
        ),
        baseline: Path | None = typer.Option(
            None,
            "--baseline",
            help="Accepted eval-summary.json to compare against.",
        ),
        accept_baseline: bool = typer.Option(
            False,
            "--accept-baseline",
            help="Copy this run's summary to --baseline after the run.",
        ),
        static_snapshot: bool = typer.Option(
            False,
            "--static-snapshot",
            help=(
                "Write the bundled accepted offline eval snapshot instead of cloning/parsing "
                "public repos. Reproduces the 1707 components / 437 findings demo headline."
            ),
        ),
    ) -> None:
        """Run the public-corpus Hardwise Eval Pack MVP."""
        from hardwise.eval_pack import load_static_eval_snapshot, run_eval, write_eval_outputs

        if accept_baseline and baseline is None:
            typer.echo("error: --accept-baseline requires --baseline", err=True)
            raise typer.Exit(1)
        if static_snapshot and (baseline is not None or accept_baseline):
            typer.echo(
                "error: --static-snapshot does not support --baseline/--accept-baseline",
                err=True,
            )
            raise typer.Exit(1)

        try:
            if static_snapshot:
                outputs = write_eval_outputs(load_static_eval_snapshot(), output_dir)
            else:
                outputs = run_eval(
                    manifest_path=manifest,
                    projects_root=projects_root,
                    output_dir=output_dir,
                    download=download,
                    limit_projects=limit_projects,
                    baseline_path=baseline,
                    accept_baseline=accept_baseline,
                )
        except Exception as e:
            typer.echo(f"error: eval failed: {type(e).__name__}: {e}", err=True)
            raise typer.Exit(1) from e

        summary = outputs.summary
        typer.echo(
            f"eval{' static-snapshot' if static_snapshot else ''}: {summary.manifest_name} "
            f"({summary.projects_passed}/{summary.projects_total} projects passed, "
            f"{summary.findings_total} findings)"
        )
        _echo_decision_counts(summary.findings_by_decision, summary.findings_total)
        typer.echo(f"summary: {outputs.summary_path}")
        typer.echo(f"html: {outputs.html_path}")
        if outputs.comparison is not None and outputs.comparison_path is not None:
            typer.echo(
                f"comparison: {outputs.comparison_path} "
                f"({outputs.comparison.status}, "
                f"{len(outputs.comparison.regressions)} regressions)"
            )
            if outputs.comparison.status == "failed":
                for regression in outputs.comparison.regressions:
                    typer.echo(f"regression: {regression}", err=True)
                raise typer.Exit(2)
        if accept_baseline and baseline is not None:
            typer.echo(f"baseline accepted: {baseline}")

    @app.command(name="eval-seeded-defects")
    def eval_seeded_defects(
        fixture: Path = typer.Option(
            Path("tests/fixtures/allegro/pst"),
            "--fixture",
            help="Clean Allegro PST passive fixture directory to mutate.",
        ),
        fixtures_root: Path = typer.Option(
            Path("tests/fixtures/allegro"),
            "--fixtures-root",
            help="Directory containing clean public/synthetic family fixtures.",
        ),
        matrix: Path = typer.Option(
            Path("tests/fixtures/eval/seeded_family_matrix.json"),
            "--matrix",
            help="Versioned seeded family-matrix JSON.",
        ),
        profiles: Path = typer.Option(
            Path("data/datasheet_profiles"),
            "--profiles",
            help="Directory containing structured DatasheetProfile JSON files.",
        ),
        output: Path | None = typer.Option(
            None,
            "--output",
            help="Optional JSON output path for seeded benchmark details.",
        ),
    ) -> None:
        """Run the Allegro seeded-defect family calibration matrix."""
        from hardwise.eval_seeded import (
            run_seeded_defect_benchmark,
            write_seeded_defect_summary,
        )

        try:
            summary = run_seeded_defect_benchmark(
                fixture=fixture,
                fixtures_root=fixtures_root,
                matrix=matrix,
                profiles=profiles,
            )
            if output is not None:
                write_seeded_defect_summary(summary, output)
        except Exception as e:
            typer.echo(f"error: seeded-defect eval failed: {type(e).__name__}: {e}", err=True)
            raise typer.Exit(1) from e

        typer.echo(f"eval seeded-defects: {summary.headline}")
        for family in summary.family_metrics:
            typer.echo(
                f"  family {family.family}: recall "
                f"{family.recall}/{family.seeded_defects}, "
                f"{family.false_positives} false positives"
            )
        for case in summary.cases:
            status = "detected" if case.detected else "missed"
            typer.echo(
                f"  {case.name} [{case.family}]: {status} "
                f"({len(case.false_positives)} false positives)"
            )
        if output is not None:
            typer.echo(f"summary: {output}")


def _echo_decision_counts(counts: dict[str, int], total: int) -> None:
    typer.echo("decisions:")
    for decision in ("likely_issue", "reviewer_to_confirm", "likely_ok", "undecided"):
        count = int(counts.get(decision, 0))
        percentage = (count / total * 100) if total else 0.0
        typer.echo(f"  {decision}: {count} ({percentage:.1f}%)")
