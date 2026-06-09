"""FastAPI app for the live workbench."""

from __future__ import annotations

import csv
import io
import os
import shutil
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from hardwise.agent.evidence_locator import (
    LocateComponentEvidenceInput,
    locate_component_evidence,
)
from hardwise.report.copilot_panel import render_copilot_panel
from hardwise.report.validator_project_ui import render_project_workbench
from hardwise.workbench.chat import ChatRequest, ChatResponse, WorkbenchChatService, default_refdes
from hardwise.workbench.context import (
    WorkbenchContext,
    build_workbench_context,
    close_workbench_context,
)
from hardwise.workbench.datasheet_candidates import (
    DatasheetCandidateSearchMiss,
    build_datasheet_candidate_search_packet,
    render_datasheet_candidate_search_markdown,
)
from hardwise.workbench.view_model import (
    ComponentMiss,
    build_review_prep_packet,
    build_component_detail,
    build_review_tasks,
    build_risk_hints_summary,
    build_workbench_state,
    render_review_prep_packet_markdown,
)
from hardwise.workbench.prep_packet import (
    build_project_review_prep_packet,
    render_project_review_prep_packet_markdown,
)
from hardwise.workbench.profile_promotion import (
    ProfilePromotionMiss,
    build_profile_promotion_packet,
    render_profile_promotion_packet_markdown,
)

STATIC_DIR = Path(__file__).with_name("static")


def risk_hints_state(context: WorkbenchContext) -> dict[str, object]:
    """Return a compact state summary for externally loaded risk hints."""

    return build_risk_hints_summary(context.risk_hints).model_dump()


def create_workbench_app(
    context: WorkbenchContext,
    chat_service: WorkbenchChatService,
    *,
    profiles: Path = Path("data/datasheet_profiles"),
    document_index: Path | None = None,
) -> FastAPI:
    """Create the local live workbench app."""

    app = FastAPI(title="Hardwise Workbench", docs_url=None, redoc_url=None)
    current_context = {"value": context}
    import_dirs: list[Path] = []
    app.state.workbench_context = current_context
    static_index = STATIC_DIR / "index.html"
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="workbench-assets")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/", response_class=HTMLResponse)
    def index():
        context = current_context["value"]
        if static_index.is_file():
            return FileResponse(static_index)

        selected = default_refdes(context)
        suggestions = chat_service.fallback_response("", selected).suggestions
        copilot_html = render_copilot_panel(
            mode="live",
            selected_refdes=selected,
            suggestions=suggestions,
            api_endpoint="/api/workbench/chat",
            datasheet_search_enabled=chat_service.datasheet_search_enabled,
        )
        return render_project_workbench(
            context.design,
            context.index,
            project_name=context.project_name,
            netlist_source=context.netlist_source,
            bom_report=context.bom_report,
            generated_at=context.generated_at,
            copilot_html=copilot_html,
            risk_hints=context.risk_hints if context.risk_hints.source_path else None,
        )

    @app.get("/api/workbench/state")
    def state() -> dict[str, object]:
        context = current_context["value"]
        return build_workbench_state(
            context,
            datasheet_search_enabled=chat_service.datasheet_search_enabled,
        ).model_dump()

    @app.get("/api/workbench/components/{refdes}")
    def component_detail(refdes: str):
        context = current_context["value"]
        detail = build_component_detail(context, refdes)
        if isinstance(detail, ComponentMiss):
            return JSONResponse(status_code=404, content=detail.model_dump())
        return detail.model_dump()

    @app.get("/api/workbench/components/{refdes}/prep-packet")
    def component_prep_packet(
        refdes: str,
        format: Literal["json", "markdown"] = Query("json"),
    ) -> Response:
        context = current_context["value"]
        packet = build_review_prep_packet(context, refdes)
        if isinstance(packet, ComponentMiss):
            return JSONResponse(status_code=404, content=packet.model_dump())
        filename_refdes = refdes.upper()
        if format == "markdown":
            return Response(
                content=render_review_prep_packet_markdown(packet),
                media_type="text/markdown; charset=utf-8",
                headers={
                    "Content-Disposition": (
                        f'attachment; filename="hardwise-prep-{filename_refdes}.md"'
                    )
                },
            )
        return JSONResponse(
            content=packet.model_dump(mode="json"),
            headers={
                "Content-Disposition": (
                    f'attachment; filename="hardwise-prep-{filename_refdes}.json"'
                )
            },
        )

    @app.get("/api/workbench/components/{refdes}/evidence")
    def component_evidence(
        refdes: str,
        topic: str = Query("all"),
        pin_number: str | None = Query(None),
        limit: int = Query(12, ge=1, le=50),
    ) -> Response:
        context = current_context["value"]
        result = locate_component_evidence(
            context.design,
            context.validation_targets,
            context.index,
            context.document_report,
            LocateComponentEvidenceInput(
                refdes=refdes,
                topic=topic,
                pin_number=pin_number,
                limit=limit,
            ),
        )
        if result.status == "not_found":
            return JSONResponse(status_code=404, content=result.model_dump(mode="json"))
        return JSONResponse(content=result.model_dump(mode="json"))

    @app.get("/api/workbench/prep-packet")
    def project_prep_packet(
        format: Literal["json", "markdown"] = Query("json"),
    ) -> Response:
        context = current_context["value"]
        packet = build_project_review_prep_packet(context)
        if format == "markdown":
            return Response(
                content=render_project_review_prep_packet_markdown(packet),
                media_type="text/markdown; charset=utf-8",
                headers={
                    "Content-Disposition": ('attachment; filename="hardwise-project-prep.md"')
                },
            )
        return JSONResponse(
            content=packet.model_dump(mode="json"),
            headers={"Content-Disposition": ('attachment; filename="hardwise-project-prep.json"')},
        )

    @app.get("/api/workbench/profile-gaps/{group_id}/promotion-packet")
    def profile_promotion_packet(
        group_id: str,
        format: Literal["json", "markdown"] = Query("json"),
    ) -> Response:
        context = current_context["value"]
        packet = build_profile_promotion_packet(context, group_id)
        if isinstance(packet, ProfilePromotionMiss):
            return JSONResponse(status_code=404, content=packet.model_dump(mode="json"))
        if format == "markdown":
            return Response(
                content=render_profile_promotion_packet_markdown(packet),
                media_type="text/markdown; charset=utf-8",
                headers={
                    "Content-Disposition": (
                        f'attachment; filename="hardwise-profile-promotion-{group_id}.md"'
                    )
                },
            )
        return JSONResponse(
            content=packet.model_dump(mode="json"),
            headers={
                "Content-Disposition": (
                    f'attachment; filename="hardwise-profile-promotion-{group_id}.json"'
                )
            },
        )

    @app.get("/api/workbench/profile-gaps/{group_id}/datasheet-candidates")
    def datasheet_candidate_search(
        group_id: str,
        format: Literal["json", "markdown", "csv"] = Query("json"),
        limit: int = Query(5, ge=1, le=10),
        page: int = Query(1, ge=1),
        timeout_seconds: int = Query(20, ge=1, le=60, alias="timeout"),
    ) -> Response:
        context = current_context["value"]
        packet = build_datasheet_candidate_search_packet(
            context,
            group_id,
            api_key=_datasheets_api_key(),
            limit=limit,
            page=page,
            timeout_seconds=timeout_seconds,
        )
        if isinstance(packet, DatasheetCandidateSearchMiss):
            return JSONResponse(status_code=404, content=packet.model_dump(mode="json"))
        if format == "markdown":
            return Response(
                content=render_datasheet_candidate_search_markdown(packet),
                media_type="text/markdown; charset=utf-8",
                headers={
                    "Content-Disposition": (
                        f'attachment; filename="hardwise-datasheet-candidates-{group_id}.md"'
                    )
                },
            )
        if format == "csv":
            return Response(
                content=packet.document_index_csv,
                media_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": (
                        f'attachment; filename="hardwise-datasheet-candidates-{group_id}.csv"'
                    )
                },
            )
        return JSONResponse(
            content=packet.model_dump(mode="json"),
            headers={
                "Content-Disposition": (
                    f'attachment; filename="hardwise-datasheet-candidates-{group_id}.json"'
                )
            },
        )

    @app.post("/api/workbench/import")
    def import_workbench(
        netlist: UploadFile = File(...),
        bom: UploadFile | None = File(None),
        risk_hints_json: UploadFile | None = File(None),
    ) -> dict[str, object]:
        import_dir = Path(tempfile.mkdtemp(prefix="hardwise-workbench-import-"))
        try:
            netlist_path = _save_upload(netlist, import_dir, fallback_name="uploaded.net")
            bom_path = (
                _save_upload(bom, import_dir, fallback_name="uploaded_bom.csv") if bom else None
            )
            hints_path = (
                _save_upload(risk_hints_json, import_dir, fallback_name="risk_hints.json")
                if risk_hints_json
                else None
            )
            next_context = build_workbench_context(
                netlist_path=netlist_path,
                bom_path=bom_path,
                profiles=profiles,
                document_index=document_index,
                risk_hints_json=hints_path,
            )
        except Exception as exc:
            shutil.rmtree(import_dir, ignore_errors=True)
            raise HTTPException(status_code=400, detail=f"import failed: {exc}") from exc

        previous = current_context["value"]
        current_context["value"] = next_context
        if hasattr(chat_service, "context"):
            chat_service.context = next_context
        close_workbench_context(previous)
        import_dirs.append(import_dir)
        state = build_workbench_state(
            next_context,
            datasheet_search_enabled=chat_service.datasheet_search_enabled,
        )
        return {
            "ok": True,
            "project": state.project.model_dump(),
            "summary": state.summary.model_dump(),
            "selected_refdes": state.selected_refdes,
            "task_counts": state.task_counts.model_dump(),
        }

    @app.get("/api/workbench/export")
    def export_workbench(
        format: Literal["json", "csv", "annotations"] = Query("json"),
    ) -> Response:
        context = current_context["value"]
        if format == "json":
            state_payload = build_workbench_state(
                context,
                datasheet_search_enabled=chat_service.datasheet_search_enabled,
            ).model_dump(mode="json")
            return JSONResponse(
                content=state_payload,
                headers={"Content-Disposition": 'attachment; filename="hardwise-workbench.json"'},
            )
        if format == "csv":
            return _task_csv_response(context)
        return _annotations_response(context)

    @app.post("/api/workbench/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        return chat_service.ask(request)

    return app


def _datasheets_api_key() -> str | None:
    key = os.environ.get("DATASHEETS_API_KEY") or os.environ.get("DATASHEETS_COM_API_KEY")
    if key is None or key.strip() == "" or key.strip() == "replace_me":
        return None
    return key


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
                "id": task.id,
                "refdes": task.refdes,
                "status_group": task.status_group,
                "trust_tier": task.trust_tier,
                "title": task.title,
                "recommended_action": task.recommended_action,
                "source_classes": ";".join(task.source_classes),
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
    return str(value).replace("\n", " ").replace(",", "；")
