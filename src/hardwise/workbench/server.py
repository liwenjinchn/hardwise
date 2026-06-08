"""FastAPI app for the live workbench."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from hardwise.report.copilot_panel import render_copilot_panel
from hardwise.report.validator_project_ui import render_project_workbench
from hardwise.workbench.chat import ChatRequest, ChatResponse, WorkbenchChatService, default_refdes
from hardwise.workbench.context import WorkbenchContext
from hardwise.workbench.view_model import (
    ComponentMiss,
    build_component_detail,
    build_risk_hints_summary,
    build_workbench_state,
)

STATIC_DIR = Path(__file__).with_name("static")


def risk_hints_state(context: WorkbenchContext) -> dict[str, object]:
    """Return a compact state summary for externally loaded risk hints."""

    return build_risk_hints_summary(context.risk_hints).model_dump()


def create_workbench_app(
    context: WorkbenchContext,
    chat_service: WorkbenchChatService,
) -> FastAPI:
    """Create the local live workbench app."""

    app = FastAPI(title="Hardwise Workbench", docs_url=None, redoc_url=None)
    static_index = STATIC_DIR / "index.html"
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="workbench-assets")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/", response_class=HTMLResponse)
    def index():
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
        return build_workbench_state(
            context,
            datasheet_search_enabled=chat_service.datasheet_search_enabled,
        ).model_dump()

    @app.get("/api/workbench/components/{refdes}")
    def component_detail(refdes: str):
        detail = build_component_detail(context, refdes)
        if isinstance(detail, ComponentMiss):
            return JSONResponse(status_code=404, content=detail.model_dump())
        return detail.model_dump()

    @app.post("/api/workbench/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        return chat_service.ask(request)

    return app
