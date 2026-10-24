"""Local saved-project endpoints; source and active context failures stay isolated."""

import shutil
import sqlite3

from fastapi import HTTPException, Query

from hardwise.workbench.context import close_workbench_context
from hardwise.workbench.decision_fingerprints import review_project_key
from hardwise.workbench.decision_journal import ReviewConflictError
from hardwise.workbench.managed_projects import ManagedProjects, ManagedProjectMissing
from hardwise.workbench.managed_project_contracts import SavedProjectView, SavedProjectCatalog


def register_managed_project_routes(
    app, *, journal, manager, lock, decisions, start_run, state_for, chat_service
):
    projects = ManagedProjects(journal) if journal else None

    def require_store():
        if projects is None:
            raise HTTPException(400, "Project save/open requires a local --review-db journal")
        return projects

    def require_current(context, expected_run_id):
        summary = decisions.summary([], project=review_project_key(context))
        if summary.run_id != expected_run_id:
            raise HTTPException(409, "Active review changed; refresh before saving or opening")

    @app.get("/api/workbench/projects", response_model=SavedProjectCatalog)
    def list_projects():
        try:
            return dict(projects=require_store().list())
        except (sqlite3.Error, OSError, ValueError) as exc:
            raise HTTPException(503, "Saved project catalog is unavailable") from exc

    @app.post("/api/workbench/projects/save", response_model=SavedProjectView)
    def save_project(expected_run_id: str = Query(..., min_length=1)):
        store = require_store()
        with lock, manager.lease() as context:
            require_current(context, expected_run_id)
            try:
                return store.save(context, expected_run_id)
            except ReviewConflictError as exc:
                raise HTTPException(409, str(exc)) from exc
            except (OSError, ValueError, sqlite3.Error) as exc:
                raise HTTPException(422, f"Project was not saved: {exc}") from exc

    @app.post("/api/workbench/projects/{identifier}/open")
    def open_project(identifier: str, expected_run_id: str = Query(..., min_length=1)):
        store = require_store()
        with lock, manager.lease() as current:
            require_current(current, expected_run_id)
            try:
                candidate, directory = store.open(identifier)
            except ManagedProjectMissing as exc:
                raise HTTPException(404, "Unknown saved project") from exc
            except (OSError, ValueError, sqlite3.Error) as exc:
                raise HTTPException(422, f"Saved project could not be opened: {exc}") from exc
            checkpoint = decisions.checkpoint()
            try:
                start_run(candidate)
                manager.swap(candidate, import_dir=directory)
            except Exception as exc:
                decisions.restore_checkpoint(checkpoint)
                close_workbench_context(candidate)
                shutil.rmtree(directory)
                raise HTTPException(503, "Saved project activation failed") from exc
            if hasattr(chat_service, "context"):
                chat_service.context = candidate
            return state_for(candidate)
