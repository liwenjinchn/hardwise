"""Complete saved-project backup/restore commands for local users."""

import json
from pathlib import Path
import typer


def register_project_backup_commands(app):
    @app.command("backup-projects")
    def backup(
        review_db: Path = typer.Option(..., "--review-db"),
        output: Path = typer.Option(..., "--output"),
    ):
        """Back up saved inputs and one consistent journal, without overwriting a file."""
        from hardwise.workbench.project_backup import backup_projects

        try:
            result = backup_projects(review_db, output)
        except Exception as exc:
            typer.echo(f"error: backup failed: {exc}", err=True)
            raise typer.Exit(1) from exc
        typer.echo(json.dumps(result, ensure_ascii=False))

    @app.command("restore-projects")
    def restore(
        archive: Path = typer.Argument(...), destination: Path = typer.Option(..., "--destination")
    ):
        """Validate and restore a complete backup to a new directory."""
        from hardwise.workbench.project_backup import restore_projects

        try:
            result = restore_projects(archive, destination)
        except Exception as exc:
            typer.echo(f"error: restore failed: {exc}", err=True)
            raise typer.Exit(1) from exc
        typer.echo(json.dumps(result, ensure_ascii=False))
