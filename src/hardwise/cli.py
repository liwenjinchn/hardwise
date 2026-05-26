"""Hardwise CLI entry point."""

from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(help="Hardwise — hardware R&D review Agent.")


@app.callback()
def _root() -> None:
    """Force Typer to treat this as a multi-command app even when only one command is registered."""


@app.command()
def hello() -> None:
    """Sanity check that the install worked."""
    typer.echo("hardwise installed.")


@app.command(name="verify-api")
def verify_api(
    tier: str = typer.Option(
        "normal",
        "--tier",
        "-t",
        help="Model tier (fast | normal | deep). Default: normal.",
    ),
) -> None:
    """Send a one-shot test message to the upstream API; print response and token counts."""
    import os

    from anthropic import Anthropic
    from dotenv import load_dotenv

    from hardwise.agent.router import ModelRouter

    load_dotenv(override=True)

    if tier not in ("fast", "normal", "deep"):
        typer.echo(f"error: tier must be fast|normal|deep, got {tier!r}", err=True)
        raise typer.Exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    model = ModelRouter().select(tier)  # type: ignore[arg-type]

    if not api_key or api_key == "replace_me":
        typer.echo("error: ANTHROPIC_API_KEY missing or unset in .env", err=True)
        raise typer.Exit(1)

    typer.echo(f"calling {model} (tier={tier}) via {base_url}")

    client = Anthropic(api_key=api_key, base_url=base_url)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=64,
            messages=[{"role": "user", "content": "Reply with exactly: hardwise api ok"}],
        )
    except Exception as e:
        typer.echo(f"error: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    text = response.content[0].text if response.content else "(empty)"
    typer.echo(f"model: {response.model}")
    typer.echo(f"content: {text}")
    typer.echo(f"tokens in/out: {response.usage.input_tokens}/{response.usage.output_tokens}")


@app.command(name="inspect-kicad")
def inspect_kicad(
    project_dir: Path = typer.Argument(..., help="Path to a KiCad project directory."),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of components to print."),
    show_nets: bool = typer.Option(
        False,
        "--net",
        help=(
            "Print PCB-side net summary instead of components. Reads from .kicad_pcb; "
            "this is a diagnostic on already-laid-out projects, not pre-Layout "
            "schematic-review evidence. Defaults to signal nets only (KiCad's auto "
            "unconnected-(Ref-Pad) entries hidden); pass --all-nets for the full count."
        ),
    ),
    all_nets: bool = typer.Option(
        False,
        "--all-nets",
        help=(
            "With --net, include unconnected-(Ref-Pad) entries so the count matches "
            "KiCad's PCB Net Inspector. No effect without --net."
        ),
    ),
) -> None:
    """Parse a KiCad project and print the initial refdes registry."""
    from hardwise.adapters.kicad import parse_project, pcb_signal_nets

    try:
        registry = parse_project(project_dir)
    except Exception as e:
        typer.echo(f"error: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    typer.echo(f"project: {registry.project_dir}")
    typer.echo(f"components: {len(registry.components)}")
    if show_nets:
        all_count = len(registry.pcb_nets)
        signal = pcb_signal_nets(registry.pcb_nets)
        unconnected = all_count - len(signal)
        typer.echo(
            f"pcb nets: {len(signal)} signal "
            f"(+{unconnected} unconnected = {all_count} total in PCB)"
        )
        typer.echo("source: .kicad_pcb (post-Layout fact; not pre-Layout review evidence)")
        nets_to_show = registry.pcb_nets if all_nets else signal
        note = (
            "showing all PCB nets (use without --all-nets for signal-only)"
            if all_nets
            else "showing PCB signal nets only (pass --all-nets to include unconnected-*)"
        )
        typer.echo(note)
        typer.echo("")
        top = sorted(nets_to_show, key=lambda n: (-len(n.members), n.name))[:limit]
        for net in top:
            typer.echo(f"{net.name:32} {len(net.members):4d} members")
        return
    typer.echo("")
    for component in registry.components[:limit]:
        footprint = component.footprint or "-"
        value = component.value or "-"
        typer.echo(f"{component.refdes:8} {value:16} {footprint}")


@app.command(name="inspect-allegro-netlist")
def inspect_allegro_netlist(
    netlist_path: Path = typer.Argument(
        ...,
        help=(
            "Path to an Allegro/Telesis third-party ASCII netlist, or a "
            "Capture/Allegro PST directory/file containing pstxnet.dat + pstxprt.dat."
        ),
    ),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of nets to print."),
) -> None:
    """Parse an Allegro schematic netlist and print topology."""
    try:
        design, source, input_type, property_count = _load_allegro_design(netlist_path)
    except Exception as e:
        typer.echo(f"error: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    typer.echo(f"source: {source}")
    typer.echo(f"type: {input_type}")
    typer.echo("scope: pre-Layout connectivity only; no .brd, boardview, or PCB geometry parsed")
    typer.echo(f"components: {len(design.components)}")
    typer.echo(f"nets: {len(design.nets)}")
    typer.echo(f"properties: {property_count}")
    typer.echo("")
    top = sorted(design.nets.values(), key=lambda n: (-len(n.nodes), n.name))[:limit]
    for net in top:
        typer.echo(f"{net.name:32} {len(net.nodes):4d} members")


@app.command(name="inspect-bom-match")
def inspect_bom_match(
    netlist_path: Path = typer.Argument(
        ...,
        help=(
            "Path to an Allegro/Telesis third-party ASCII netlist, or a "
            "Capture/Allegro PST directory/file."
        ),
    ),
    bom_path: Path = typer.Argument(..., help="Path to a schematic-exported BOM file."),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of mismatches to print."),
) -> None:
    """Match a schematic BOM to an Allegro netlist by refdes."""
    from hardwise.bom import match_bom_to_design, parse_bom

    try:
        design, source, input_type, _property_count = _load_allegro_design(netlist_path)
        bom = parse_bom(bom_path)
        report = match_bom_to_design(bom, design)
    except Exception as e:
        typer.echo(f"error: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    typer.echo(f"netlist: {source}")
    typer.echo(f"netlist type: {input_type}")
    typer.echo(f"bom: {bom.source_file}")
    typer.echo("scope: component identity match only; no PLM, lifecycle, pricing, or PCB geometry")
    typer.echo(f"design refdes: {report.design_refdes_count}")
    typer.echo(f"bom items: {report.bom_item_count}")
    typer.echo(f"bom refdes rows: {report.bom_row_count}")
    typer.echo(f"non-refdes bom items: {report.non_refdes_item_count}")
    typer.echo(f"matched refdes: {len(report.matched_refdes)}")
    typer.echo(f"bom-only refdes: {len(report.bom_only_refdes)}")
    typer.echo(f"design-only refdes: {len(report.design_only_refdes)}")
    typer.echo(f"duplicate bom refdes: {len(report.duplicate_bom_refdes)}")
    typer.echo(f"quantity mismatches: {len(report.quantity_mismatches)}")
    typer.echo(f"status: {'clean refdes match' if report.is_clean else 'mismatch found'}")

    _echo_refdes_sample("bom-only", report.bom_only_refdes, limit)
    _echo_refdes_sample("design-only", report.design_only_refdes, limit)
    _echo_refdes_sample("duplicate-bom", report.duplicate_bom_refdes, limit)
    if report.quantity_mismatches:
        typer.echo("")
        typer.echo("quantity-mismatch sample:")
        for mismatch in report.quantity_mismatches[:limit]:
            typer.echo(
                f"  item {mismatch.item_number or '-'} line {mismatch.source_line}: "
                f"quantity={mismatch.quantity}, refdes={mismatch.refdes_count}"
            )


@app.command(name="report-allegro-bom")
def report_allegro_bom(
    netlist_path: Path = typer.Argument(
        ...,
        help=(
            "Path to an Allegro/Telesis third-party ASCII netlist, or a "
            "Capture/Allegro PST directory/file."
        ),
    ),
    bom_path: Path = typer.Argument(..., help="Path to a schematic-exported BOM file."),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output markdown path (default: reports/<netlist>-bom-intake-<YYYYMMDD>.md).",
    ),
    net_limit: int = typer.Option(
        8,
        "--net-limit",
        help="Maximum number of connected net names shown per component.",
    ),
    summary_only: bool = typer.Option(
        False,
        "--summary-only",
        help="Write only intake status, prefix summary, BOM groups, and mismatch sections.",
    ),
    mismatch_only: bool = typer.Option(
        False,
        "--mismatch-only",
        help="Write only intake status and BOM/design mismatch sections.",
    ),
    document_index: Path | None = typer.Option(
        None,
        "--document-index",
        help=(
            "Optional CSV/TSV index of public datasheet/document links. "
            "Adds BOM-item document match sections; no live supplier lookup."
        ),
    ),
    component_index_json: Path | None = typer.Option(
        None,
        "--component-index-json",
        help=(
            "Optional JSON output for UI/component-index prototypes. "
            "Contains registry-verified component rows plus BOM/document status."
        ),
    ),
) -> None:
    """Write a component-centric Allegro netlist + schematic BOM intake report."""
    from datetime import datetime, timezone

    from hardwise.bom import match_bom_to_design, parse_bom
    from hardwise.documents import match_documents_to_bom, parse_document_index
    from hardwise.report.allegro_bom_markdown import render

    if net_limit < 1:
        typer.echo("error: --net-limit must be >= 1", err=True)
        raise typer.Exit(1)
    if summary_only and mismatch_only:
        typer.echo("error: --summary-only and --mismatch-only cannot be used together", err=True)
        raise typer.Exit(1)
    if mismatch_only and document_index is not None:
        typer.echo("error: --document-index cannot be used with --mismatch-only", err=True)
        raise typer.Exit(1)

    try:
        design, source, input_type, _property_count = _load_allegro_design(netlist_path)
        bom = parse_bom(bom_path)
        report = match_bom_to_design(bom, design)
        document_report = (
            match_documents_to_bom(bom, parse_document_index(document_index))
            if document_index is not None
            else None
        )
    except Exception as e:
        typer.echo(f"error: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    now = datetime.now(timezone.utc)
    project_name = _report_source_name(source)
    project_meta = {
        "project_name": project_name,
        "generated_at": now.isoformat(timespec="seconds"),
        "netlist_source": str(source),
        "netlist_type": input_type,
    }
    report_text = render(
        design,
        bom,
        report,
        project_meta,
        net_limit=net_limit,
        summary_only=summary_only,
        mismatch_only=mismatch_only,
        document_report=document_report,
    )

    if output is None:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        output = reports_dir / f"{project_name}-bom-intake-{now.strftime('%Y%m%d')}.md"
    else:
        output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(report_text, encoding="utf-8")
    if component_index_json is not None:
        _write_component_index_json(
            component_index_json,
            design=design,
            report=report,
            project_meta=project_meta,
            document_report=document_report,
            net_limit=net_limit,
        )
    mismatch_count = _bom_report_mismatch_count(report)
    typer.echo(
        f"report: {output} "
        f"({len(report.matched_refdes)}/{report.design_refdes_count} matched, "
        f"{mismatch_count} mismatches)"
    )
    if component_index_json is not None:
        typer.echo(f"component-index: {component_index_json} ({len(design.components)} rows)")


@app.command(name="report-allegro-pin-profile")
def report_allegro_pin_profile(
    netlist_path: Path = typer.Argument(
        ...,
        help=(
            "Path to an Allegro/Telesis third-party ASCII netlist, or a "
            "Capture/Allegro PST directory/file."
        ),
    ),
    bom_path: Path = typer.Argument(..., help="Path to a schematic-exported BOM file."),
    refdes: str = typer.Option(..., "--refdes", help="Registry-verified component refdes."),
    profile_path: Path = typer.Option(
        ...,
        "--profile",
        help="DatasheetProfile JSON used for deterministic pin comparison.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output markdown path (default: reports/<netlist>-<refdes>-pin-profile-<YYYYMMDD>.md).",
    ),
) -> None:
    """Write one component's deterministic pin profile comparison report."""
    from datetime import datetime, timezone

    from hardwise.bom import match_bom_to_design, parse_bom
    from hardwise.ir.profile import DatasheetProfile
    from hardwise.report.pin_validation_markdown import compare_component_pins, render

    target_refdes = refdes.strip().upper()
    try:
        design, source, input_type, _property_count = _load_allegro_design(netlist_path)
        bom = parse_bom(bom_path)
        report = match_bom_to_design(bom, design)
        profile = DatasheetProfile.load(profile_path)
    except Exception as e:
        typer.echo(f"error: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    component = design.components.get(target_refdes)
    if component is None:
        typer.echo(f"error: unknown refdes {target_refdes!r} in design registry", err=True)
        raise typer.Exit(1)

    bom_row = report.rows_by_refdes.get(target_refdes)
    now = datetime.now(timezone.utc)
    project_name = _report_source_name(source)
    comparisons = compare_component_pins(
        component,
        profile,
        design_source_name=design.project_path.name,
    )
    project_meta = {
        "project_name": project_name,
        "generated_at": now.isoformat(timespec="seconds"),
        "netlist_source": str(source),
        "netlist_type": input_type,
        "profile_source": str(profile_path),
    }
    report_text = render(component, profile, comparisons, project_meta, bom_row=bom_row)

    if output is None:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        output = (
            reports_dir
            / f"{project_name}-{target_refdes}-pin-profile-{now.strftime('%Y%m%d')}.md"
        )
    else:
        output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(report_text, encoding="utf-8")
    counts = _pin_comparison_counts(comparisons)
    typer.echo(
        f"report: {output} ({target_refdes}, PASS={counts['PASS']}, "
        f"WARN={counts['WARN']}, ERROR={counts['ERROR']}, "
        f"manual_needed={counts['manual_needed']})"
    )


@app.command(name="validate-allegro-component")
def validate_allegro_component(
    netlist_path: Path = typer.Argument(
        ...,
        help=(
            "Path to an Allegro/Telesis third-party ASCII netlist, or a "
            "Capture/Allegro PST directory/file."
        ),
    ),
    bom_path: Path = typer.Argument(..., help="Path to a schematic-exported BOM file."),
    refdes: str = typer.Option(..., "--refdes", help="Registry-verified component refdes."),
    profile_path: Path = typer.Option(
        ...,
        "--profile",
        help="DatasheetProfile JSON used for deterministic component validation.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output markdown path (default: reports/<netlist>-<refdes>-validation-<YYYYMMDD>.md).",
    ),
) -> None:
    """Write one PCA9548A component's deterministic validation report."""
    from datetime import datetime, timezone

    from hardwise.bom import match_bom_to_design, parse_bom
    from hardwise.ir.profile import DatasheetProfile
    from hardwise.report.component_validation_markdown import count_checks, render
    from hardwise.validation.pca9548a import validate_pca9548a

    target_refdes = refdes.strip().upper()
    try:
        design, source, input_type, _property_count = _load_allegro_design(netlist_path)
        bom = parse_bom(bom_path)
        report = match_bom_to_design(bom, design)
        profile = DatasheetProfile.load(profile_path)
    except Exception as e:
        typer.echo(f"error: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    component = design.components.get(target_refdes)
    if component is None:
        typer.echo(f"error: unknown refdes {target_refdes!r} in design registry", err=True)
        raise typer.Exit(1)
    if profile.part_number.upper() != "PCA9548A":
        typer.echo(
            f"error: unsupported profile part {profile.part_number!r}; "
            "this MVP command supports PCA9548A only",
            err=True,
        )
        raise typer.Exit(1)

    bom_row = report.rows_by_refdes.get(target_refdes)
    bom_source_token = _component_index_bom_source(bom_row)
    now = datetime.now(timezone.utc)
    project_name = _report_source_name(source)
    checks = validate_pca9548a(
        component,
        profile,
        design_source_name=design.project_path.name,
        bom_source_token=bom_source_token,
    )
    project_meta = {
        "project_name": project_name,
        "generated_at": now.isoformat(timespec="seconds"),
        "netlist_source": str(source),
        "netlist_type": input_type,
        "profile_source": str(profile_path),
        "design_source_name": design.project_path.name,
    }
    report_text = render(component, profile, checks, project_meta, bom_row=bom_row)

    if output is None:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        output = reports_dir / f"{project_name}-{target_refdes}-validation-{now:%Y%m%d}.md"
    else:
        output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(report_text, encoding="utf-8")
    counts = count_checks(checks)
    typer.echo(
        f"report: {output} ({target_refdes}, PASS={counts['PASS']}, "
        f"WARN={counts['WARN']}, ERROR={counts['ERROR']}, "
        f"manual_needed={counts['manual_needed']})"
    )


@app.command(name="validate-allegro-project")
def validate_allegro_project(
    netlist_path: Path = typer.Argument(
        ...,
        help=(
            "Path to an Allegro/Telesis third-party ASCII netlist, or a "
            "Capture/Allegro PST directory/file."
        ),
    ),
    bom_path: Path = typer.Argument(..., help="Path to a schematic-exported BOM file."),
    profile_catalog: Path = typer.Option(
        Path("data/datasheet_profiles/profile_catalog.json"),
        "--profile-catalog",
        help="Explicit profile catalog mapping BOM identities to validators.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output markdown path (default: reports/<netlist>-validation-index-<YYYYMMDD>.md).",
    ),
    index_json: Path | None = typer.Option(
        None,
        "--index-json",
        help="Optional JSON sidecar for UI/component workspace prototypes.",
    ),
    detail_dir: Path | None = typer.Option(
        None,
        "--detail-dir",
        help="Optional directory for per-component validation detail reports.",
    ),
    manual_limit: int = typer.Option(
        50,
        "--manual-limit",
        help="Maximum manual/unsupported rows to show in markdown; JSON keeps all rows.",
    ),
    candidate_limit: int = typer.Option(
        30,
        "--candidate-limit",
        help="Maximum active no-profile candidate groups to show in markdown.",
    ),
) -> None:
    """Write a project-level deterministic validation index for supported profiles."""
    from datetime import datetime, timezone

    from hardwise.bom import match_bom_to_design, parse_bom
    from hardwise.ir.profile import DatasheetProfile
    from hardwise.report import component_validation_markdown
    from hardwise.report.validation_index_markdown import render, write_json
    from hardwise.validation.project_index import (
        build_project_validation_index,
        load_profile_catalog,
    )

    if manual_limit < 0:
        typer.echo("error: --manual-limit must be >= 0", err=True)
        raise typer.Exit(1)
    if candidate_limit < 0:
        typer.echo("error: --candidate-limit must be >= 0", err=True)
        raise typer.Exit(1)

    try:
        design, source, input_type, _property_count = _load_allegro_design(netlist_path)
        bom = parse_bom(bom_path)
        report = match_bom_to_design(bom, design)
        catalog = load_profile_catalog(profile_catalog)
    except Exception as e:
        typer.echo(f"error: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    now = datetime.now(timezone.utc)
    project_name = _report_source_name(source)
    index = build_project_validation_index(
        design=design,
        report=report,
        catalog=catalog,
        profile_catalog_path=profile_catalog,
        project_name=project_name,
        generated_at=now.isoformat(timespec="seconds"),
        netlist_source=str(source),
        netlist_type=input_type,
        detail_dir=detail_dir,
    )

    if detail_dir is not None:
        detail_dir.mkdir(parents=True, exist_ok=True)
        detail_meta_base = {
            "project_name": project_name,
            "generated_at": now.isoformat(timespec="seconds"),
            "netlist_source": str(source),
            "netlist_type": input_type,
            "design_source_name": design.project_path.name,
        }
        for row in index.validated_rows:
            if row.detail_report is None or row.profile_path is None:
                continue
            component = design.components[row.refdes]
            profile = DatasheetProfile.load(Path(row.profile_path))
            detail_meta = {**detail_meta_base, "profile_source": row.profile_path}
            detail_text = component_validation_markdown.render(
                component,
                profile,
                row.checks,
                detail_meta,
                bom_row=report.rows_by_refdes.get(row.refdes),
            )
            Path(row.detail_report).write_text(detail_text, encoding="utf-8")

    if output is None:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        output = reports_dir / f"{project_name}-validation-index-{now:%Y%m%d}.md"
    else:
        output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        render(index, manual_limit=manual_limit, candidate_limit=candidate_limit),
        encoding="utf-8",
    )
    if index_json is not None:
        write_json(index, index_json)

    totals = index.totals
    typer.echo(
        f"validation-index: {output} "
        f"({len(index.validated_rows)} validated, "
        f"PASS={totals['PASS']}, WARN={totals['WARN']}, "
        f"ERROR={totals['ERROR']}, manual_needed={totals['manual_needed']})"
    )
    if index_json is not None:
        typer.echo(f"validation-index-json: {index_json} ({len(index.rows)} rows)")
    if detail_dir is not None:
        typer.echo(f"validation-details: {detail_dir} ({len(index.validated_rows)} reports)")


@app.command(name="explain-component")
def explain_component(
    index_json: Path = typer.Argument(..., help="Path to a validation-index JSON sidecar."),
    refdes: str = typer.Argument(..., help="Registry-verified refdes to explain."),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional markdown output path. Defaults to stdout.",
    ),
) -> None:
    """Explain stored deterministic validation results for one component."""
    import json

    from hardwise.report.component_explain_markdown import render
    from hardwise.validation.project_index import ProjectValidationIndex

    try:
        payload = json.loads(index_json.read_text(encoding="utf-8"))
        index = ProjectValidationIndex.model_validate(payload)
    except Exception as e:
        typer.echo(f"error: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    rows = {row.refdes: row for row in index.rows}
    row = rows.get(refdes)
    if row is None:
        typer.echo(f"error: unknown refdes {refdes!r} in validation index", err=True)
        raise typer.Exit(1)

    text = render(index, row)
    if output is None:
        typer.echo(text)
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    typer.echo(f"explanation: {output} ({row.refdes}, status={row.status})")


@app.command()
def review(
    project_dir: Path = typer.Argument(..., help="Path to a KiCad project directory."),
    rules: str = typer.Option(
        "R001",
        "--rules",
        "-r",
        help="Comma-separated rule IDs to run (default: R001).",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output report path (default: reports/<project>-<YYYYMMDD>.<format>).",
    ),
    output_format: str = typer.Option(
        "md",
        "--format",
        "-f",
        help="Report format: md or html. Default: md.",
    ),
    report_style: str = typer.Option(
        "classic",
        "--report-style",
        help="Report style: classic or component. Component style is markdown-only in V2.3.",
    ),
    checklist: Path = typer.Option(
        Path("data/checklists/sch_review.yaml"),
        "--checklist",
        help="Path to the checklist yaml.",
    ),
    consolidate_flag: bool = typer.Option(
        True,
        "--consolidate/--no-consolidate",
        help="Run the Sleep Consolidator over the findings and append candidate rules.",
    ),
    memory_output: Path = typer.Option(
        Path("memory/rules.md"),
        "--memory-output",
        help="Path to the candidate-rule memory file (default: memory/rules.md).",
    ),
    db_path: str | None = typer.Option(
        None,
        "--db-path",
        help=(
            "SQLite DB path; populated with components + NC pins. "
            "Default: reports/<project>.db. Use empty string to skip. "
            "Override the whole backend by setting the HARDWISE_DB_URL "
            "env var to any SQLAlchemy URL (e.g. postgresql+psycopg2://...)."
        ),
    ),
    use_vector: bool = typer.Option(
        False,
        "--vector/--no-vector",
        help=(
            "Enable datasheet evidence chain for R003 (queries the local "
            "Chroma store for NC-pin hits, attaches evidence_chain + decision "
            "to findings). Off by default — turn on after `ingest-datasheet` "
            "has populated chunks for the relevant parts."
        ),
    ),
    persist_dir: Path = typer.Option(
        Path("data/chroma"),
        "--persist-dir",
        help="Chroma persistence directory (only used with --vector).",
    ),
    trace_output: Path | None = typer.Option(
        None,
        "--trace-output",
        help="JSONL run trace path (default: <report-dir>/trace.jsonl).",
    ),
    write_run_trace: bool = typer.Option(
        True,
        "--run-trace/--no-run-trace",
        help="Append a machine-readable review run record to trace.jsonl.",
    ),
) -> None:
    """Run a schematic review on a KiCad project and write a report."""
    from datetime import datetime, timezone

    from hardwise.adapters.kicad import parse_project
    from hardwise.checklist.checks import CHECK_SPECS
    from hardwise.checklist.finding import Finding
    from hardwise.checklist.loader import load_rules
    from hardwise.checklist.protocols import CheckContext, run_component_checks
    from hardwise.guards.evidence import strip_unsupported
    from hardwise.guards.refdes import sanitize_finding
    from hardwise.ir.build import build_design
    from hardwise.memory.consolidator import consolidate

    if output_format not in ("md", "html"):
        typer.echo(f"error: --format must be md|html, got {output_format!r}", err=True)
        raise typer.Exit(1)
    if report_style not in ("classic", "component"):
        typer.echo(
            f"error: --report-style must be classic|component, got {report_style!r}",
            err=True,
        )
        raise typer.Exit(1)
    if output_format == "html" and report_style == "component":
        typer.echo(
            "error: --report-style component is only supported with --format md in V2.3",
            err=True,
        )
        raise typer.Exit(1)

    requested_rules = [r.strip() for r in rules.split(",") if r.strip()]
    requested_ids = set(requested_rules)

    try:
        registry = parse_project(project_dir)
    except Exception as e:
        typer.echo(f"error: failed to parse {project_dir}: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    try:
        active_rules = load_rules(checklist)
    except Exception as e:
        typer.echo(
            f"error: failed to load checklist {checklist}: {type(e).__name__}: {e}", err=True
        )
        raise typer.Exit(1) from e

    collection = None
    if use_vector:
        from hardwise.store.vector import create_collection

        collection = create_collection(persist_dir)

    spec_by_id = {spec.rule_id: spec for spec in CHECK_SPECS}
    selected_specs = []
    for rule in active_rules:
        if rule.id not in requested_ids:
            continue
        spec = spec_by_id.get(rule.id)
        if spec is None:
            typer.echo(
                f"warning: rule {rule.id} active in yaml but no check function registered",
                err=True,
            )
            continue
        selected_specs.append(spec)

    design = build_design(registry)
    context = CheckContext(registry=registry, collection=collection)
    findings: list[Finding]
    findings, rules_run = run_component_checks(
        design=design,
        specs=selected_specs,
        requested_rule_ids=requested_ids,
        context=context,
    )

    if not rules_run:
        typer.echo(
            f"warning: no requested rules ({sorted(requested_ids)}) matched any active rule",
            err=True,
        )

    findings, dropped = strip_unsupported(findings)
    sanitized: list[Finding] = []
    total_wrapped = 0
    for f in findings:
        sf, w = sanitize_finding(f, registry)
        sanitized.append(sf)
        total_wrapped += w
    findings = sanitized

    now = datetime.now(timezone.utc)
    project_meta = {
        "project_name": project_dir.name,
        "project_dir": str(registry.project_dir),
        "components_reviewed": len(registry.components),
        "rules_run": rules_run,
        "generated_at": now.isoformat(timespec="seconds"),
        "unverified_refdes_wrapped": total_wrapped,
        "findings_dropped_no_evidence": dropped,
        "sanitize_note": (
            f"{total_wrapped} unverified refdes wrapped, {dropped} findings dropped (no evidence)"
        ),
    }

    if output_format == "html":
        from hardwise.report.html import render

        report_text = render(findings, project_meta)
    elif report_style == "component":
        from hardwise.report.component_markdown import render

        report_text = render(findings, project_meta, design)
    else:
        from hardwise.report.markdown import render

        report_text = render(findings, project_meta)

    if output is None:
        date_stamp = now.strftime("%Y%m%d")
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        output = reports_dir / f"{project_dir.name}-{date_stamp}.{output_format}"
    else:
        output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(report_text, encoding="utf-8")
    typer.echo(
        f"report: {output} ({len(findings)} findings, "
        f"{len(registry.components)} components reviewed)"
    )

    import os

    env_url = os.environ.get("HARDWISE_DB_URL", "").strip()
    store_trace: dict[str, object] = {"enabled": False}
    if env_url:
        from hardwise.store.relational import create_store, populate_from_registry

        session = create_store(env_url)
        try:
            n_comp, n_pin = populate_from_registry(session, registry)
        finally:
            session.close()
        store_trace = {
            "enabled": True,
            "target": env_url,
            "backend": "sqlalchemy_url",
            "components": n_comp,
            "nc_pins": n_pin,
        }
        typer.echo(f"store: {env_url} ({n_comp} components, {n_pin} NC pins)")
    else:
        resolved_db_path = _review_db_path(project_dir.name, db_path)
        if resolved_db_path is not None:
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            resolved_db_path.parent.mkdir(parents=True, exist_ok=True)
            from hardwise.store.relational import create_store, populate_from_registry

            if resolved_db_path.exists():
                resolved_db_path.unlink()
            session = create_store(resolved_db_path)
            try:
                n_comp, n_pin = populate_from_registry(session, registry)
            finally:
                session.close()
            store_trace = {
                "enabled": True,
                "target": str(resolved_db_path),
                "backend": "sqlite",
                "components": n_comp,
                "nc_pins": n_pin,
            }
            typer.echo(f"store: {resolved_db_path} ({n_comp} components, {n_pin} NC pins)")

    consolidator_trace: dict[str, object] = {"enabled": False}
    if consolidate_flag:
        candidates = consolidate(findings, project_dir.name, output_path=memory_output, now=now)
        consolidator_trace = {
            "enabled": True,
            "output_path": str(memory_output),
            "candidate_count": len(candidates),
        }
        if candidates:
            typer.echo(
                f"consolidator: {len(candidates)} candidate rule(s) appended to {memory_output}"
            )

    if write_run_trace:
        from hardwise.run_trace import ReviewRunSummary, append_jsonl, build_review_trace

        trace_path = trace_output or (output.parent / "trace.jsonl")
        summary = ReviewRunSummary(
            generated_at=project_meta["generated_at"],
            project_name=project_dir.name,
            project_dir=str(registry.project_dir),
            requested_rules=requested_rules,
            rules_run=rules_run,
            output_path=output,
            output_format=output_format,
            components_reviewed=len(registry.components),
            nc_pins_reviewed=len(registry.nc_pins),
            findings=findings,
            unverified_refdes_wrapped=total_wrapped,
            findings_dropped_no_evidence=dropped,
            vector_enabled=use_vector,
            store=store_trace,
            consolidator=consolidator_trace,
        )
        trace = build_review_trace(
            generated_at=summary.generated_at,
            project_name=summary.project_name,
            project_dir=summary.project_dir,
            requested_rules=summary.requested_rules,
            rules_run=summary.rules_run,
            output_path=summary.output_path,
            output_format=summary.output_format,
            components_reviewed=summary.components_reviewed,
            nc_pins_reviewed=summary.nc_pins_reviewed,
            findings=summary.findings,
            unverified_refdes_wrapped=summary.unverified_refdes_wrapped,
            findings_dropped_no_evidence=summary.findings_dropped_no_evidence,
            vector_enabled=summary.vector_enabled,
            store=summary.store,
            consolidator=summary.consolidator,
        )
        try:
            append_jsonl(trace_path, trace)
        except OSError as e:
            # The report is the primary artifact; trace is auxiliary run-history
            # data, so disk/permission failures warn without failing review.
            typer.echo(
                f"warning: failed to write run trace {trace_path}: {type(e).__name__}: {e}",
                err=True,
            )
        else:
            typer.echo(f"trace: {trace_path}")


@app.command(name="ingest-datasheet")
def ingest_datasheet(
    pdf_path: Path = typer.Argument(..., help="Path to a datasheet PDF."),
    part_ref: str = typer.Option(
        ..., "--part-ref", help="Refdes the datasheet belongs to (e.g. U3)."
    ),
    persist_dir: Path = typer.Option(
        Path("data/chroma"),
        "--persist-dir",
        help="Chroma persistence directory.",
    ),
    chunk_size: int = typer.Option(500, "--chunk-size"),
    overlap: int = typer.Option(100, "--overlap"),
    extract_profile: bool = typer.Option(
        False,
        "--extract-profile",
        help="Also extract a deterministic V2.4 DatasheetProfile JSON when supported.",
    ),
    profile_output_dir: Path = typer.Option(
        Path("data/datasheet_profiles"),
        "--profile-output-dir",
        help="Directory for extracted profile JSON files.",
    ),
) -> None:
    """Ingest a datasheet PDF into the local Chroma vector store."""
    from hardwise.ingest.pdf import extract_chunks
    from hardwise.store.vector import create_collection, ingest_chunks

    if not pdf_path.exists():
        typer.echo(f"error: pdf not found: {pdf_path}", err=True)
        raise typer.Exit(1)

    try:
        chunks = extract_chunks(pdf_path, chunk_size=chunk_size, overlap=overlap)
    except Exception as e:
        typer.echo(f"error: pdf extract failed: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    collection = create_collection(persist_dir)
    n = ingest_chunks(collection, chunks, part_ref=part_ref)
    typer.echo(f"ingest: {pdf_path.name} → {persist_dir} ({n} chunks, part_ref={part_ref})")
    if extract_profile:
        from hardwise.ir.profile import extract_l78_profile

        try:
            profile = extract_l78_profile(pdf_path)
        except Exception as e:
            typer.echo(
                f"warning: profile extraction skipped: {type(e).__name__}: {e}",
                err=True,
            )
        else:
            profile_path = profile_output_dir / f"{pdf_path.stem}.json"
            profile.save(profile_path)
            typer.echo(f"profile: {profile_path} (part={profile.part_number})")


@app.command(name="query-datasheet")
def query_datasheet(
    query: str = typer.Argument(..., help="Natural-language query."),
    top_k: int = typer.Option(5, "--top-k", "-k"),
    persist_dir: Path = typer.Option(
        Path("data/chroma"),
        "--persist-dir",
        help="Chroma persistence directory.",
    ),
) -> None:
    """Retrieve top-k datasheet chunks by semantic similarity (demo)."""
    from hardwise.store.vector import create_collection, query_chunks

    collection = create_collection(persist_dir)
    results = query_chunks(collection, query, top_k=top_k)
    if not results:
        typer.echo(f"no results for query: {query!r}")
        return
    for i, row in enumerate(results, start=1):
        meta = row["metadata"]
        snippet = row["text"].strip().replace("\n", " ")[:120]
        typer.echo(
            f"{i}. [{meta.get('source_pdf')} p{meta.get('page')} "
            f"part={meta.get('part_ref')}] {snippet}…"
        )


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
) -> None:
    """Run the public-corpus Hardwise Eval Pack MVP."""
    from hardwise.eval_pack import run_eval

    if accept_baseline and baseline is None:
        typer.echo("error: --accept-baseline requires --baseline", err=True)
        raise typer.Exit(1)

    try:
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
        f"eval: {summary.manifest_name} "
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


def _echo_decision_counts(counts: dict[str, int], total: int) -> None:
    typer.echo("decisions:")
    for decision in ("likely_issue", "reviewer_to_confirm", "likely_ok", "undecided"):
        count = int(counts.get(decision, 0))
        percentage = (count / total * 100) if total else 0.0
        typer.echo(f"  {decision}: {count} ({percentage:.1f}%)")


def _write_component_index_json(
    output: Path,
    *,
    design,
    report,
    project_meta: dict[str, object],
    document_report,
    net_limit: int,
) -> None:
    """Write registry-verified component rows for UI prototypes."""
    import json

    from hardwise.bom.types import sort_refdes_key

    rows = []
    duplicate_refdes = set(report.duplicate_bom_refdes)
    for component in sorted(design.components.values(), key=lambda c: sort_refdes_key(c.refdes)):
        bom_row = report.rows_by_refdes.get(component.refdes)
        document = _component_document_payload(bom_row, document_report)
        rows.append(
            {
                "refdes": component.refdes,
                "match_status": _component_index_match_status(
                    component.refdes,
                    report,
                    duplicate_refdes,
                ),
                "value": (bom_row.value if bom_row and bom_row.value else component.value) or "",
                "part_number": (
                    bom_row.part_number
                    if bom_row and bom_row.part_number
                    else component.part_number
                )
                or "",
                "manufacturer": (
                    bom_row.manufacturer
                    if bom_row and bom_row.manufacturer
                    else component.manufacturer
                )
                or "",
                "description": (bom_row.description if bom_row else None) or "",
                "package": component.package or "",
                "pin_count": len(component.pins),
                "nets": _component_index_nets(component, limit=net_limit),
                "bom_source": _component_index_bom_source(bom_row),
                "design_source": f"design:{design.project_path.name}#{component.refdes}",
                "document": document,
            }
        )

    payload = {
        "project": project_meta,
        "scope": "component identity and connectivity facts only",
        "counts": {
            "components": len(design.components),
            "nets": len(design.nets),
            "matched_refdes": len(report.matched_refdes),
            "bom_only_refdes": len(report.bom_only_refdes),
            "design_only_refdes": len(report.design_only_refdes),
            "duplicate_bom_refdes": len(report.duplicate_bom_refdes),
            "quantity_mismatches": len(report.quantity_mismatches),
        },
        "components": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _component_index_match_status(refdes: str, report, duplicate_refdes: set[str]) -> str:
    if refdes in duplicate_refdes:
        return "duplicate_bom"
    if refdes in report.design_only_refdes:
        return "design_only"
    if refdes in report.matched_refdes:
        return "matched"
    return "unknown"


def _component_index_nets(component, *, limit: int) -> list[str]:
    nets = sorted({pin.net for pin in component.pins if pin.net})
    return nets[:limit]


def _component_index_bom_source(row) -> str | None:
    if row is None:
        return None
    return f"bom:{row.source_file.name}#line{row.source_line}"


def _component_document_payload(row, document_report) -> dict[str, object]:
    if row is None or document_report is None or row.item_number is None:
        return {"status": "manual_needed", "reason": "No document index match for this row."}
    match = document_report.matches_by_item_key.get(row.item_number)
    if match is None:
        return {"status": "manual_needed", "reason": "No document match row for BOM item."}
    selected = match.selected
    return {
        "status": match.status,
        "identity": match.identity,
        "identity_kind": match.identity_kind,
        "reason": match.reason,
        "title": selected.title if selected else None,
        "url": selected.url if selected else None,
        "source_token": selected.source_token if selected else None,
    }


def _load_allegro_design(netlist_path: Path):
    """Load an Allegro schematic netlist/PST input into Design plus display metadata."""
    from hardwise.adapters.allegro_netlist import parse_allegro_netlist
    from hardwise.adapters.allegro_pst import is_allegro_pst_input, parse_allegro_pst
    from hardwise.ir.build import build_design_from_netlist, build_design_from_pst

    if is_allegro_pst_input(netlist_path):
        registry = parse_allegro_pst(netlist_path)
        design = build_design_from_pst(registry)
        source = registry.source_dir
        input_type = "Cadence Capture/Allegro PST schematic netlist topology"
        property_count = sum(len(part.properties) for part in registry.parts)
        return design, source, input_type, property_count

    registry = parse_allegro_netlist(netlist_path)
    design = build_design_from_netlist(registry)
    source = registry.source_file
    input_type = "Allegro/Telesis schematic netlist topology"
    property_count = len(registry.properties)
    return design, source, input_type, property_count


def _report_source_name(source: Path) -> str:
    """Return a stable report basename for a netlist source path."""
    return source.name if source.is_dir() else source.stem


def _bom_report_mismatch_count(report) -> int:
    """Count registry mismatch entries shown in the Allegro BOM intake status."""
    return (
        len(report.bom_only_refdes)
        + len(report.design_only_refdes)
        + len(report.duplicate_bom_refdes)
        + len(report.quantity_mismatches)
    )


def _pin_comparison_counts(comparisons) -> dict[str, int]:
    """Count pin comparison statuses for CLI summary output."""
    statuses = ("PASS", "WARN", "ERROR", "manual_needed")
    return {status: sum(row.status == status for row in comparisons) for status in statuses}


def _echo_refdes_sample(label: str, refdes_list: list[str], limit: int) -> None:
    """Print a compact mismatch sample for CLI smoke checks."""
    if not refdes_list:
        return
    sample = ", ".join(refdes_list[:limit])
    suffix = "" if len(refdes_list) <= limit else f" ... (+{len(refdes_list) - limit} more)"
    typer.echo(f"{label} sample: {sample}{suffix}")


def _review_db_path(project_name: str, db_path: str | None) -> Path | None:
    """Resolve review --db-path.

    ``None`` means use the default reports DB. Empty string means skip the
    SQLite store; Typer's Path coercion turns ``""`` into ``.`` too early,
    so keep this option as str and normalize it here.
    """
    if db_path is None:
        return Path("reports") / f"{project_name}.db"
    value = db_path.strip()
    if not value:
        return None
    return Path(value)


@app.command()
def ask(
    project_dir: Path = typer.Argument(..., help="Path to a KiCad project directory."),
    question: str = typer.Argument(..., help="Natural-language question about the project."),
    tier: str = typer.Option("normal", "--tier", "-t", help="Model tier: fast | normal | deep."),
    db_path: Path | None = typer.Option(
        None,
        "--db-path",
        help="SQLite DB path used during the run. Default: in-memory.",
    ),
    persist_dir: Path = typer.Option(
        Path("data/chroma"),
        "--persist-dir",
        help="Chroma persistence directory (only used with --vector).",
    ),
    use_vector: bool = typer.Option(
        False,
        "--vector/--no-vector",
        help="Enable search_datasheet against the local Chroma store. "
        "Off by default — turn on after `ingest-datasheet` has populated chunks.",
    ),
    max_iterations: int = typer.Option(
        10, "--max-iterations", help="Cap on tool-use loop iterations."
    ),
    show_trace: bool = typer.Option(
        True,
        "--trace/--no-trace",
        help="Print one line per tool call after the answer.",
    ),
) -> None:
    """Ask the agent a question about a KiCad project; runs the tool-use loop."""
    import os

    from anthropic import Anthropic
    from dotenv import load_dotenv

    from hardwise.adapters.kicad import parse_project
    from hardwise.agent.router import ModelRouter
    from hardwise.agent.runner import Runner
    from hardwise.store.relational import create_store, populate_from_registry

    load_dotenv(override=True)

    if tier not in ("fast", "normal", "deep"):
        typer.echo(f"error: tier must be fast|normal|deep, got {tier!r}", err=True)
        raise typer.Exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    if not api_key or api_key == "replace_me":
        typer.echo("error: ANTHROPIC_API_KEY missing or unset in .env", err=True)
        raise typer.Exit(1)

    try:
        registry = parse_project(project_dir)
    except Exception as e:
        typer.echo(f"error: failed to parse {project_dir}: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    db_path_str = ":memory:" if db_path is None else str(db_path)
    if db_path is not None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if db_path.exists():
            db_path.unlink()
    session = create_store(db_path_str)
    try:
        n_comp, n_pin = populate_from_registry(session, registry)
    except Exception as e:
        session.close()
        typer.echo(f"error: failed to populate store: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    collection = None
    if use_vector:
        from hardwise.store.vector import create_collection

        collection = create_collection(persist_dir)

    client = Anthropic(api_key=api_key, base_url=base_url)
    router = ModelRouter()
    runner = Runner(
        client=client,
        router=router,
        session=session,
        registry=registry,
        collection=collection,
        tier=tier,  # type: ignore[arg-type]
        max_iterations=max_iterations,
    )

    typer.echo(
        f"project: {project_dir.name} ({n_comp} components, {n_pin} NC pins) "
        f"tier={tier} model={router.select(tier)}"  # type: ignore[arg-type]
    )
    typer.echo(f"question: {question}")
    typer.echo("---")

    try:
        result = runner.run(question)
    finally:
        session.close()

    answer = result.text if result.text else "(no text returned)"
    trace_wrapped = sum(tc.wrapped for tc in result.tool_calls)
    total_wrapped = result.text_wrapped + trace_wrapped
    typer.echo(answer)
    typer.echo("---")
    typer.echo(
        f"iterations: {result.iterations} | "
        f"tool calls: {len(result.tool_calls)} | "
        f"tokens in/out: {result.input_tokens}/{result.output_tokens}"
        + (
            f" | cache create/read: {result.cache_creation_tokens}/{result.cache_read_tokens}"
            if result.cache_creation_tokens or result.cache_read_tokens
            else ""
        )
        + (f" | unverified refdes wrapped: {total_wrapped}" if total_wrapped else "")
        + (" | STOPPED AT CAP" if result.stopped_at_cap else "")
    )
    if show_trace and result.tool_calls:
        for i, tc in enumerate(result.tool_calls, start=1):
            typer.echo(f"  {i}. {tc.name}({tc.input}) → {tc.output_summary}")


if __name__ == "__main__":
    app()
