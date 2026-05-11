"""Evidence Ledger — drop any finding that doesn't carry a source token.

Per `data/checklists/sch_review.yaml` and DR-008: every finding must reference
where its claim came from (`sch:...`, `bom:...`, `datasheet:...#pNN`, `drc:...`,
`rule:...`). Findings with empty `evidence_tokens` are silently dropped before
reaching the report — they are unsupported claims by definition.
"""

from __future__ import annotations

from hardwise.checklist.finding import Finding


def strip_unsupported(findings: list[Finding]) -> tuple[list[Finding], int]:
    """Return (findings_with_evidence, num_dropped)."""

    kept = [f for f in findings if f.evidence_tokens]
    dropped = len(findings) - len(kept)
    return kept, dropped
