"""Static design-validator workbench CLI command."""

from __future__ import annotations

from pathlib import Path

import typer

from hardwise.path_display import display_path


def register_design_validator_commands(app: typer.Typer) -> None:
    """Register static design-validator workbench commands."""

    @app.command(name="design-validator-ui")
    def design_validator_ui(
        netlist_path: Path = typer.Argument(
            ...,
            help="Path to an Allegro/Telesis third-party ASCII netlist, or a Capture/Allegro PST input.",
        ),
        bom_path: Path | None = typer.Argument(
            None,
            help=(
                "Path to a schematic-exported BOM file. If omitted, "
                "BOM candidates are auto-selected from an Allegro/PST project directory."
            ),
        ),
        profiles: Path = typer.Option(
            Path("data/datasheet_profiles"),
            "--profiles",
            help="Directory containing structured DatasheetProfile JSON files.",
        ),
        output: Path | None = typer.Option(
            None,
            "--output",
            "-o",
            help="Output HTML path (default: reports/<source>-design-validator.html).",
        ),
        index_output: Path | None = typer.Option(
            None,
            "--index-output",
            help="Optional markdown project validation index path.",
        ),
        index_json: Path | None = typer.Option(
            None,
            "--index-json",
            help="Optional JSON sidecar path for the project validation index.",
        ),
        document_index: Path | None = typer.Option(
            None,
            "--document-index",
            help=(
                "Optional CSV/TSV index of public datasheet/document links. "
                "Adds grouped document coverage; no live supplier lookup."
            ),
        ),
        risk_hints_json: Path | None = typer.Option(
            None,
            "--risk-hints-json",
            help="Optional external risk-hints JSON anchored to registry-verified refdes.",
        ),
        review_package_manifest: Path | None = typer.Option(
            None,
            "--review-package",
            help=(
                "Optional YAML/JSON manifest for schematic PDF, ERC/DRC, checklist, "
                "and review-note artifacts. Records evidence presence only."
            ),
        ),
        pin_table: Path | None = typer.Option(
            None,
            "--pin-table",
            help=(
                "Optional Capture pin-table CSV. Runs R008/R009/R010 into workbench review tasks; "
                "does not change ValidationReport PASS/WARN/ERROR totals."
            ),
        ),
        manual_limit: int = typer.Option(
            50,
            "--manual-limit",
            help="Maximum no-profile/manual rows shown in the optional markdown index.",
        ),
        ai_snapshot: bool = typer.Option(
            False,
            "--ai-snapshot",
            help="Embed the offline audited Copilot panel snapshot in the static HTML.",
        ),
    ) -> None:
        """Write a screenshot-like static design-validator workbench for matched profiles."""
        from hardwise.report.project_validation_markdown import (
            render as render_project_index,
            write_json,
        )
        from hardwise.report.validator_project_ui import render_project_workbench
        from hardwise.report.workbench_spa_snapshot import render_spa_snapshot
        from hardwise.validation import ProfileCandidateError
        from hardwise.workbench.context import build_workbench_context
        from hardwise.workbench.view_model import build_pin_table_summary

        if manual_limit < 0:
            typer.echo("error: --manual-limit must be >= 0", err=True)
            raise typer.Exit(1)

        try:
            context = build_workbench_context(
                netlist_path=netlist_path,
                bom_path=bom_path,
                profiles=profiles,
                document_index=document_index,
                risk_hints_json=risk_hints_json,
                review_package_manifest=review_package_manifest,
                pin_table=pin_table,
            )
        except ProfileCandidateError as e:
            typer.echo(f"error: profile candidate generation failed: {e}", err=True)
            raise typer.Exit(1) from e
        except Exception as e:
            typer.echo(f"error: design validator UI failed: {type(e).__name__}: {e}", err=True)
            raise typer.Exit(1) from e

        if output is None:
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            output = reports_dir / f"{context.project_name}-design-validator.html"
        else:
            output.parent.mkdir(parents=True, exist_ok=True)

        if ai_snapshot:
            html = render_spa_snapshot(context, datasheet_search_enabled=False)
        else:
            pin_table_summary = build_pin_table_summary(context)
            html = render_project_workbench(
                context.design,
                context.index,
                project_name=context.project_name,
                netlist_source=context.netlist_source,
                bom_report=context.bom_report,
                generated_at=context.index.generated_at,
                risk_hints=context.risk_hints if context.risk_hints.source_path else None,
                pin_table=(
                    pin_table_summary if pin_table_summary.status == "loaded" else None
                ),
                review_package=(
                    context.review_package if context.review_package.source_path else None
                ),
            )
        output.write_text(html, encoding="utf-8")

        if index_output is not None:
            index_output.parent.mkdir(parents=True, exist_ok=True)
            index_output.write_text(
                render_project_index(context.index, manual_limit=manual_limit),
                encoding="utf-8",
            )
        if index_json is not None:
            write_json(context.index, index_json)

        totals = context.index.totals
        typer.echo(f"selected-netlist: {display_path(context.netlist_source)}")
        typer.echo(f"selected-bom: {display_path(context.bom.source_file)}")
        if context.document_report is not None:
            doc_counts = context.document_report.counts_by_status
            typer.echo(
                f"document-index: {display_path(context.document_report.document_index_file)} "
                f"(document_index_matched={doc_counts['matched']}, no_result={doc_counts['no_result']}, "
                f"ambiguous={doc_counts['ambiguous']}, manual_needed={doc_counts['manual_needed']})"
            )
        if context.risk_hints.source_path is not None:
            typer.echo(
                "risk-hints: loaded "
                f"(accepted={context.risk_hints.accepted_count}, "
                f"rejected={context.risk_hints.rejected_count})"
            )
        if context.review_package.source_path is not None:
            pkg_counts = context.review_package.counts
            typer.echo(
                f"review-package: {context.review_package.source_path} "
                f"(package_status={context.review_package.package_status}, "
                f"status_group={context.review_package.status_group}, "
                f"manual_gaps={context.review_package.manual_gap_count}, "
                f"present={pkg_counts['present']}, "
                f"missing_required={pkg_counts['missing_required']}, "
                f"missing_optional={pkg_counts['missing_optional']}, "
                f"hash_mismatch={pkg_counts['hash_mismatch']})"
            )
        if context.pin_table_path is not None:
            pin_table_summary = build_pin_table_summary(context)
            affected = ",".join(pin_table_summary.affected_refdes_list) or "-"
            rejected = ",".join(pin_table_summary.rejected_unknown_refdes) or "-"
            typer.echo(
                f"pin-table: {display_path(context.pin_table_path)} "
                f"(accepted={pin_table_summary.accepted_findings}, "
                f"affected_refdes={pin_table_summary.affected_refdes} [{affected}], "
                f"rejected_unknown_refdes={pin_table_summary.rejected_findings} [{rejected}])"
            )
        if context.resolved_bom.auto_selected:
            parseable_count = sum(
                item.status != "parse_error" for item in context.resolved_bom.candidates
            )
            typer.echo(
                f"bom-candidates: {len(context.resolved_bom.candidates)} "
                f"(parseable={parseable_count}, selected={context.bom.source_file.name})"
            )
        if ai_snapshot:
            typer.echo("ai-snapshot: enabled")
        typer.echo(
            f"design-validator-ui: {output} "
            f"({context.index.components_in_design} components, "
            f"validated={len(context.index.validated_rows)}, "
            f"bom_rows_matched={context.index.bom_matched}, "
            f"PASS/WARN/ERROR={totals['PASS']}/{totals['WARN']}/{totals['ERROR']}, "
            f"manual={len(context.index.manual_rows)})"
        )
        if index_output is not None:
            typer.echo(f"validation-index: {index_output}")
        if index_json is not None:
            typer.echo(f"validation-index-json: {index_json} ({len(context.index.rows)} rows)")
