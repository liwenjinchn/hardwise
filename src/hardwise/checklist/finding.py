"""Finding — the shared output type produced by every check function.

Per `docs/PLAN.md` DR-008, no rule, guard, or report writer is allowed to
introduce a parallel finding shape. Slice 1 ships this; Slice 2+ extend
behavior, never structure.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "low", "info"]
FindingStatus = Literal["open", "accepted", "rejected", "closed"]


class Finding(BaseModel):
    """One row in the review report — aligned with《SCH_review_feedback_list 汇总表》."""

    rule_id: str
    severity: Severity
    refdes: str | None = None
    net: str | None = None
    message: str
    evidence_tokens: list[str] = Field(default_factory=list)
    suggested_action: str = ""
    status: FindingStatus = "open"
