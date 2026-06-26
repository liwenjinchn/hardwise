"""Hardwise CLI entry point."""

from __future__ import annotations

import re
from pathlib import Path

import typer

from hardwise.cli_agent import register_agent_commands
from hardwise.cli_eval import register_eval_commands
from hardwise.cli_workbench import register_workbench_commands
from hardwise.path_display import display_path

app = typer.Typer(help="Hardwise — hardware R&D review Agent.")
register_agent_commands(app)
register_eval_commands(app)
register_workbench_commands(app)


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


@app.command(name="suggest-validation-targets")
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

        report_text = render(findings, project_meta, registry=registry)
    elif report_style == "component":
        from hardwise.report.component_markdown import render

        report_text = render(findings, project_meta, design, registry=registry)
    else:
        from hardwise.report.markdown import render

        report_text = render(findings, project_meta, registry=registry)

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


@app.command(name="extract-datasheet-html")
def extract_datasheet_html_cmd(
    source: str = typer.Argument(..., help="Local path or public HTTP(S) HTML datasheet page."),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output chunk JSONL path (default: reports/<source>-html-chunks.jsonl).",
    ),
    source_name: str | None = typer.Option(
        None,
        "--source-name",
        help="Evidence source name used in datasheet:<source>#p<N> tokens.",
    ),
    page: int | None = typer.Option(
        None,
        "--page",
        help="Override the 1-indexed datasheet page number.",
    ),
    part_ref: str | None = typer.Option(
        None,
        "--part-ref",
        help="Optional part identity/ref used to ingest chunks into Chroma.",
    ),
    persist_dir: Path = typer.Option(
        Path("data/chroma"),
        "--persist-dir",
        help="Chroma persistence directory, used only with --part-ref.",
    ),
    chunk_size: int = typer.Option(500, "--chunk-size"),
    overlap: int = typer.Option(100, "--overlap"),
) -> None:
    """Extract chunks from a public HTML datasheet fulltext page."""

    import json

    from hardwise.ingest.html import HtmlDatasheetExtractError, extract_html_chunks

    if page is not None and page < 1:
        typer.echo("error: --page must be >= 1", err=True)
        raise typer.Exit(1)
    if chunk_size < 1:
        typer.echo("error: --chunk-size must be >= 1", err=True)
        raise typer.Exit(1)
    if overlap < 0:
        typer.echo("error: --overlap must be >= 0", err=True)
        raise typer.Exit(1)

    try:
        chunks = extract_html_chunks(
            source,
            source_name=source_name,
            page=page,
            chunk_size=chunk_size,
            overlap=overlap,
        )
    except HtmlDatasheetExtractError as e:
        typer.echo(f"error: html extract failed: {e}", err=True)
        raise typer.Exit(1) from e
    except Exception as e:
        typer.echo(f"error: html extract failed: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    if output is None:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        output = reports_dir / f"{_safe_output_stem(source_name or source)}-html-chunks.jsonl"
    else:
        output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            row = chunk.model_dump(mode="json")
            row["evidence_token"] = chunk.evidence_token
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    ingested = 0
    if part_ref:
        from hardwise.store.vector import create_collection, ingest_chunks

        collection = create_collection(persist_dir)
        ingested = ingest_chunks(collection, chunks, part_ref=part_ref)

    typer.echo(
        f"html-datasheet-extract: {output} "
        f"(chunks={len(chunks)}, source={chunks[0].source_pdf if chunks else source_name or source}, "
        f"page={chunks[0].page if chunks else page or 'unknown'}, "
        f"ingested={ingested if part_ref else 'off'})"
    )


@app.command(name="report-pin-profile")
def report_pin_profile(
    profile_path: Path = typer.Argument(..., help="Path to a DatasheetProfile JSON file."),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output markdown path (default: reports/<profile>-pin-profile.md).",
    ),
) -> None:
    """Write a structured datasheet pin-profile report."""
    from hardwise.ir.profile import DatasheetProfile
    from hardwise.report.pin_profile_markdown import render

    try:
        profile = DatasheetProfile.load(profile_path)
    except Exception as e:
        typer.echo(f"error: profile load failed: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    if output is None:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        output = reports_dir / f"{profile_path.stem}-pin-profile.md"
    else:
        output.parent.mkdir(parents=True, exist_ok=True)

    report_text = render(profile, source_path=profile_path)
    output.write_text(report_text, encoding="utf-8")
    typer.echo(f"pin-profile: {output} ({len(profile.pins)} pins, part={profile.part_number})")


@app.command(name="report-pin-table")
def report_pin_table(
    pin_table_path: Path = typer.Argument(
        ...,
        help="Capture pin-table CSV from scripts/capture_pin_table_export.tcl.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output markdown path (default: reports/<csv>-pin-table.md).",
    ),
) -> None:
    """Run deterministic pin-table checks (R008/R009/R010)."""
    from hardwise.adapters.capture_pin_table import parse_pin_table
    from hardwise.checklist.checks.r008_floating_input import check as r008_check
    from hardwise.checklist.checks.r009_power_pin_unconnected import check as r009_check
    from hardwise.checklist.checks.r010_nc_marker_conflict import check as r010_check
    from hardwise.report.pin_table_markdown import render as render_pin_table

    try:
        records = parse_pin_table(pin_table_path)
    except Exception as e:
        typer.echo(f"error: pin-table parse failed: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    findings = r008_check(records) + r009_check(records) + r010_check(records)

    if output is None:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        output = reports_dir / f"{pin_table_path.stem}-pin-table.md"
    else:
        output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        render_pin_table(records, findings, source_path=pin_table_path),
        encoding="utf-8",
    )
    r008_n = sum(1 for f in findings if f.rule_id == "R008")
    r009_n = sum(1 for f in findings if f.rule_id == "R009")
    r010_n = sum(1 for f in findings if f.rule_id == "R010")
    typer.echo(
        f"pin-table: {output} ({len(records)} pins, R008={r008_n}, R009={r009_n}, R010={r010_n})"
    )


@app.command(name="store-datasheet-profile")
def store_datasheet_profile(
    profile_path: Path = typer.Argument(..., help="Path to a DatasheetProfile JSON file."),
    db_path: Path = typer.Option(
        ...,
        "--db-path",
        help="SQLite database path for the structured profile contract store.",
    ),
) -> None:
    """Store a structured datasheet profile contract in the relational store."""

    from hardwise.ir.profile import DatasheetProfile
    from hardwise.store.profile_contracts import (
        DatasheetProfileStoreError,
        get_datasheet_profile,
        upsert_datasheet_profile,
    )
    from hardwise.store.relational import create_store

    try:
        profile = DatasheetProfile.load(profile_path)
    except Exception as e:
        typer.echo(f"error: profile load failed: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    session = create_store(db_path)
    try:
        upsert_datasheet_profile(session, profile, source_path=profile_path)
        stored = get_datasheet_profile(session, profile.part_number)
    except DatasheetProfileStoreError as e:
        typer.echo(f"error: profile store failed: {e}", err=True)
        raise typer.Exit(1) from e
    except Exception as e:
        typer.echo(f"error: profile store failed: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e
    finally:
        session.close()

    if stored is None:
        typer.echo(f"error: stored profile not found: {profile.part_number}", err=True)
        raise typer.Exit(1)

    typer.echo(
        f"datasheet-profile-store: {display_path(db_path)} "
        f"(part={stored.part_number}, aliases={len(stored.part_number_aliases)}, "
        f"pins={len(stored.pins)}, status={stored.review_status})"
    )


@app.command(name="report-component-validation")
def report_component_validation(
    netlist_path: Path = typer.Argument(
        ...,
        help="Path to an Allegro/Telesis third-party ASCII netlist, or a Capture/Allegro PST input.",
    ),
    refdes: str = typer.Argument(..., help="Component refdes to validate."),
    profile_path: Path = typer.Argument(..., help="Path to a structured DatasheetProfile JSON."),
    bom_path: Path | None = typer.Option(
        None,
        "--bom",
        help="Optional schematic BOM used to attach component identity before validation.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output markdown path (default: reports/<refdes>-component-validation.md).",
    ),
) -> None:
    """Write a deterministic single-component pin validation report."""
    from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
    from hardwise.ir.profile import DatasheetProfile
    from hardwise.report.component_validation_markdown import render
    from hardwise.validation import validate_component_against_profile

    try:
        design, _source, _input_type, _property_count = _load_allegro_design(netlist_path)
        if bom_path is not None:
            bom = parse_bom(bom_path)
            design = apply_bom_to_design(design, match_bom_to_design(bom, design))
        component = design.components.get(refdes.upper())
        if component is None:
            typer.echo(f"error: refdes not found in design: {refdes}", err=True)
            raise typer.Exit(1)
        profile = DatasheetProfile.load(profile_path)
        validation_report = validate_component_against_profile(component, profile, design)
    except typer.Exit:
        raise
    except Exception as e:
        typer.echo(f"error: validation failed: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    if output is None:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        output = reports_dir / f"{component.refdes}-component-validation.md"
    else:
        output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        render(
            validation_report,
            profile_path=profile_path,
            profile=profile,
            component=component,
            design=design,
        ),
        encoding="utf-8",
    )
    counts = validation_report.counts_by_status
    typer.echo(
        f"component-validation: {output} "
        f"({validation_report.status}, "
        f"PASS/WARN/ERROR={counts['PASS']}/{counts['WARN']}/{counts['ERROR']})"
    )


@app.command(name="build-document-index-candidates")
def build_document_index_candidates(
    validation_index: Path = typer.Argument(
        ...,
        help="Project validation index JSON generated by design-validator-ui --index-json.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output CSV path (default: reports/<index-stem>-document-candidates.csv).",
    ),
    families: list[str] | None = typer.Option(
        None,
        "--family",
        help="Only include candidate rows for this suggested family; may be repeated.",
    ),
    datasheets_com: bool = typer.Option(
        False,
        "--datasheets-com",
        help="Classify rows with Datasheets.com lookup; exact single MPN PDF hits are approved.",
    ),
    limit: int = typer.Option(
        5,
        "--limit",
        help="Datasheets.com search result limit when --datasheets-com is enabled (1-10).",
    ),
    timeout_seconds: int = typer.Option(
        20,
        "--timeout",
        help="Datasheets.com HTTP timeout in seconds when --datasheets-com is enabled.",
    ),
) -> None:
    """Write reviewable document-index candidate rows from grouped coverage."""

    from hardwise.documents import (
        DocumentCandidateError,
        build_document_candidate_report,
        render_document_candidate_csv,
    )

    lookup = None
    if datasheets_com:
        import os

        from dotenv import load_dotenv

        from hardwise.documents.datasheets_com import (
            DATASHEETS_COM_API_KEY_ENV,
            DATASHEETS_COM_API_KEY_ENV_LEGACY,
            lookup_datasheets_com,
        )

        if limit < 1 or limit > 10:
            typer.echo("error: --limit must be between 1 and 10", err=True)
            raise typer.Exit(1)
        if timeout_seconds < 1:
            typer.echo("error: --timeout must be >= 1", err=True)
            raise typer.Exit(1)
        load_dotenv(override=True)
        api_key = os.environ.get(DATASHEETS_COM_API_KEY_ENV) or os.environ.get(
            DATASHEETS_COM_API_KEY_ENV_LEGACY
        )
        if api_key == "replace_me":
            api_key = None

        def lookup(query: str):
            return lookup_datasheets_com(
                query,
                api_key=api_key,
                limit=limit,
                timeout_seconds=timeout_seconds,
            )

    try:
        report = build_document_candidate_report(
            validation_index,
            families=families,
            datasheets_com_lookup=lookup,
        )
    except DocumentCandidateError as e:
        typer.echo(f"error: document candidate generation failed: {e}", err=True)
        raise typer.Exit(1) from e

    if output is None:
        output = Path("reports") / f"{validation_index.stem}-document-candidates.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_document_candidate_csv(report), encoding="utf-8")
    document_counts = {
        status: sum(row.document_status == status for row in report.candidates)
        for status in ("matched", "no_result", "ambiguous", "manual_needed")
    }
    approved = sum(row.review_status == "approved" for row in report.candidates)
    typer.echo(
        f"document-index-candidates: {output} "
        f"(groups={report.component_group_count}, candidates={len(report.candidates)}, "
        f"families={','.join(report.family_filter) if report.family_filter else 'all'}, "
        f"matched={document_counts['matched']}, "
        f"no_result={document_counts['no_result']}, "
        f"ambiguous={document_counts['ambiguous']}, "
        f"manual_needed={document_counts['manual_needed']}, "
        f"approved={approved}, "
        f"skipped_passive={report.skipped_passive}, "
        f"skipped_mechanical={report.skipped_mechanical}, "
        f"skipped_matched={report.skipped_matched_document}, "
        f"skipped_family_filter={report.skipped_family_filter})"
    )


@app.command(name="document-candidate-smoke")
def document_candidate_smoke(
    netlist_path: Path = typer.Argument(
        ...,
        help=(
            "Path to an Allegro/Telesis third-party ASCII netlist, or a "
            "Capture/Allegro PST input."
        ),
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
    baseline_document_index: Path | None = typer.Option(
        None,
        "--document-index",
        help=(
            "Optional reviewed document index used for the baseline workbench context. "
            "Candidate CSV output remains separate."
        ),
    ),
    candidate_csv: Path | None = typer.Option(
        None,
        "--candidate-csv",
        help=(
            "Output candidate CSV path "
            "(default: reports/<project>-document-candidate-smoke.csv)."
        ),
    ),
    summary_json: Path | None = typer.Option(
        None,
        "--summary-json",
        help=(
            "Output smoke summary JSON path "
            "(default: reports/<candidate-csv-stem>-summary.json)."
        ),
    ),
    families: list[str] | None = typer.Option(
        None,
        "--family",
        help="Only include candidate rows for this suggested family; may be repeated.",
    ),
    datasheets_com: bool = typer.Option(
        False,
        "--datasheets-com",
        help="Classify rows with Datasheets.com lookup; exact single MPN PDF hits are approved.",
    ),
    limit: int = typer.Option(
        5,
        "--limit",
        help="Datasheets.com search result limit when --datasheets-com is enabled (1-10).",
    ),
    timeout_seconds: int = typer.Option(
        20,
        "--timeout",
        help="Datasheets.com HTTP timeout in seconds when --datasheets-com is enabled.",
    ),
) -> None:
    """Run document-candidate generation plus workbench queue projection smoke."""

    from hardwise.documents import (
        run_document_candidate_smoke,
        write_document_candidate_smoke_summary,
    )

    lookup = None
    if datasheets_com:
        import os

        from dotenv import load_dotenv

        from hardwise.documents.datasheets_com import (
            DATASHEETS_COM_API_KEY_ENV,
            DATASHEETS_COM_API_KEY_ENV_LEGACY,
            lookup_datasheets_com,
        )

        if limit < 1 or limit > 10:
            typer.echo("error: --limit must be between 1 and 10", err=True)
            raise typer.Exit(1)
        if timeout_seconds < 1:
            typer.echo("error: --timeout must be >= 1", err=True)
            raise typer.Exit(1)
        load_dotenv(override=True)
        api_key = os.environ.get(DATASHEETS_COM_API_KEY_ENV) or os.environ.get(
            DATASHEETS_COM_API_KEY_ENV_LEGACY
        )
        if api_key == "replace_me":
            api_key = None

        def lookup(query: str):
            return lookup_datasheets_com(
                query,
                api_key=api_key,
                limit=limit,
                timeout_seconds=timeout_seconds,
            )

    try:
        summary = run_document_candidate_smoke(
            netlist_path=netlist_path,
            bom_path=bom_path,
            profiles=profiles,
            baseline_document_index=baseline_document_index,
            candidate_csv=candidate_csv,
            families=families,
            datasheets_com_lookup=lookup,
            datasheets_com_enabled=datasheets_com,
        )
    except Exception as e:
        typer.echo(f"error: document candidate smoke failed: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    if summary_json is None:
        candidate_path = Path(summary.candidate_csv)
        summary_json = candidate_path.with_name(f"{candidate_path.stem}-summary.json")
    write_document_candidate_smoke_summary(summary, summary_json)
    typer.echo(
        f"document-candidate-smoke: {summary_json} "
        f"(candidate_csv={summary.candidate_csv}, "
        f"candidates={summary.candidate_rows}, "
        f"approved={summary.candidate_approved}, "
        f"needs_review={summary.candidate_needs_review}, "
        f"rows_with_url={summary.candidate_rows_with_url}, "
        f"queue={summary.workbench_document_candidate_tasks}, "
        f"PASS/WARN/ERROR={summary.pass_count}/{summary.warn_count}/{summary.error_count}, "
        f"unchanged={summary.pass_warn_error_unchanged})"
    )


@app.command(name="fetch-approved-documents")
def fetch_approved_documents_cmd(
    document_index: Path = typer.Argument(
        ...,
        help="Reviewed document-index CSV/TSV with direct public PDF URLs.",
    ),
    cache_dir: Path = typer.Option(
        Path("data/datasheets/cache"),
        "--cache-dir",
        help="Directory for SHA-addressed cached PDFs.",
    ),
    metadata: Path | None = typer.Option(
        Path("data/datasheets/documents.jsonl"),
        "--metadata",
        help="Append JSONL provenance records here.",
    ),
    no_metadata: bool = typer.Option(
        False,
        "--no-metadata",
        help="Do not write provenance JSONL records.",
    ),
    timeout_seconds: int = typer.Option(
        20,
        "--timeout",
        help="Per-document HTTP timeout in seconds.",
    ),
) -> None:
    """Fetch reviewed public datasheet PDFs into the local document cache."""

    from hardwise.documents import fetch_approved_documents, parse_document_index

    if timeout_seconds < 1:
        typer.echo("error: --timeout must be >= 1", err=True)
        raise typer.Exit(1)
    resolved_metadata = None if no_metadata else metadata

    try:
        index = parse_document_index(document_index)
        report = fetch_approved_documents(
            index,
            cache_dir,
            metadata_path=resolved_metadata,
            timeout_seconds=timeout_seconds,
        )
    except Exception as e:
        typer.echo(f"error: document fetch failed: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    typer.echo(
        f"documents-fetch: {cache_dir} "
        f"(fetched={len(report.fetched)}, skipped={len(report.skipped)}, "
        f"metadata={display_path(resolved_metadata) if resolved_metadata else 'off'})"
    )
    for skipped in report.skipped[:5]:
        typer.echo(
            f"skip line {skipped.source_line}: {skipped.reason} ({skipped.title})",
            err=True,
        )


@app.command(name="search-datasheets-com")
def search_datasheets_com_cmd(
    query: str = typer.Argument(..., help="MPN or part search query."),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output reviewable document-index CSV path.",
    ),
    limit: int = typer.Option(
        5,
        "--limit",
        help="Maximum search results to request (1-10).",
    ),
    page: int = typer.Option(
        1,
        "--page",
        help="Search result page to request.",
    ),
    timeout_seconds: int = typer.Option(
        20,
        "--timeout",
        help="HTTP timeout in seconds.",
    ),
) -> None:
    """Search Datasheets.com and write candidate document-index rows."""

    import os

    from dotenv import load_dotenv

    from hardwise.documents.datasheets_com import (
        DATASHEETS_COM_API_KEY_ENV,
        DATASHEETS_COM_API_KEY_ENV_LEGACY,
        lookup_datasheets_com,
        render_datasheets_com_document_index_csv,
    )

    if limit < 1 or limit > 10:
        typer.echo("error: --limit must be between 1 and 10", err=True)
        raise typer.Exit(1)
    if page < 1:
        typer.echo("error: --page must be >= 1", err=True)
        raise typer.Exit(1)
    if timeout_seconds < 1:
        typer.echo("error: --timeout must be >= 1", err=True)
        raise typer.Exit(1)

    load_dotenv(override=True)
    api_key = os.environ.get(DATASHEETS_COM_API_KEY_ENV) or os.environ.get(
        DATASHEETS_COM_API_KEY_ENV_LEGACY
    )
    if api_key == "replace_me":
        api_key = None

    report = lookup_datasheets_com(
        query,
        api_key=api_key,
        limit=limit,
        page=page,
        timeout_seconds=timeout_seconds,
    )
    if report.status in {
        "not_configured",
        "rate_limited",
        "cloudflare_challenge",
        "provider_error",
    }:
        typer.echo(f"error: datasheets.com lookup failed: {report.status}", err=True)
        if report.reason:
            typer.echo(f"reason: {report.reason}", err=True)
        raise typer.Exit(1)

    if output is None:
        output = Path("reports") / f"{_safe_output_stem(query)}-datasheets-com-candidates.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_datasheets_com_document_index_csv(report), encoding="utf-8")

    remaining = report.rate_limits.remaining_month
    remaining_text = f", remaining_month={remaining}" if remaining is not None else ""
    typer.echo(
        f"datasheets-com-lookup: {output} "
        f"(status={report.status}, results={len(report.results)}, "
        f"direct_pdfs={report.direct_datasheet_count}{remaining_text})"
    )


@app.command(name="recommend-next-family")
def recommend_next_family(
    validation_index: Path = typer.Argument(
        ...,
        help="Project validation index JSON generated by design-validator-ui --index-json.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output Markdown path (default: reports/<index-stem>-next-family.md).",
    ),
) -> None:
    """Write advisory next-family recommendations from grouped coverage."""

    from hardwise.validation.coverage_priority import (
        CoveragePriorityError,
        build_family_coverage_report,
        render_family_coverage_markdown,
    )

    try:
        report = build_family_coverage_report(validation_index)
    except CoveragePriorityError as e:
        typer.echo(f"error: next-family recommendation failed: {e}", err=True)
        raise typer.Exit(1) from e

    if output is None:
        output = Path("reports") / f"{validation_index.stem}-next-family.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_family_coverage_markdown(report), encoding="utf-8")
    try_existing = sum(
        item.recommended_action == "try_existing_validator_profile"
        for item in report.recommendations
    )
    triage_new = sum(
        item.recommended_action == "triage_for_new_validator" for item in report.recommendations
    )
    typer.echo(
        f"next-family: {output} "
        f"(families={len(report.recommendations)}, "
        f"try_existing={try_existing}, triage_new={triage_new})"
    )


@app.command(name="draft-datasheet-profile")
def draft_datasheet_profile(
    validation_index: Path = typer.Argument(
        ...,
        help="Project validation index JSON generated by design-validator-ui --index-json.",
    ),
    identity: str = typer.Option(
        ...,
        "--identity",
        help="Component group identity to draft, e.g. PCA9548APW.",
    ),
    document_index: Path | None = typer.Option(
        None,
        "--document-index",
        help="Optional reviewed document index CSV/TSV used to select the public document.",
    ),
    archetype: str | None = typer.Option(
        None,
        "--archetype",
        help="Optional needs-review profile archetype id, e.g. 74x165_piso_16pin.",
    ),
    evidence_chunks: Path | None = typer.Option(
        None,
        "--evidence-chunks",
        help="Optional PDF/HTML chunk JSONL used to attach datasheet page evidence tokens.",
    ),
    output: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Output needs-review DatasheetProfile draft JSON path.",
    ),
) -> None:
    """Create a needs-review DatasheetProfile draft from grouped coverage."""

    from hardwise.ir.profile_draft import ProfileDraftError, draft_profile_from_project_index

    try:
        profile = draft_profile_from_project_index(
            validation_index,
            identity=identity,
            document_index_path=document_index,
            archetype_id=archetype,
            evidence_chunks_path=evidence_chunks,
        )
        profile.save(output)
    except ProfileDraftError as e:
        typer.echo(f"error: profile draft failed: {e}", err=True)
        raise typer.Exit(1) from e
    except Exception as e:
        typer.echo(f"error: profile draft failed: {type(e).__name__}: {e}", err=True)
        raise typer.Exit(1) from e

    typer.echo(
        f"profile-draft: {output} "
        f"(part_number={profile.part_number}, review_status={profile.review_status}"
        f"{', archetype=' + archetype if archetype else ''}"
        f"{', evidence_chunks=on' if evidence_chunks else ''})"
    )


@app.command(name="trust-dashboard")
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


if __name__ == "__main__":
    app()
