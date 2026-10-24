"""Download a frozen current-project report without mutating the review journal."""

import sqlite3
from fastapi import HTTPException, Query
from fastapi.responses import HTMLResponse
from hardwise.workbench.decision_journal import ReviewConflictError
from hardwise.workbench.decision_fingerprints import review_project_key
from hardwise.report.workbench_spa_snapshot import render_spa_snapshot


def register_offline_report_route(app, *, manager, lock, decisions, state_for, chat_service):
    @app.get("/api/workbench/offline-report", response_class=HTMLResponse)
    def offline_report(
        expected_project_id: str = Query(..., min_length=1),
        expected_run_id: str = Query(..., min_length=1),
    ):
        with lock, manager.lease() as context:
            try:
                if expected_project_id != review_project_key(context):
                    raise ReviewConflictError("active project changed; reload before exporting")
                history = decisions.offline_history(
                    expected_project_id=expected_project_id, expected_run_id=expected_run_id
                )
                state = state_for(context)
                state.review_decisions.history_count = history.total
                html = render_spa_snapshot(
                    context,
                    datasheet_search_enabled=chat_service.datasheet_search_enabled,
                    reviewed_state=state,
                    review_history=history,
                )
            except ReviewConflictError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            except (sqlite3.Error, OSError, ValueError) as exc:
                raise HTTPException(
                    status_code=503,
                    detail="Offline report could not be generated; no partial report was delivered.",
                ) from exc
        return HTMLResponse(
            html,
            headers={
                "Content-Disposition": 'attachment; filename="hardwise-review-offline.html"',
                "Cache-Control": "no-store",
            },
        )
