"""Hardwise CLI entry point and command registrar."""

from __future__ import annotations

import typer

from hardwise.cli_agent import register_agent_commands
from hardwise.cli_analytics import register_commands as register_analytics_commands
from hardwise.cli_core import register_commands as register_core_commands
from hardwise.cli_datasheets import register_commands as register_datasheet_commands
from hardwise.cli_documents import register_commands as register_document_commands
from hardwise.cli_eval import register_eval_commands
from hardwise.cli_intake import register_commands as register_intake_commands
from hardwise.cli_reports import _review_db_path
from hardwise.cli_reports import register_commands as register_report_commands
from hardwise.cli_workbench import register_workbench_commands

app = typer.Typer(help="Hardwise — hardware R&D review Agent.")
register_agent_commands(app)
register_eval_commands(app)
register_workbench_commands(app)
register_core_commands(app)
register_intake_commands(app)
register_report_commands(app)
register_datasheet_commands(app)
register_document_commands(app)
register_analytics_commands(app)


@app.callback()
def _root() -> None:
    """Force Typer to treat this as a multi-command app."""


__all__ = ["_review_db_path", "app"]


if __name__ == "__main__":
    app()
