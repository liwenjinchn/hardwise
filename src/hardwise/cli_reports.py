"""Project review CLI command."""

from __future__ import annotations

from pathlib import Path

import typer

commands = typer.Typer()


@commands.command()
def review(
    project_dir: Path = typer.Argument(
        ...,
        help=(
            "Path to a KiCad appendix/regression project directory. "
            "The product workbench path is exported Allegro/PST + BOM."
        ),
    ),
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
    """Run the KiCad appendix schematic-review path and write a report."""
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


def register_commands(app: typer.Typer) -> None:
    """Register this command group on the root CLI app."""
    app.registered_commands.extend(commands.registered_commands)
