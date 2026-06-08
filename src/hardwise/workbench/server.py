"""FastAPI app for the live workbench."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from hardwise.report.copilot_panel import render_copilot_panel
from hardwise.report.validator_project_ui import render_project_workbench
from hardwise.workbench.chat import ChatRequest, ChatResponse, WorkbenchChatService, default_refdes
from hardwise.workbench.context import WorkbenchContext


def risk_hints_state(context: WorkbenchContext) -> dict[str, object]:
    """Return a compact state summary for externally loaded risk hints."""

    return {
        "external_status": "loaded" if context.risk_hints.source_path else "not_configured",
        "count": context.risk_hints.total_count,
        "accepted_external_count": context.risk_hints.accepted_count,
        "rejected_external_count": context.risk_hints.rejected_count,
    }


def create_workbench_app(
    context: WorkbenchContext,
    chat_service: WorkbenchChatService,
) -> FastAPI:
    """Create the local live workbench app."""

    app = FastAPI(title="Hardwise Workbench", docs_url=None, redoc_url=None)

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
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
        )

    @app.get("/api/workbench/state")
    def state() -> dict[str, object]:
        return {
            "project_name": context.project_name,
            "components": context.index.components_in_design,
            "validated": len(context.index.validated_rows),
            "selected_refdes": default_refdes(context),
            "datasheet_search_enabled": chat_service.datasheet_search_enabled,
            "risk_hints": risk_hints_state(context),
        }

    @app.post("/api/workbench/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        return chat_service.ask(request)

    return app
