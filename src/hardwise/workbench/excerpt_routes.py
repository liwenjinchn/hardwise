"""Local human excerpt editing with atomic run/catalog publication."""

from datetime import datetime, timezone
from pathlib import Path
import shutil
import sqlite3

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from hardwise.ir.excerpt_edits import ExcerptEdit, apply_excerpt_edit
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.excerpt_sharing import sharing_status
from hardwise.ir.profile_review import profile_values, Lifecycle
from hardwise.workbench.context import close_workbench_context
from hardwise.workbench.decision_fingerprints import review_project_key, review_fingerprints
from hardwise.workbench.decision_journal import ReviewConflictError
from hardwise.workbench.excerpt_stage import profile_files, profiles_revision, stage_excerpt
from hardwise.workbench.managed_projects import ManagedProjects
from hardwise.workbench.run_provenance import build_run_provenance
from hardwise.workbench.task_projection import build_review_tasks


class ExcerptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_project_id: str = Field(min_length=1)
    expected_run_id: str = Field(min_length=1)
    expected_revision: str = Field(pattern=r"^[0-9a-f]{64}$")
    profile_name: str = Field(min_length=1, max_length=256)
    edit: ExcerptEdit


class ExcerptProfileView(BaseModel):
    name: str
    lifecycle: Lifecycle
    profile: DatasheetProfile
    values: dict[str, object]
    sharing_states: dict[str, str]


class ExcerptResponse(BaseModel):
    project_id: str
    run_id: str
    revision: str
    editable: bool
    saved_project_id: str | None
    profiles: list[ExcerptProfileView]


def register_excerpt_routes(app, *, journal, manager, lock, decisions, chat_service):
    store = ManagedProjects(Path(journal)) if journal else None

    def view(context):
        profiles = profile_files(context)
        return dict(
            project_id=review_project_key(context),
            run_id=decisions.summary([], project=review_project_key(context)).run_id,
            revision=profiles_revision(profiles),
            editable=store is not None,
            saved_project_id=context.managed_project_id,
            profiles=[
                dict(
                    name=name,
                    lifecycle=p.lifecycle,
                    profile=p.model_dump(mode="json"),
                    values=profile_values(p),
                    sharing_states={
                        f.pointer: sharing_status(f.source) for f in p.field_review.fields
                    }
                    if p.field_review
                    else {},
                )
                for name, (_, p) in profiles.items()
            ],
        )

    @app.get("/api/workbench/excerpts", response_model=ExcerptResponse)
    def get_excerpts():
        with lock, manager.lease() as context:
            try:
                return view(context)
            except (OSError, ValueError) as exc:
                raise HTTPException(409, "Sources changed; reload before editing") from exc

    @app.post("/api/workbench/excerpts", response_model=ExcerptResponse)
    def save_excerpt(request: ExcerptRequest):
        if store is None:
            raise HTTPException(400, "Excerpt editing requires a local --review-db journal")
        with lock, manager.lease() as context:
            try:
                current = view(context)
                profiles = profile_files(context)
            except (OSError, ValueError) as exc:
                raise HTTPException(409, "Sources changed; reload before editing") from exc
            if (
                request.expected_project_id,
                request.expected_run_id,
                request.expected_revision,
            ) != (current["project_id"], current["run_id"], current["revision"]):
                raise HTTPException(
                    409, "Active project/run/source changed; preserve draft and reload"
                )
            if request.profile_name not in profiles:
                raise HTTPException(422, "Select a captured profile")
            candidate, directory = None, None
            checkpoint = decisions.checkpoint()
            try:
                updated = apply_excerpt_edit(
                    profiles[request.profile_name][1],
                    request.edit,
                    recorded_at=datetime.now(timezone.utc),
                )
                candidate, directory, prepared, previous = stage_excerpt(
                    store, context, request.profile_name, updated
                )
                tasks = build_review_tasks(candidate)
                fingerprints = review_fingerprints(candidate, tasks)
                publication = {}

                def catalog_write(db, run_id):
                    publication.update(
                        store.publish(db, candidate, prepared, retained_snapshots=(previous,))
                    )

                def commit():
                    decisions.begin_run(
                        current["project_id"],
                        fingerprints,
                        tasks=[task.model_dump(mode="json") for task in tasks],
                        provenance=build_run_provenance(candidate).model_dump(mode="json"),
                        extra_write=catalog_write,
                    )
                    candidate.managed_project_id = publication["id"]

                # Compute the response before committing: a later read failure must not
                # report an already-published mutation as unsuccessful.
                result = view(candidate)
                manager.publish(candidate, import_dir=directory, commit=commit)
            except (ValueError, OSError, sqlite3.Error, RuntimeError, ReviewConflictError) as exc:
                decisions.restore_checkpoint(checkpoint)
                if candidate is not None:
                    close_workbench_context(candidate)
                if directory is not None:
                    shutil.rmtree(directory)
                code = 409 if isinstance(exc, ReviewConflictError) else 422
                raise HTTPException(
                    code, "Excerpt was not published; preserve draft and reload"
                ) from exc
            if hasattr(chat_service, "context"):
                chat_service.context = candidate
            result["run_id"] = decisions.summary([], project=current["project_id"]).run_id
            result["saved_project_id"] = candidate.managed_project_id
            return result
