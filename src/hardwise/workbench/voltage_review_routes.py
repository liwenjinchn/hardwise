"""Local voltage confirmation with guarded, atomic run and catalog publication."""

from datetime import datetime, timezone
from pathlib import Path
import shutil
import sqlite3

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from hardwise.ir.voltage_review import VoltageReviewDocument
from hardwise.ir.voltage_review_actions import (
    VoltageReviewConflict,
    VoltageSelection,
    apply_voltage_selections,
    review_revision,
)
from hardwise.ir.voltage_review_projection import project_voltage_review, VoltageReviewScope
from hardwise.workbench.context import close_workbench_context
from hardwise.workbench.decision_fingerprints import review_project_key, review_fingerprints
from hardwise.workbench.decision_journal import ReviewConflictError
from hardwise.workbench.managed_projects import ManagedProjects
from hardwise.workbench.run_provenance import build_run_provenance
from hardwise.workbench.task_projection import build_review_tasks
from hardwise.workbench.voltage_review_stage import stage_voltage_review


class VoltageBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_project_id: str = Field(min_length=1)
    expected_run_id: str = Field(min_length=1)
    expected_revision: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer: str = Field(min_length=1, max_length=256)
    reason: str = Field(min_length=1, max_length=4000)
    selections: tuple[VoltageSelection, ...] = Field(min_length=1, max_length=1000)


class VoltageReviewResponse(BaseModel):
    project_id: str
    run_id: str
    revision: str
    editable: bool
    saved_project_id: str | None
    review: VoltageReviewDocument
    scopes: list[VoltageReviewScope]
    nets: list[str]


def review_for(context):
    return context.design.voltage_review or VoltageReviewDocument.from_legacy(
        context.design.voltage_facts
    )


def register_voltage_review_routes(app, *, journal, manager, lock, decisions, chat_service):
    store = ManagedProjects(Path(journal)) if journal else None

    def view(context):
        review = review_for(context)
        project = review_project_key(context)
        return dict(
            project_id=project,
            run_id=decisions.summary([], project=project).run_id,
            revision=review_revision(review),
            editable=store is not None,
            saved_project_id=context.managed_project_id,
            review=review.model_dump(mode="json"),
            scopes=[s.model_dump(mode="json") for s in project_voltage_review(review)[1]],
            nets=sorted(
                set(context.design.nets)
                | {pin.net for c in context.design.components.values() for pin in c.pins if pin.net}
            ),
        )

    @app.get("/api/workbench/voltage-review", response_model=VoltageReviewResponse)
    def voltage_review():
        with lock, manager.lease() as context:
            return view(context)

    @app.post("/api/workbench/voltage-review/confirm", response_model=VoltageReviewResponse)
    def confirm_voltage_review(request: VoltageBatchRequest):
        if store is None:
            raise HTTPException(400, "Voltage editing requires a local --review-db journal")
        with lock, manager.lease() as context:
            current = view(context)
            if (request.expected_project_id, request.expected_run_id) != (
                current["project_id"],
                current["run_id"],
            ):
                raise HTTPException(409, "Active project/run changed; reload before confirming")
            candidate, directory = None, None
            checkpoint = decisions.checkpoint()
            try:
                review = apply_voltage_selections(
                    review_for(context),
                    request.selections,
                    expected_revision=request.expected_revision,
                    reviewer=request.reviewer,
                    reason=request.reason,
                    recorded_at=datetime.now(timezone.utc),
                    known_nets=set(current["nets"]),
                )
                candidate, directory, prepared, previous = stage_voltage_review(
                    store, context, review
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

                manager.publish(candidate, import_dir=directory, commit=commit)
            except (ReviewConflictError, VoltageReviewConflict) as exc:
                decisions.restore_checkpoint(checkpoint)
                if candidate is not None:
                    close_workbench_context(candidate)
                if directory is not None:
                    shutil.rmtree(directory)
                raise HTTPException(409, str(exc)) from exc
            except (ValueError, OSError, sqlite3.Error, RuntimeError) as exc:
                decisions.restore_checkpoint(checkpoint)
                if candidate is not None:
                    close_workbench_context(candidate)
                if directory is not None:
                    shutil.rmtree(directory)
                raise HTTPException(
                    422, "Voltage batch was not published; reload and retry"
                ) from exc
            if hasattr(chat_service, "context"):
                chat_service.context = candidate
            return view(candidate)
