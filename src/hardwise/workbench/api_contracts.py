"""Public JSON response contracts for the workbench API."""

from __future__ import annotations

from pydantic import BaseModel

from hardwise.workbench.evidence_package import EvidencePackageSummary

from hardwise.workbench.view_model import (
    PinTableSummary,
    ReviewPackageSummary,
    ReviewTaskCounts,
    WorkbenchProject,
    WorkbenchSummary,
)


class ImportResponse(BaseModel):
    """Summary returned after an uploaded project becomes the active context."""

    ok: bool
    project: WorkbenchProject
    summary: WorkbenchSummary
    evidence_package: EvidencePackageSummary
    pin_table: PinTableSummary
    review_package: ReviewPackageSummary
    selected_refdes: str | None = None
    task_counts: ReviewTaskCounts
