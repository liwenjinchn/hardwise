"""Own startup sources for the entire local server lifetime."""

from contextlib import contextmanager
from pathlib import Path
import shutil

from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.managed_projects import ManagedProjects


@contextmanager
def startup_context(*, netlist_path, bom_path, review_db, open_project, **inputs):
    directory = None
    context = None
    try:
        if open_project:
            if (
                netlist_path is not None
                or bom_path is not None
                or any(v is not None for v in inputs.values())
            ):
                raise ValueError(
                    "--open-project cannot be combined with source inputs or --profiles"
                )
            if review_db is None or not review_db.is_file():
                raise ValueError("--open-project requires an existing --review-db journal")
            context, directory = ManagedProjects(review_db).open(open_project)
        else:
            if netlist_path is None:
                raise ValueError(
                    "Provide a netlist/PST path or use --open-project with --review-db"
                )
            inputs["profiles"] = inputs.get("profiles") or Path("data/datasheet_profiles")
            context = build_workbench_context(
                netlist_path=netlist_path, bom_path=bom_path, **inputs
            )
        yield context
    finally:
        if context is not None:
            close_workbench_context(context)
        if directory is not None:
            shutil.rmtree(directory)
