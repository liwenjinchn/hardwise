"""Datasheet ingest, query, and validation report commands."""

from __future__ import annotations

from pathlib import Path

import typer

from hardwise.path_display import display_path
from hardwise.cli_documents import _safe_output_stem
from hardwise.cli_intake import _load_allegro_design

commands = typer.Typer()


@commands.command(name="ingest-datasheet")
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


@commands.command(name="query-datasheet")
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


@commands.command(name="extract-datasheet-html")
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


@commands.command(name="report-pin-profile")
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


@commands.command(name="report-pin-table")
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


@commands.command(name="report-review-package")
def report_review_package(
    manifest_path: Path = typer.Argument(
        ...,
        help="YAML/JSON review-package manifest for schematic PDF, ERC/DRC, checklist, and notes.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output markdown path (default: reports/<manifest>-review-package.md).",
    ),
) -> None:
    """Summarize exported review-package evidence without parsing it into findings."""
    from hardwise.review_package import (
        ReviewPackageParseError,
        load_review_package_manifest,
        render_review_package_markdown,
    )

    try:
        report = load_review_package_manifest(manifest_path)
    except ReviewPackageParseError as e:
        typer.echo(f"error: review-package manifest failed: {e}", err=True)
        raise typer.Exit(1) from e

    if output is None:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        output = reports_dir / f"{manifest_path.stem}-review-package.md"
    else:
        output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(render_review_package_markdown(report), encoding="utf-8")
    counts = report.counts
    typer.echo(
        f"review-package: {output} "
        f"(package_status={report.package_status}, status_group={report.status_group}, "
        f"manual_gaps={report.manual_gap_count}, "
        f"present={counts['present']}, missing_required={counts['missing_required']}, "
        f"missing_optional={counts['missing_optional']}, hash_mismatch={counts['hash_mismatch']})"
    )


@commands.command(name="store-datasheet-profile")
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


@commands.command(name="report-component-validation")
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


def register_commands(app: typer.Typer) -> None:
    """Register this command group on the root CLI app."""
    app.registered_commands.extend(commands.registered_commands)
