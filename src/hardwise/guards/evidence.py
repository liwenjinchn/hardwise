"""Evidence Ledger — drop any finding that doesn't carry a source token.

Per `data/checklists/sch_review.yaml` and DR-008: every finding must reference
where its claim came from (`sch:...`, `bom:...`, `datasheet:...#pNN`, `drc:...`,
`rule:...`). Findings with empty `evidence_tokens` are silently dropped before
reaching the report — they are unsupported claims by definition.
"""

from __future__ import annotations

from hardwise.checklist.finding import Finding
from hardwise.guards.evidence_class import (
    EvidenceAuditStatus,
    EvidenceClassification,
    EvidenceSourceClass,
    classify_evidence_token,
    classify_evidence_tokens,
)


def has_evidence(finding: Finding) -> bool:
    """Return true when a finding carries at least one source token.

    DR-009 added structured `evidence_chain` alongside legacy
    `evidence_tokens`; either path is a valid source-token carrier.
    """

    if finding.evidence_tokens:
        return True
    return any(step.token for step in finding.evidence_chain)


def strip_unsupported(findings: list[Finding]) -> tuple[list[Finding], int]:
    """Return (findings_with_evidence, num_dropped)."""

    kept = [f for f in findings if has_evidence(f)]
    dropped = len(findings) - len(kept)
    return kept, dropped


__all__ = [
    "EvidenceAuditStatus",
    "EvidenceClassification",
    "EvidenceSourceClass",
    "classify_evidence_token",
    "classify_evidence_tokens",
    "has_evidence",
    "strip_unsupported",
]
