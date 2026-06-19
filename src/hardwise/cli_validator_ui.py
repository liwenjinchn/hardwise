"""Single-component and batch validator UI CLI commands."""

from __future__ import annotations

from pathlib import Path

import typer


def register_validator_ui_commands(app: typer.Typer) -> None:
    """Register validator UI report commands on the root CLI app."""

    @app.command(name="report-validator-ui")
    def report_validator_ui(
        netlist_path: Path = typer.Argument(
            ...,
            help="Path to an Allegro/Telesis third-party ASCII netlist, or a Capture/Allegro PST input.",
        ),
        bom_path: Path = typer.Argument(..., help="Path to a schematic-exported BOM file."),
        refdes: str = typer.Argument(
            ..., help="Component refdes to validate in the UI detail pane."
        ),
        profile_path: Path = typer.Argument(
            ..., help="Path to a structured DatasheetProfile JSON."
        ),
        output: Path | None = typer.Option(
            None,
            "--output",
            "-o",
            help="Output HTML path (default: reports/<source>-validator-ui.html).",
        ),
    ) -> None:
        """Write a local static validator UI over one Allegro+BOM validation run."""
        from datetime import datetime, timezone

        from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
        from hardwise.ir.profile import DatasheetProfile
        from hardwise.report.validator_ui import render
        from hardwise.validation import validate_component_against_profile

        try:
            design, source, _input_type, _property_count = _load_allegro_design(netlist_path)
            bom = parse_bom(bom_path)
            bom_report = match_bom_to_design(bom, design)
            design = apply_bom_to_design(design, bom_report)
            component = design.components.get(refdes.upper())
            if component is None:
                typer.echo(f"error: refdes not found in design: {refdes}", err=True)
                raise typer.Exit(1)
            profile = DatasheetProfile.load(profile_path)
            validation_report = validate_component_against_profile(component, profile, design)
        except typer.Exit:
            raise
        except Exception as e:
            typer.echo(f"error: validator UI failed: {type(e).__name__}: {e}", err=True)
            raise typer.Exit(1) from e

        now = datetime.now(timezone.utc)
        project_name = _report_source_name(source)
        if output is None:
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            output = reports_dir / f"{project_name}-validator-ui.html"
        else:
            output.parent.mkdir(parents=True, exist_ok=True)

        html = render(
            design,
            validation_report,
            project_name=project_name,
            netlist_source=source,
            profile_path=profile_path,
            profile=profile,
            bom_report=bom_report,
            generated_at=now.isoformat(timespec="seconds"),
        )
        output.write_text(html, encoding="utf-8")
        counts = validation_report.counts_by_status
        typer.echo(
            f"validator-ui: {output} "
            f"({len(design.components)} components, selected={validation_report.refdes}, "
            f"{validation_report.status}, "
            f"PASS/WARN/ERROR={counts['PASS']}/{counts['WARN']}/{counts['ERROR']})"
        )

    @app.command(name="report-validator-ui-batch")
    def report_validator_ui_batch(
        netlist_path: Path = typer.Argument(
            ...,
            help="Path to an Allegro/Telesis third-party ASCII netlist, or a Capture/Allegro PST input.",
        ),
        bom_path: Path = typer.Argument(..., help="Path to a schematic-exported BOM file."),
        targets: list[str] | None = typer.Argument(
            None,
            help="Validation targets as REFDES=profile.json. Example: U1=data/datasheet_profiles/l78.json",
        ),
        targets_manifest: Path | None = typer.Option(
            None,
            "--targets-manifest",
            help="YAML manifest with explicit validation targets. Cannot be combined with positional targets.",
        ),
        output: Path | None = typer.Option(
            None,
            "--output",
            "-o",
            help="Output HTML path (default: reports/<source>-validator-ui-batch.html).",
        ),
    ) -> None:
        """Write a local static validator UI over multiple component validation runs."""
        from datetime import datetime, timezone

        from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
        from hardwise.ir.profile import DatasheetProfile
        from hardwise.report.validator_multi_ui import ValidatorUiResult, render
        from hardwise.validation import (
            ValidationTargetParseError,
            load_targets_manifest,
            parse_inline_targets,
            validate_component_against_profile,
        )

        try:
            if targets and targets_manifest is not None:
                typer.echo(
                    "error: use either positional REFDES=profile.json targets or "
                    "--targets-manifest, not both",
                    err=True,
                )
                raise typer.Exit(1)
            if targets_manifest is not None:
                target_specs = load_targets_manifest(targets_manifest)
            else:
                target_specs = parse_inline_targets(targets or [])

            design, source, _input_type, _property_count = _load_allegro_design(netlist_path)
            bom = parse_bom(bom_path)
            bom_report = match_bom_to_design(bom, design)
            design = apply_bom_to_design(design, bom_report)
            validation_results = []
            for target in target_specs:
                component = design.components.get(target.refdes)
                if component is None:
                    typer.echo(f"error: refdes not found in design: {target.refdes}", err=True)
                    raise typer.Exit(1)
                profile = DatasheetProfile.load(target.profile_path)
                validation = validate_component_against_profile(component, profile, design)
                validation_results.append(
                    ValidatorUiResult(
                        validation=validation,
                        profile_path=target.profile_path,
                        profile=profile,
                    )
                )
        except typer.Exit:
            raise
        except ValidationTargetParseError as e:
            typer.echo(f"error: invalid validation targets: {e}", err=True)
            raise typer.Exit(1) from e
        except Exception as e:
            typer.echo(f"error: batch validator UI failed: {type(e).__name__}: {e}", err=True)
            raise typer.Exit(1) from e

        now = datetime.now(timezone.utc)
        project_name = _report_source_name(source)
        if output is None:
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            output = reports_dir / f"{project_name}-validator-ui-batch.html"
        else:
            output.parent.mkdir(parents=True, exist_ok=True)

        html = render(
            design,
            validation_results,
            project_name=project_name,
            netlist_source=source,
            bom_report=bom_report,
            generated_at=now.isoformat(timespec="seconds"),
        )
        output.write_text(html, encoding="utf-8")
        status_counts = {
            "PASS": sum(item.validation.status == "PASS" for item in validation_results),
            "WARN": sum(item.validation.status == "WARN" for item in validation_results),
            "ERROR": sum(item.validation.status == "ERROR" for item in validation_results),
        }
        target_names = ",".join(item.validation.refdes for item in validation_results)
        typer.echo(
            f"validator-ui-batch: {output} "
            f"({len(design.components)} components, validated={target_names}, "
            f"PASS/WARN/ERROR={status_counts['PASS']}/{status_counts['WARN']}/{status_counts['ERROR']})"
        )


def _load_allegro_design(netlist_path: Path):
    """Load an Allegro schematic netlist/PST input into Design plus display metadata."""
    from hardwise.workbench.context import load_allegro_design

    return load_allegro_design(netlist_path)


def _report_source_name(source: Path) -> str:
    """Return a stable report basename for a netlist source path."""
    return source.name if source.is_dir() else source.stem
