"""Workbench-related CLI command registration."""

from __future__ import annotations

import typer

from hardwise.cli_design_validator import register_design_validator_commands
from hardwise.cli_validator_ui import register_validator_ui_commands
from hardwise.cli_workbench_server import register_workbench_server_commands


def register_workbench_commands(app: typer.Typer) -> None:
    """Register workbench and validator commands on the root CLI app."""

    register_validator_ui_commands(app)
    register_design_validator_commands(app)
    register_workbench_server_commands(app)
