"""Grounding helpers for datasheet-backed agent traces.

These helpers intentionally judge evidence presence, not natural-language
entailment. A datasheet search trace is L2 when retrieved chunks carry source
PDF + page provenance that can be shown to the reviewer.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from hardwise.trust import TrustTier


def datasheet_evidence_token(source_pdf: str, page: int) -> str | None:
    """Return the canonical datasheet source token for one retrieved page."""

    source = source_pdf.strip()
    if not source or page <= 0:
        return None
    return f"datasheet:{source}#p{page}"


def evidence_tokens_from_datasheet_hits(hits: Sequence[Any]) -> list[str]:
    """Extract stable evidence tokens from search_datasheet hits."""

    tokens: list[str] = []
    for hit in hits:
        source_pdf = _hit_value(hit, "source_pdf")
        page_value = _hit_value(hit, "page")
        try:
            page = int(page_value)
        except (TypeError, ValueError):
            continue
        token = datasheet_evidence_token(str(source_pdf or ""), page)
        if token and token not in tokens:
            tokens.append(token)
    return tokens


def trust_tier_for_datasheet_search(evidence_tokens: Sequence[str]) -> TrustTier:
    """Classify a datasheet search turn from retrieved evidence presence."""

    return "l2" if evidence_tokens else "l3"


def _hit_value(hit: Any, name: str) -> Any:
    if isinstance(hit, dict):
        return hit.get(name)
    return getattr(hit, name, None)
