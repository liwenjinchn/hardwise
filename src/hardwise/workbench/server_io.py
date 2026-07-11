"""Upload and export helpers for the local workbench server."""

from __future__ import annotations

import csv
import io
import shutil
from pathlib import Path

from fastapi import UploadFile
from fastapi.responses import Response

from hardwise.csv_safety import csv_safe_cell
from hardwise.workbench.context import WorkbenchContext
from hardwise.workbench.view_model import ReviewTask, build_review_tasks


def _save_upload(upload: UploadFile, directory: Path, *, fallback_name: str) -> Path:
    safe_name = Path(upload.filename or fallback_name).name or fallback_name
    target = directory / safe_name
    upload.file.seek(0)
    with target.open("wb") as handle:
        shutil.copyfileobj(upload.file, handle)
    return target


def _task_csv_response(
    context: WorkbenchContext,
    *,
    tasks: list[ReviewTask] | None = None,
) -> Response:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "id",
            "refdes",
            "status_group",
            "trust_tier",
            "title",
            "recommended_action",
            "source_classes",
            "review_status",
            "review_reason",
            "review_updated_at",
            "derived_from_task_id",
            "signoff_evidence_ready",
            "missing_local_sources",
        ],
    )
    writer.writeheader()
    for task in tasks if tasks is not None else build_review_tasks(context):
        decision = task.review_decision
        missing_sources = _missing_local_sources(task)
        writer.writerow(
            {
                "id": csv_safe_cell(task.id),
                "refdes": csv_safe_cell(task.refdes),
                "status_group": csv_safe_cell(task.status_group),
                "trust_tier": csv_safe_cell(task.trust_tier),
                "title": csv_safe_cell(task.title),
                "recommended_action": csv_safe_cell(task.recommended_action),
                "source_classes": csv_safe_cell(";".join(task.source_classes)),
                "review_status": csv_safe_cell(decision.status if decision else "open"),
                "review_reason": csv_safe_cell(decision.reason if decision else ""),
                "review_updated_at": csv_safe_cell(decision.updated_at if decision else ""),
                "derived_from_task_id": csv_safe_cell(task.derived_from_task_id or ""),
                "signoff_evidence_ready": csv_safe_cell(str(not missing_sources).lower()),
                "missing_local_sources": csv_safe_cell(";".join(missing_sources)),
            }
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="hardwise-findings.csv"'},
    )


def _annotations_response(
    context: WorkbenchContext,
    *,
    tasks: list[ReviewTask] | None = None,
) -> Response:
    lines = [
        "# Hardwise EDA annotation export",
        "# format: refdes,status_group,task_id,title,recommended_action,review_status,review_reason,signoff_evidence_ready,missing_local_sources",
    ]
    for task in tasks if tasks is not None else build_review_tasks(context):
        decision = task.review_decision
        missing_sources = _missing_local_sources(task)
        lines.append(
            ",".join(
                [
                    _annotation_cell(task.refdes),
                    _annotation_cell(task.status_group),
                    _annotation_cell(task.id),
                    _annotation_cell(task.title),
                    _annotation_cell(task.recommended_action),
                    _annotation_cell(decision.status if decision else "open"),
                    _annotation_cell(decision.reason if decision else ""),
                    _annotation_cell(str(not missing_sources).lower()),
                    _annotation_cell(";".join(missing_sources)),
                ]
            )
        )
    return Response(
        content="\n".join(lines) + "\n",
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="hardwise-annotations.txt"'},
    )


def _annotation_cell(value: object) -> str:
    return csv_safe_cell(str(value).replace("\n", " ").replace(",", "；"))


def _missing_local_sources(task: ReviewTask) -> list[str]:
    return sorted(
        {
            evidence.token
            for chain in task.evidence_chain
            for evidence in chain.evidence
            if evidence.audit_status == "missing_local_source"
        }
    )
