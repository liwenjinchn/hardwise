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
    db_path: Path | None = typer.Option(
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
    from hardwise.checklist.checks.r001_new_component_candidate import (
        check as check_r001,
    )
    from hardwise.checklist.checks.r002_cap_voltage_derating import (
        check as check_r002,
    )
    from hardwise.checklist.checks.r003_nc_pin_handling import (
        check as check_r003,
    )
    from hardwise.checklist.finding import Finding
    from hardwise.checklist.loader import load_rules
    from hardwise.guards.evidence import strip_unsupported
    from hardwise.guards.refdes import sanitize_finding
    from hardwise.memory.consolidator import consolidate

    if output_format not in ("md", "html"):
        typer.echo(f"error: --format must be md|html, got {output_format!r}", err=True)
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

    rule_dispatch = {
        "R001": lambda: check_r001(registry.schematic_records),
        "R002": lambda: check_r002(registry.schematic_records),
        "R003": lambda: check_r003(registry.nc_pins, registry=registry, collection=collection),
    }

    findings: list[Finding] = []
    rules_run: list[str] = []
    for rule in active_rules:
        if rule.id not in requested_ids:
            continue
        check_fn = rule_dispatch.get(rule.id)
        if check_fn is None:
            typer.echo(
                f"warning: rule {rule.id} active in yaml but no check function registered",
                err=True,
            )
            continue
        findings.extend(check_fn())
        rules_run.append(rule.id)

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
        if db_path is None:
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            db_path = reports_dir / f"{project_dir.name}.db"
        if str(db_path):
            from hardwise.store.relational import create_store, populate_from_registry

            db_path.parent.mkdir(parents=True, exist_ok=True)
            if db_path.exists():
                db_path.unlink()
            session = create_store(db_path)
            try:
                n_comp, n_pin = populate_from_registry(session, registry)
            finally:
                session.close()
            store_trace = {
                "enabled": True,
                "target": str(db_path),
                "backend": "sqlite",
                "components": n_comp,
                "nc_pins": n_pin,
            }
            typer.echo(f"store: {db_path} ({n_comp} components, {n_pin} NC pins)")

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
