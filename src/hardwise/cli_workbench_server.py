"""Live workbench server CLI command."""

from __future__ import annotations

from pathlib import Path

import typer


def register_workbench_server_commands(app: typer.Typer) -> None:
    """Register live workbench server commands."""

    @app.command(name="serve-workbench")
    def serve_workbench(
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
        host: str = typer.Option("127.0.0.1", "--host", help="Host interface for localhost UI."),
        port: int = typer.Option(8765, "--port", help="Port for localhost UI."),
        tier: str = typer.Option(
            "normal", "--tier", "-t", help="Model tier: fast | normal | deep."
        ),
        fake_ai: bool = typer.Option(
            False,
            "--fake-ai",
            help="Use deterministic fake model blocks while still running the real Runner/tools.",
        ),
        persist_dir: Path = typer.Option(
            Path("data/chroma"),
            "--persist-dir",
            help="Chroma persistence directory (only used with --vector).",
        ),
        use_vector: bool = typer.Option(
            False,
            "--vector/--no-vector",
            help="Enable search_datasheet against the local Chroma store.",
        ),
        document_index: Path | None = typer.Option(
            None,
            "--document-index",
            help=(
                "Optional CSV/TSV index of public datasheet/document links. "
                "Enables document-coverage Copilot tools; no live supplier lookup."
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
        auto_datasheet_candidates: bool = typer.Option(
            True,
            "--auto-datasheet-candidates/--no-auto-datasheet-candidates",
            help=(
                "On component detail views, query Datasheets.com for MPN-like missing "
                "document candidates. This never downloads PDFs or changes validation verdicts."
            ),
        ),
        dry_run: bool = typer.Option(
            False,
            "--dry-run",
            help="Build the workbench context and exit without starting the server.",
        ),
    ) -> None:
        """Serve the Allegro-first validator workbench with live Copilot chat."""
        from dotenv import load_dotenv

        from hardwise.validation import ProfileCandidateError
        from hardwise.workbench.chat import WorkbenchChatService
        from hardwise.workbench.context import build_workbench_context
        from hardwise.workbench.server import create_workbench_app
        from hardwise.workbench.view_model import build_pin_table_summary

        if tier not in ("fast", "normal", "deep"):
            typer.echo(f"error: tier must be fast|normal|deep, got {tier!r}", err=True)
            raise typer.Exit(1)

        load_dotenv(override=True)
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
            collection = None
            if use_vector:
                from hardwise.store.vector import create_collection

                collection = create_collection(persist_dir)
            chat_service = WorkbenchChatService(
                context,
                mode="fake" if fake_ai else "real",
                tier=tier,  # type: ignore[arg-type]
                collection=collection,
            )
        except ProfileCandidateError as e:
            typer.echo(f"error: profile candidate generation failed: {e}", err=True)
            raise typer.Exit(1) from e
        except Exception as e:
            typer.echo(f"error: serve-workbench failed: {type(e).__name__}: {e}", err=True)
            raise typer.Exit(1) from e

        url = f"http://{host}:{port}"
        document_state = "off"
        if context.document_report is not None:
            doc_counts = context.document_report.counts_by_status
            document_state = (
                f"on document_index_matched={doc_counts['matched']}, no_result={doc_counts['no_result']}, "
                f"ambiguous={doc_counts['ambiguous']}, manual_needed={doc_counts['manual_needed']}"
            )
        risk_hints_state = "not_configured"
        if context.risk_hints.source_path is not None:
            risk_hints_state = (
                "loaded "
                f"accepted={context.risk_hints.accepted_count}, "
                f"rejected={context.risk_hints.rejected_count}"
            )
        pin_table_state = "not_configured"
        if context.pin_table_path is not None:
            pin_table_summary = build_pin_table_summary(context)
            affected = ",".join(pin_table_summary.affected_refdes_list) or "-"
            rejected = ",".join(pin_table_summary.rejected_unknown_refdes) or "-"
            pin_table_state = (
                f"loaded accepted={pin_table_summary.accepted_findings}, "
                f"affected_refdes={pin_table_summary.affected_refdes} [{affected}], "
                f"rejected_unknown_refdes={pin_table_summary.rejected_findings} [{rejected}]"
            )
        review_package_state = "not_configured"
        if context.review_package.source_path is not None:
            pkg_counts = context.review_package.counts
            review_package_state = (
                f"loaded package_status={context.review_package.package_status}, "
                f"status_group={context.review_package.status_group}, "
                f"manual_gaps={context.review_package.manual_gap_count}, "
                f"present={pkg_counts['present']}, "
                f"missing_required={pkg_counts['missing_required']}, "
                f"missing_optional={pkg_counts['missing_optional']}, "
                f"hash_mismatch={pkg_counts['hash_mismatch']}"
            )
        typer.echo(
            f"serve-workbench: {url} "
            f"({context.index.components_in_design} components, "
            f"validated={len(context.index.validated_rows)}, "
            f"mode={'fake' if fake_ai else 'real'}, vector={'on' if use_vector else 'off'}, "
            f"document-index={document_state}, risk-hints={risk_hints_state}, "
            f"pin-table={pin_table_state}, "
            f"review-package={review_package_state}, "
            f"datasheet-candidates={'auto' if auto_datasheet_candidates else 'off'})"
        )
        if dry_run:
            return

        import uvicorn

        app_obj = create_workbench_app(
            context,
            chat_service,
            profiles=profiles,
            document_index=document_index,
            pin_table=pin_table,
            review_package_manifest=review_package_manifest,
            auto_datasheet_candidates=auto_datasheet_candidates,
        )
        uvicorn.run(app_obj, host=host, port=port)
