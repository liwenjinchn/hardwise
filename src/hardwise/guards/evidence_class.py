"""Evidence-token source classification and local-source audit helpers."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


EvidenceSourceClass = Literal[
    "live_retrieved",
    "reviewed_profile",
    "document_index",
    "design_source",
    "unknown",
]
EvidenceAuditStatus = Literal["ok", "missing_local_source"]

LOCAL_PDF_PREFIXES = {"datasheet", "pdf"}


class EvidenceClassification(BaseModel):
    """One evidence token's source class plus filesystem audit state."""

    token: str
    source_class: EvidenceSourceClass
    audit_status: EvidenceAuditStatus = "ok"
    local_source: str | None = None
    reason: str = ""


def classify_evidence_token(
    token: str,
    *,
    live_retrieved_tokens: Iterable[str] | None = None,
    source_roots: Sequence[str | Path] | None = None,
) -> EvidenceClassification:
    """Classify one token by provenance origin and local PDF availability."""

    value = token.strip()
    live_tokens = set(live_retrieved_tokens or [])
    source_class = _source_class(value, live_tokens)
    local_source, missing = _local_pdf_audit(value, source_roots)
    return EvidenceClassification(
        token=value,
        source_class=source_class,
        audit_status="missing_local_source" if missing else "ok",
        local_source=str(local_source) if local_source is not None else None,
        reason=_reason(value, source_class, missing),
    )


def classify_evidence_tokens(
    tokens: Iterable[str],
    *,
    live_retrieved_tokens: Iterable[str] | None = None,
    source_roots: Sequence[str | Path] | None = None,
) -> list[EvidenceClassification]:
    """Classify a sequence of evidence tokens, preserving input order."""

    live_tokens = set(live_retrieved_tokens or [])
    return [
        classify_evidence_token(
            token,
            live_retrieved_tokens=live_tokens,
            source_roots=source_roots,
        )
        for token in tokens
    ]


def _source_class(token: str, live_retrieved_tokens: set[str]) -> EvidenceSourceClass:
    if token in live_retrieved_tokens:
        return "live_retrieved"
    prefix = _token_prefix(token)
    if prefix == "doc":
        return "document_index"
    if prefix in {"datasheet", "pdf", "public_profile", "reviewer_to_confirm"}:
        return "reviewed_profile"
    if prefix in {"sch", "bom", "drc", "rule", "netlist"}:
        return "design_source"
    return "unknown"


def _local_pdf_audit(
    token: str,
    source_roots: Sequence[str | Path] | None,
) -> tuple[Path | None, bool]:
    prefix = _token_prefix(token)
    if prefix not in LOCAL_PDF_PREFIXES:
        return None, False

    source = _token_source(token)
    if not source or _is_url(source) or not source.lower().endswith(".pdf"):
        return None, False

    for candidate in _candidate_paths(source, source_roots):
        if candidate.is_file():
            return candidate, False
    return None, True


def _candidate_paths(source: str, source_roots: Sequence[str | Path] | None) -> list[Path]:
    source_path = Path(source)
    if source_path.is_absolute():
        return [source_path]

    roots = (
        [Path(root) for root in source_roots]
        if source_roots is not None
        else [
            Path.cwd(),
            Path.cwd() / "data" / "datasheets",
            Path.cwd() / "datasheets",
            Path.cwd() / "data",
        ]
    )
    return [root / source_path for root in roots]


def _token_prefix(token: str) -> str:
    prefix, separator, _rest = token.partition(":")
    return prefix if separator else ""


def _token_source(token: str) -> str:
    _prefix, _separator, rest = token.partition(":")
    source, _anchor, _fragment = rest.partition("#")
    return source


def _is_url(source: str) -> bool:
    return "://" in source


def _reason(
    token: str,
    source_class: EvidenceSourceClass,
    missing: bool,
) -> str:
    if missing:
        return "datasheet/pdf token points to a local PDF that is not present"
    if source_class == "live_retrieved":
        return "token came from this turn's search_datasheet retrieval trace"
    if source_class == "reviewed_profile":
        return "token came from reviewed profile or validator evidence, not this turn's retrieval"
    if source_class == "document_index":
        return "token points to a local document-index row"
    if source_class == "design_source":
        return "token points to deterministic design/checklist evidence"
    return f"unrecognized evidence token format: {token}"


__all__ = [
    "EvidenceAuditStatus",
    "EvidenceClassification",
    "EvidenceSourceClass",
    "classify_evidence_token",
    "classify_evidence_tokens",
]
