"""FastAPI app for the live workbench."""

from __future__ import annotations

import copy
import logging
import shutil
import sqlite3
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from threading import RLock
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
from hardwise.workbench.chat_client import WorkbenchAIUnavailable
from hardwise.workbench.ai_disclosure import AIDisclosure, AIConfirmationRequired
from hardwise.workbench.api_contracts import ImportResponse
from hardwise.workbench.review_history import ReviewHistoryPage
from hardwise.workbench.run_provenance import RunProvenanceResponse, build_run_provenance
from hardwise.workbench.context import (
    WorkbenchContext,
    build_workbench_context,
    close_workbench_context,
)
from hardwise.workbench.context_manager import WorkbenchContextManager
from hardwise.workbench.server_datasheet_candidates import (
    _attach_auto_datasheet_candidates,
    DATASHEET_QUERY_DISCLOSURE,
    _datasheets_api_key,
)
from hardwise.workbench.server_io import (
    _annotation_cell,
    _annotations_response,
    _save_upload,
    _task_csv_response,
)
from hardwise.workbench.datasheet_candidates import (
    DatasheetCandidateSearchMiss,
    build_datasheet_candidate_search_packet,
    render_datasheet_candidate_search_markdown,
)
from hardwise.workbench.view_model import (
    ComponentMiss,
    ComponentDetail,
    WorkbenchState,
    build_review_prep_packet,
    build_component_detail,
    build_risk_hints_summary,
    build_workbench_state,
    render_review_prep_packet_markdown,
)

__all__ = ["_annotation_cell", "create_workbench_app", "risk_hints_state"]
from hardwise.workbench.prep_packet import (
    build_project_review_prep_packet,
    render_project_review_prep_packet_markdown,
)
from hardwise.workbench.profile_promotion import (
    ProfilePromotionMiss,
    build_profile_promotion_packet,
    render_profile_promotion_packet_markdown,
)
from hardwise.workbench.decision_fingerprints import review_fingerprints, review_project_key
from hardwise.workbench.decision_journal import ReviewConflictError
from hardwise.workbench.review_decisions import (
    ReviewDecisionRequest,
    ReviewDecisionStore,
)
from hardwise.workbench.task_projection import build_review_tasks

STATIC_DIR = Path(__file__).with_name("static")


def risk_hints_state(context: WorkbenchContext) -> dict[str, object]:
    """Return a compact state summary for externally loaded risk hints."""

    return build_risk_hints_summary(context.risk_hints).model_dump()


def create_workbench_app(
    context: WorkbenchContext,
    chat_service: WorkbenchChatService,
    *,
    profiles: Path | None = None,
    document_index: Path | None = None,
    pin_table: Path | None = None,
    review_package_manifest: Path | None = None,
    auto_datasheet_candidates: bool = False,
    review_db: Path | None = None,
) -> FastAPI:
    """Create the workbench; explicit query opt-in discloses its outbound boundary."""
    if auto_datasheet_candidates:
        logging.getLogger(__name__).warning(DATASHEET_QUERY_DISCLOSURE)

    # Import must retain the caller's actual profile collection, including managed copies.
    profiles = profiles if profiles is not None else Path(context.candidate_report.profiles_dir)
    context_manager = WorkbenchContextManager(context)
    review_decisions = ReviewDecisionStore(review_db)
    review_workflow_lock = RLock()

    def start_review_run(active_context):
        tasks = build_review_tasks(active_context)
        return review_decisions.begin_run(
            review_project_key(active_context),
            review_fingerprints(active_context, tasks),
            tasks=[task.model_dump(mode="json") for task in tasks],
            provenance=build_run_provenance(active_context).model_dump(mode="json"),
        )

    def decisions_for(active_context, tasks):
        return review_decisions.apply(
            tasks,
            fingerprints=review_fingerprints(active_context, tasks),
            project=review_project_key(active_context),
        )

    start_review_run(context)

    def state_with_decisions(active_context: WorkbenchContext) -> WorkbenchState:
        state = build_workbench_state(
            active_context,
            datasheet_search_enabled=chat_service.datasheet_search_enabled,
            datasheet_candidate_lookup_enabled=auto_datasheet_candidates,
        )
        state.review_tasks = decisions_for(active_context, state.review_tasks)
        state.review_decisions = review_decisions.summary(
            [task.stable_key for task in state.review_tasks],
            project=review_project_key(active_context),
        )
        return state

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        context_manager.shutdown()

    app = FastAPI(title="Hardwise Workbench", docs_url=None, redoc_url=None, lifespan=lifespan)
    app.state.workbench_context = context_manager
    current_context = context_manager
    from hardwise.workbench.managed_project_routes import register_managed_project_routes

    register_managed_project_routes(
        app,
        journal=review_db,
        manager=context_manager,
        lock=review_workflow_lock,
        decisions=review_decisions,
        start_run=start_review_run,
        state_for=state_with_decisions,
        chat_service=chat_service,
    )

    from hardwise.workbench.voltage_review_routes import register_voltage_review_routes

    register_voltage_review_routes(
        app,
        journal=review_db,
        manager=context_manager,
        lock=review_workflow_lock,
        decisions=review_decisions,
        chat_service=chat_service,
    )

    from hardwise.workbench.offline_report_routes import register_offline_report_route

    register_offline_report_route(
        app,
        manager=context_manager,
        lock=review_workflow_lock,
        decisions=review_decisions,
        state_for=state_with_decisions,
        chat_service=chat_service,
    )

    @app.middleware("http")
    async def lease_workbench_context(request, call_next):
        with context_manager.lease():
            return await call_next(request)

    static_index = STATIC_DIR / "index.html"
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="workbench-assets")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/", response_class=HTMLResponse)
    def index():
        with context_manager.lease() as context:
            if static_index.is_file():
                return FileResponse(static_index)

            selected = default_refdes(context)
            snapshot_service = copy.copy(chat_service)
            snapshot_service.context = context
            suggestions = snapshot_service.fallback_response("", selected).suggestions
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

    @app.get("/api/workbench/state", response_model=WorkbenchState)
    def state() -> WorkbenchState:
        with context_manager.lease() as context:
            return state_with_decisions(context)

    @app.get("/api/workbench/components/{refdes}", response_model=ComponentDetail)
    def component_detail(refdes: str) -> ComponentDetail | JSONResponse:
        with context_manager.lease() as context:
            detail = build_component_detail(context, refdes)
            if isinstance(detail, ComponentMiss):
                return JSONResponse(status_code=404, content=detail.model_dump())
            if auto_datasheet_candidates:
                detail = _attach_auto_datasheet_candidates(context, detail)
            detail.tasks = decisions_for(context, detail.tasks)
            return detail

    @app.get("/api/workbench/components/{refdes}/prep-packet")
    def component_prep_packet(
        refdes: str,
        format: Literal["json", "markdown"] = Query("json"),
    ) -> Response:
        context = current_context["value"]
        packet = build_review_prep_packet(context, refdes)
        if isinstance(packet, ComponentMiss):
            return JSONResponse(status_code=404, content=packet.model_dump())
        packet.tasks = decisions_for(context, packet.tasks)
        packet.component.tasks = list(packet.tasks)
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
        packet.priority_tasks = decisions_for(context, packet.priority_tasks)
        packet.review_decisions = review_decisions.summary(
            [task.stable_key for task in build_review_tasks(context)],
            project=review_project_key(context),
        )
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
        if not auto_datasheet_candidates:
            raise HTTPException(
                status_code=403,
                detail="资料联网查询已关闭；需显式启用 --auto-datasheet-candidates。"
                "启用后将向 https://www.datasheets.com/api/v1/search 发送器件型号/标识、"
                "limit/page及资料服务认证；不上传设计原文件。此设置独立于云AI确认。",
            )
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

    @app.post("/api/workbench/import", response_model=ImportResponse)
    def import_workbench(
        netlist: UploadFile = File(...),
        bom: UploadFile | None = File(None),
        document_index_csv: UploadFile | None = File(None),
        pin_table_csv: UploadFile | None = File(None),
        risk_hints_json: UploadFile | None = File(None),
        voltage_facts_json: UploadFile | None = File(None),
        review_package: UploadFile | None = File(None),
    ) -> ImportResponse:
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
            document_index_path = (
                _save_upload(
                    document_index_csv,
                    import_dir,
                    fallback_name="document_index.csv",
                )
                if document_index_csv
                else None
            )
            pin_table_path = (
                _save_upload(pin_table_csv, import_dir, fallback_name="pin_table.csv")
                if pin_table_csv
                else None
            )
            review_package_path = (
                _save_upload(review_package, import_dir, fallback_name="review_package.yaml")
                if review_package
                else None
            )
            voltage_facts_path = (
                _save_upload(voltage_facts_json, import_dir, fallback_name="voltage_facts.json")
                if voltage_facts_json
                else None
            )
            next_context = build_workbench_context(
                voltage_facts=voltage_facts_path,
                netlist_path=netlist_path,
                bom_path=bom_path,
                profiles=profiles,
                document_index=document_index_path,
                risk_hints_json=hints_path,
                review_package_manifest=review_package_path,
                pin_table=pin_table_path,
            )
        except Exception as exc:
            shutil.rmtree(import_dir, ignore_errors=True)
            raise HTTPException(status_code=400, detail=f"import failed: {exc}") from exc

        try:
            state = build_workbench_state(
                next_context,
                datasheet_search_enabled=chat_service.datasheet_search_enabled,
                datasheet_candidate_lookup_enabled=auto_datasheet_candidates,
            )
            with review_workflow_lock:
                checkpoint = review_decisions.checkpoint()
                try:
                    start_review_run(next_context)
                    context_manager.swap(next_context, import_dir=import_dir)
                except Exception:
                    review_decisions.restore_checkpoint(checkpoint)
                    raise
        except Exception as exc:
            try:
                close_workbench_context(next_context)
            finally:
                shutil.rmtree(import_dir, ignore_errors=True)
            raise HTTPException(status_code=503, detail=f"import activation failed: {exc}") from exc
        if hasattr(chat_service, "context"):
            chat_service.context = next_context
        return ImportResponse(
            ok=True,
            project=state.project,
            summary=state.summary,
            evidence_package=state.evidence_package,
            pin_table=state.pin_table,
            review_package=state.review_package,
            selected_refdes=state.selected_refdes,
            task_counts=state.task_counts,
        )

    @app.get("/api/workbench/export")
    def export_workbench(
        format: Literal["json", "csv", "annotations"] = Query("json"),
    ) -> Response:
        with context_manager.lease() as context:
            if format == "json":
                state_payload = state_with_decisions(context).model_dump(mode="json")
                return JSONResponse(
                    content=state_payload,
                    headers={
                        "Content-Disposition": 'attachment; filename="hardwise-workbench.json"'
                    },
                )
            if format == "csv":
                return _task_csv_response(
                    context,
                    tasks=decisions_for(context, build_review_tasks(context)),
                )
            return _annotations_response(
                context,
                tasks=decisions_for(context, build_review_tasks(context)),
            )

    @app.get("/api/workbench/review-decisions/history", response_model=ReviewHistoryPage)
    def review_history(
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        expected_project_id: str | None = None,
    ):
        with review_workflow_lock:
            try:
                return review_decisions.history_page(limit, offset, expected_project_id)
            except ReviewConflictError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            except (sqlite3.Error, OSError) as exc:
                raise HTTPException(
                    status_code=503, detail="Review history could not be read."
                ) from exc

    @app.get("/api/workbench/review-runs/{run_id}/provenance", response_model=RunProvenanceResponse)
    def review_run_provenance(
        run_id: str, response: Response, expected_project_id: str | None = None
    ):
        with review_workflow_lock:
            try:
                result = RunProvenanceResponse.model_validate(
                    review_decisions.run_provenance(run_id, expected_project_id)
                )
            except ReviewConflictError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            except KeyError as exc:
                raise HTTPException(
                    status_code=404, detail="Run not found in the active project."
                ) from exc
            except (sqlite3.Error, OSError, ValueError) as exc:
                raise HTTPException(
                    status_code=503, detail="Run provenance could not be read."
                ) from exc
            response.headers["Content-Disposition"] = (
                'attachment; filename="hardwise-run-provenance.json"'
            )
            return result

    @app.put("/api/workbench/review-decisions")
    def update_review_decisions(request: ReviewDecisionRequest) -> WorkbenchState:
        with review_workflow_lock, context_manager.lease() as context:
            tasks = build_review_tasks(context)
            try:
                review_decisions.update(
                    known_keys=[task.stable_key for task in tasks],
                    request=request,
                    fingerprints=review_fingerprints(context, tasks),
                )
            except ReviewConflictError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            except KeyError as exc:
                raise HTTPException(
                    status_code=404,
                    detail=f"unknown stable finding key: {exc.args[0]}",
                ) from exc
            except (sqlite3.Error, OSError) as exc:
                raise HTTPException(
                    status_code=503,
                    detail="Review decision was not saved; previous records remain unchanged.",
                ) from exc
            return state_with_decisions(context)

    @app.post("/api/workbench/rerun")
    def rerun_workbench() -> WorkbenchState:
        """Rebuild deterministic truth and reconcile decisions by stable key."""
        with review_workflow_lock:
            with context_manager.lease() as context:
                try:
                    next_context = build_workbench_context(
                        netlist_path=context.netlist_source,
                        bom_path=context.bom.source_file,
                        profiles=Path(context.candidate_report.profiles_dir),
                        document_index=(
                            context.document_report.document_index_file
                            if context.document_report is not None
                            else None
                        ),
                        risk_hints_json=(
                            Path(context.risk_hints.source_path)
                            if context.risk_hints.source_path
                            else None
                        ),
                        review_package_manifest=(
                            Path(context.review_package.source_path)
                            if context.review_package.source_path
                            else None
                        ),
                        pin_table=context.pin_table_path,
                        voltage_facts=context.voltage_facts_path,
                    )
                except Exception as exc:
                    raise HTTPException(status_code=422, detail=f"rerun failed: {exc}") from exc
            next_context.managed_project_key = context.managed_project_key
            next_context.managed_project_id = context.managed_project_id
            try:
                start_review_run(next_context)
            except ReviewConflictError as exc:
                close_workbench_context(next_context)
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            except (sqlite3.Error, OSError, ValueError) as exc:
                close_workbench_context(next_context)
                raise HTTPException(
                    status_code=503,
                    detail="Rerun review snapshot was not saved; the active run remains unchanged.",
                ) from exc
            context_manager.refresh(next_context)
            if hasattr(chat_service, "context"):
                chat_service.context = next_context
            return state_with_decisions(next_context)

    @app.get("/api/workbench/ai-disclosure", response_model=AIDisclosure)
    def ai_disclosure():
        with context_manager.lease() as context:
            service = copy.copy(chat_service)
            service.context = context
            if not hasattr(service, "disclosure"):
                return AIDisclosure(
                    mode="unavailable",
                    available=False,
                    data_categories=[],
                    notice="此工作台未启用 AI；本地评审仍可使用。",
                )
            return service.disclosure()

    @app.post("/api/workbench/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        with context_manager.lease() as context:
            snapshot_service = copy.copy(chat_service)
            snapshot_service.context = context
            try:
                return snapshot_service.ask(request)
            except AIConfirmationRequired as exc:
                raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
            except WorkbenchAIUnavailable as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc

    return app
