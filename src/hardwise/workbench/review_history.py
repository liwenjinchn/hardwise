"""Read-only history response, separate from current electrical assessments."""

from typing import Literal
from pydantic import BaseModel, Field
from hardwise.workbench.review_decision_contracts import ReviewDecisionView


class ReviewHistoryEvent(BaseModel):
    id: int
    run_id: str
    event: Literal["human_decision", "inputs_changed", "disappeared"]
    stable_key: str
    created_at: str
    decision: ReviewDecisionView


class ReviewHistoryPage(BaseModel):
    project_id: str
    run_id: str
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=1000)
    offset: int = Field(ge=0)
    events: list[ReviewHistoryEvent]
