"""Core CLI commands."""

from __future__ import annotations

import typer

commands = typer.Typer()


@commands.command()
def hello() -> None:
    """Sanity check that the install worked."""
    typer.echo("hardwise installed.")


@commands.command(name="verify-api")
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


def register_commands(app: typer.Typer) -> None:
    """Register this command group on the root CLI app."""
    app.registered_commands.extend(commands.registered_commands)
