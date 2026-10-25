"""Human review wire contracts; independent of journal storage and electrical truth."""

from typing import Literal
from pydantic import BaseModel, Field, field_validator

# New mutations require an explicit classification; legacy stored values remain readable.
ReviewDecisionStatus = Literal["open", "accepted_risk", "false_positive", "resolved"]
StoredReviewDecisionStatus = Literal[ReviewDecisionStatus, "accepted", "waived"]

REVIEW_STATUS_LABELS = {
    "open": "待处理",
    "accepted_risk": "接受风险",
    "false_positive": "误报",
    "resolved": "已解决",
    "needs_review": "需复核",
    "accepted": "旧版接受",
    "waived": "旧版豁免",
}


def review_status_label(status: str) -> str:
    return REVIEW_STATUS_LABELS.get(status, status)


class ReviewDecisionView(BaseModel):
    """One human workflow decision keyed by a stable finding key."""

    stable_key: str
    status: Literal[StoredReviewDecisionStatus, "needs_review"]
    reason: str
    updated_at: str
    previous_status: StoredReviewDecisionStatus | None = None
    fingerprint: str | None = None
    current_fingerprint: str | None = None


class ReviewDecisionRequest(BaseModel):
    """Mutation request used by the local workbench API."""

    stable_keys: list[str] = Field(min_length=1)
    status: ReviewDecisionStatus
    reason: str = ""
    expected_run_id: str | None = Field(default=None, min_length=1)

    @field_validator("stable_keys")
    @classmethod
    def unique_nonempty_keys(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("at least one stable finding key is required")
        return list(dict.fromkeys(cleaned))

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return value.strip()

    def require_reason(self) -> None:
        if self.status != "open" and not self.reason:
            raise ValueError(f"reason is required when review status is {self.status}")


class ReviewDecisionSummary(BaseModel):
    """Workflow counts kept separate from electrical task counts."""

    total_tasks: int
    open: int
    accepted: int
    waived: int
    resolved: int
    accepted_risk: int = 0
    false_positive: int = 0
    stale_removed_on_rerun: int = 0
    needs_review: int = 0
    storage: Literal["memory", "local_file"] = "memory"
    history_count: int = 0
    project_id: str | None = None
    run_id: str | None = None
