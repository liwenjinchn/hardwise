"""EDA intake and inspection CLI commands."""

from __future__ import annotations

import re
from pathlib import Path

import typer

commands = typer.Typer()


@commands.command(name="inspect-kicad")
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
    schematic_net: bool = typer.Option(
        False,
        "--schematic-net",
        help=(
            "Print explicit .kicad_sch net names from labels and power symbols. "
            "This is pre-Layout naming evidence only; it does not infer wire fanout."
        ),
    ),
    check_net_names: bool = typer.Option(
        False,
        "--check-net-names",
        help=(
            "With --schematic-net, run the shared NamingPolicy over schematic-side "
            "net names and print WARN findings."
        ),
    ),
    naming_policy: Path | None = typer.Option(
        None,
        "--naming-policy",
        help=(
            "Optional YAML NamingPolicy for --schematic-net --check-net-names. "
            "Defaults to the public permissive policy."
        ),
    ),
) -> None:
    """Parse a KiCad project and print the initial refdes registry."""
    from hardwise.adapters.kicad import parse_project, pcb_signal_nets
    from hardwise.ir.types import Design, Net
    from hardwise.validation.net_naming import load_naming_policy, validate_net_naming

    try:
        registry = parse_project(project_dir)
    except Exception as e:
        typer.echo(f"error: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e
    if show_nets and schematic_net:
        typer.echo("error: --net and --schematic-net are mutually exclusive", err=True)
        raise typer.Exit(1)
    if check_net_names and not schematic_net:
        typer.echo("error: --check-net-names requires --schematic-net", err=True)
        raise typer.Exit(1)
    if naming_policy is not None and not check_net_names:
        typer.echo("error: --naming-policy requires --schematic-net --check-net-names", err=True)
        raise typer.Exit(1)

    typer.echo(f"project: {registry.project_dir}")
    typer.echo(f"components: {len(registry.components)}")
    if schematic_net:
        typer.echo(f"schematic named nets: {len(registry.schematic_nets)}")
        typer.echo("source: .kicad_sch labels/power symbols (pre-Layout naming evidence)")
        typer.echo(
            "scope: net names only; no wire fanout, pin endpoints, .kicad_pcb, or PCB geometry"
        )
        if check_net_names:
            try:
                policy = load_naming_policy(naming_policy) if naming_policy is not None else None
            except Exception as e:
                typer.echo(f"error: {type(e).__name__}: {e}", err=True)
                raise typer.Exit(1) from e
            names_by_file: dict[Path, set[str]] = {}
            for record in registry.schematic_nets:
                names_by_file.setdefault(record.source_file, set()).add(record.name)
            checks = []
            for source_file, names in sorted(names_by_file.items(), key=lambda item: item[0].name):
                design = Design(
                    components={},
                    nets={name: Net(name=name) for name in names},
                    project_path=registry.project_dir,
                    source_eda="kicad",
                )
                checks.extend(
                    validate_net_naming(
                        design,
                        policy=policy,
                        source_label=source_file.name,
                    )
                )
            typer.echo(f"naming checks: {len(checks)} warning(s)")
            for check in checks[:limit]:
                evidence = ", ".join(check.evidence) if check.evidence else "-"
                typer.echo(f"{check.net_name:32} {check.check:28} {check.status:5} {evidence}")
            return
        typer.echo("")
        for record in registry.schematic_nets[:limit]:
            typer.echo(f"{record.name:32} {record.source_kind:18} {record.source_file.name}")
        return
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


@commands.command(name="inspect-allegro-netlist")
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


@commands.command(name="inspect-bom-match")
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
    typer.echo(f"bom_rows_matched: {len(report.matched_refdes)}")
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


@commands.command(name="report-allegro-bom")
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
    mismatch_count = _bom_report_mismatch_count(report)
    typer.echo(
        f"report: {output} "
        f"(bom_rows_matched={len(report.matched_refdes)}/{report.design_refdes_count}, "
        f"{mismatch_count} mismatches)"
    )


@commands.command(name="suggest-validation-targets")
def suggest_validation_targets(
    bom_path: Path = typer.Argument(..., help="Path to a schematic-exported BOM file."),
    profiles: Path = typer.Option(
        Path("data/datasheet_profiles"),
        "--profiles",
        help="Directory containing structured DatasheetProfile JSON files.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output YAML path (default: reports/<bom-stem>-target-candidates.yaml).",
    ),
    matched_only: bool = typer.Option(
        False,
        "--matched-only",
        help="Write only matched targets in the V3.5 manifest shape.",
    ),
) -> None:
    """Suggest explicit refdes-to-profile validation targets from a schematic BOM."""
    from hardwise.bom import parse_bom
    from hardwise.validation import (
        ProfileCandidateError,
        render_profile_candidate_manifest,
        suggest_profile_candidates,
    )

    try:
        bom = parse_bom(bom_path)
        report = suggest_profile_candidates(bom, profiles, project=bom_path.stem)
    except ProfileCandidateError as e:
        typer.echo(f"error: profile candidate generation failed: {e}", err=True)
        raise typer.Exit(1) from e
    except Exception as e:
        typer.echo(f"error: suggest validation targets failed: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    if output is None:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        output = reports_dir / f"{bom_path.stem}-target-candidates.yaml"
    else:
        output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        render_profile_candidate_manifest(report, matched_only=matched_only),
        encoding="utf-8",
    )
    counts = report.counts_by_status
    typer.echo(
        f"target-candidates: {output} "
        f"(profile_targets_matched={counts['matched']}, no_result={counts['no_result']}, "
        f"ambiguous={counts['ambiguous']}, manual_needed={counts['manual_needed']})"
    )


def _load_allegro_design(netlist_path: Path):
    """Load an Allegro schematic netlist/PST input into Design plus display metadata."""
    from hardwise.workbench.context import load_allegro_design

    return load_allegro_design(netlist_path)


def _report_source_name(source: Path) -> str:
    """Return a stable report basename for a netlist source path."""
    return source.name if source.is_dir() else source.stem


def _safe_output_stem(value: str) -> str:
    """Return a conservative filesystem stem for generated report paths."""

    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return stem.lower() or "datasheets-com"


def _bom_report_mismatch_count(report) -> int:
    """Count registry mismatch entries shown in the Allegro BOM intake status."""
    return (
        len(report.bom_only_refdes)
        + len(report.design_only_refdes)
        + len(report.duplicate_bom_refdes)
        + len(report.quantity_mismatches)
    )


def _echo_refdes_sample(label: str, refdes_list: list[str], limit: int) -> None:
    """Print a compact mismatch sample for CLI smoke checks."""
    if not refdes_list:
        return
    sample = ", ".join(refdes_list[:limit])
    suffix = "" if len(refdes_list) <= limit else f" ... (+{len(refdes_list) - limit} more)"
    typer.echo(f"{label} sample: {sample}{suffix}")


def register_commands(app: typer.Typer) -> None:
    """Register this command group on the root CLI app."""
    app.registered_commands.extend(commands.registered_commands)
