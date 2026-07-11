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
from hardwise.workbench.view_model import build_review_tasks


def _save_upload(upload: UploadFile, directory: Path, *, fallback_name: str) -> Path:
    safe_name = Path(upload.filename or fallback_name).name or fallback_name
    target = directory / safe_name
    upload.file.seek(0)
    with target.open("wb") as handle:
        shutil.copyfileobj(upload.file, handle)
    return target


def _task_csv_response(context: WorkbenchContext) -> Response:
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
        ],
    )
    writer.writeheader()
    for task in build_review_tasks(context):
        writer.writerow(
            {
                "id": csv_safe_cell(task.id),
                "refdes": csv_safe_cell(task.refdes),
                "status_group": csv_safe_cell(task.status_group),
                "trust_tier": csv_safe_cell(task.trust_tier),
                "title": csv_safe_cell(task.title),
                "recommended_action": csv_safe_cell(task.recommended_action),
                "source_classes": csv_safe_cell(";".join(task.source_classes)),
            }
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="hardwise-findings.csv"'},
    )


def _annotations_response(context: WorkbenchContext) -> Response:
    lines = [
        "# Hardwise EDA annotation export",
        "# format: refdes,status_group,task_id,title,recommended_action",
    ]
    for task in build_review_tasks(context):
        lines.append(
            ",".join(
                [
                    _annotation_cell(task.refdes),
                    _annotation_cell(task.status_group),
                    _annotation_cell(task.id),
                    _annotation_cell(task.title),
                    _annotation_cell(task.recommended_action),
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
