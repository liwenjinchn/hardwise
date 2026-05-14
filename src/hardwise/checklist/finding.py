"""Finding — the shared output type produced by every check function.

Per `docs/PLAN.md` DR-008, no rule, guard, or report writer is allowed to
introduce a parallel finding shape. Slice 1 ships this; Slice 2+ extend
behavior, never structure.

DR-009 (2026-05-14) extends `Finding` with two backward-compatible optional
fields — `evidence_chain` and `decision` — both default-empty so all existing
checks continue to work unchanged. The `EvidenceStep` model below is the unit
of structured provenance: every step names a `source` (EDA registry,
datasheet vector store, or rule deduction), a one-sentence human-readable
`claim`, and a machine-readable `token` reusing the `evidence_token()`
convention from `ingest/pdf.py`. `decision` carries the *machine* judgment
(`likely_ok` / `likely_issue` / `reviewer_to_confirm`) and is kept strictly
separate from `status`, which remains the *human / workflow* state field
(`open` / `accepted` / `rejected` / `closed`). Rule code writes `decision`;
human review writes `status`.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "low", "info"]
FindingStatus = Literal["open", "accepted", "rejected", "closed"]
EvidenceSource = Literal["eda", "datasheet", "rule"]
FindingDecision = Literal["likely_ok", "likely_issue", "reviewer_to_confirm"]


class EvidenceStep(BaseModel):
    """One step in a Finding's evidence chain.

    `source` constrains the provenance to the three real evidence channels in
    Hardwise; `claim` is the human-readable assertion; `token` is the machine
    pointer back to the source (e.g. `sch:foo.kicad_sch#U4` /
    `pdf:l78.pdf#p4` / `rule:R003#nc_match`).
    """

    source: EvidenceSource
    claim: str
    token: str


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
    evidence_chain: list[EvidenceStep] = Field(default_factory=list)
    decision: Optional[FindingDecision] = None
