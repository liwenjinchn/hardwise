"""Validated, project-scoped history embedded in a read-only report."""

from datetime import datetime, timezone
from pydantic import BaseModel, Field
from hardwise.workbench.review_history import ReviewHistoryEvent
from hardwise.workbench.run_provenance import RunProvenanceResponse, load_run_provenance


class OfflineReviewHistory(BaseModel):
    project_id: str
    run_id: str
    captured_at: str
    total: int = Field(ge=0)
    events: list[ReviewHistoryEvent]
    run_provenance: dict[str, RunProvenanceResponse]


def build_offline_history(project, run_id, events, runs):
    # Some legacy events predate recorded run snapshots. Preserve their missing state.
    for event in events:
        runs.setdefault(event["run_id"], {"project": project})
    records = {rid: load_run_provenance(None, runs, project, rid) for rid in runs}
    return OfflineReviewHistory(
        project_id=project,
        run_id=run_id,
        captured_at=datetime.now(timezone.utc).isoformat(),
        total=len(events),
        events=events,
        run_provenance=records,
    )
