"""Evidence Ledger — drop any finding that doesn't carry a source token.

Per `data/checklists/sch_review.yaml` and DR-008: every finding must reference
where its claim came from (`sch:...`, `bom:...`, `datasheet:...#pNN`, `drc:...`,
`rule:...`). Findings with empty `evidence_tokens` are silently dropped before
reaching the report — they are unsupported claims by definition.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from hardwise.checklist.finding import Finding
from hardwise.guards.evidence_class import (
    EvidenceAuditStatus,
    EvidenceClassification,
    EvidenceSourceClass,
    classify_evidence_token,
    classify_evidence_tokens,
)

# Source-token shapes the model may echo in free prose that the workbench
# renders as authoritative evidence chips (CopilotPanel `renderInline`). A
# negative lookbehind for an ASCII word char (not `\b`) is deliberate: Python's
# `\w` is Unicode, so `\b` would miss a token glued to Chinese prose
# (`电感不足datasheet:…`) that the JS renderer — whose `\w` is ASCII — still chips.
_CITED_TOKEN_PATTERN = re.compile(r"(?<![A-Za-z0-9_])(?:datasheet|doc):[^\s,;，。；：、)）]+")


def cited_evidence_tokens(text: str) -> list[str]:
    """Return `datasheet:`/`doc:` source tokens echoed in free model prose.

    Order-preserving and de-duplicated. These are the tokens the Copilot panel
    styles as evidence chips, so they are the surface that misleads a reviewer
    if the model emits one without a backing tool result.
    """

    seen: list[str] = []
    for match in _CITED_TOKEN_PATTERN.finditer(text):
        token = match.group(0)
        if token not in seen:
            seen.append(token)
    return seen


def unsupported_evidence_tokens(text: str, verified_tokens: Iterable[str]) -> list[str]:
    """Source tokens cited in prose that this turn's tools did not produce.

    Second layer of defense for the evidence channel, mirroring the Refdes Guard
    (`guards/refdes.py`): a `datasheet:`/`doc:` token in the answer must trace
    back to a tool result from the same turn. Tokens absent from
    `verified_tokens` are unsupported — surfaced without retrieval/profile
    backing — so callers can downgrade them from authoritative evidence chips.
    """

    verified = set(verified_tokens)
    return [token for token in cited_evidence_tokens(text) if token not in verified]



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
    "cited_evidence_tokens",
    "classify_evidence_token",
    "classify_evidence_tokens",
    "has_evidence",
    "strip_unsupported",
    "unsupported_evidence_tokens",
]
