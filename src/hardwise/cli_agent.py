"""Agent-facing CLI commands."""

from __future__ import annotations

from pathlib import Path

import typer


def register_agent_commands(app: typer.Typer) -> None:
    """Register agent commands on the root CLI app."""

    @app.command()
    def ask(
        project_dir: Path = typer.Argument(..., help="Path to a KiCad project directory."),
        question: str = typer.Argument(..., help="Natural-language question about the project."),
        tier: str = typer.Option(
            "normal", "--tier", "-t", help="Model tier: fast | normal | deep."
        ),
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
            help=(
                "Enable search_datasheet against the local Chroma store. "
                "Off by default — turn on after `ingest-datasheet` has populated chunks."
            ),
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
            typer.echo(
                f"error: failed to parse {project_dir}: {type(e).__name__}: {e}",
                err=True,
            )
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
