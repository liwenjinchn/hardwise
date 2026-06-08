"""Trace loading for Hardwise trust analytics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hardwise.analytics.trust_types import (
    TRUST_TIERS,
    SourceState,
    TraceExample,
    TraceHealth,
)


def load_trace(path: Path | None) -> TraceHealth:
    """Load review JSONL or workbench ChatResponse traces."""

    if path is None:
        return TraceHealth(
            source=SourceState(status="not_provided", message="No trace path provided.")
        )
    if not path.exists():
        return TraceHealth(
            source=SourceState(path=str(path), status="missing", message="Trace file not found.")
        )
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return TraceHealth(
            source=SourceState(path=str(path), status="empty", message="Trace file is empty."),
            available=True,
        )
    try:
        entries = _parse_entries(text)
    except ValueError as e:
        return TraceHealth(source=SourceState(path=str(path), status="invalid", message=str(e)))

    health = TraceHealth(
        source=SourceState(path=str(path), status="loaded", message="Loaded trace rows."),
        available=True,
        rows_read=len(entries),
    )
    for entry in entries:
        if isinstance(entry, dict):
            _consume_entry(health, entry)
    if health.review_runs and health.review_findings_total:
        health.trust_tier_counts["l1"] += health.review_findings_total
        health.notes.append(
            "Review run traces do not include per-tool trust tiers; deterministic findings "
            "are counted as L1."
        )
    if not any(health.trust_tier_counts.values()) and not health.review_runs:
        health.notes.append("No trust-tier rows were present in the trace input.")
    return health


def _consume_entry(health: TraceHealth, entry: dict[str, Any]) -> None:
    if entry.get("command") == "review":
        health.review_runs += 1
        health.review_findings_total += _int(entry.get("findings_total"))
        health.unverified_refdes_wrapped += _int(entry.get("unverified_refdes_wrapped"))
        health.findings_dropped_no_evidence += _int(entry.get("findings_dropped_no_evidence"))
        if entry.get("vector_enabled"):
            health.vector_enabled_runs += 1
        return

    traces = entry.get("trace")
    if isinstance(traces, list):
        health.workbench_turns += 1
        wrapped_before = health.unverified_refdes_wrapped
        for trace in traces:
            if isinstance(trace, dict):
                _consume_evidence_trace(health, trace)
        if health.unverified_refdes_wrapped == wrapped_before:
            health.unverified_refdes_wrapped += _int(entry.get("wrapped_count"))
        return

    if "trust_tier" in entry:
        _consume_evidence_trace(health, entry)


def _consume_evidence_trace(health: TraceHealth, trace: dict[str, Any]) -> None:
    tier = str(trace.get("trust_tier") or "")
    if tier not in TRUST_TIERS:
        return
    health.trust_tier_counts[tier] += 1
    wrapped = _int(trace.get("wrapped"))
    health.unverified_refdes_wrapped += wrapped
    if len(health.examples) < 8:
        health.examples.append(
            TraceExample(
                tier=tier,
                label=str(trace.get("trust_label") or tier.upper()),
                tool=str(trace.get("tool") or "trace"),
                summary=str(trace.get("summary") or ""),
                evidence=[str(item) for item in _list(trace.get("evidence"))[:4]],
                wrapped=wrapped,
            )
        )


def _parse_entries(text: str) -> list[Any]:
    stripped = text.strip()
    if stripped.startswith(("[", "{")):
        try:
            loaded = json.loads(stripped)
            return loaded if isinstance(loaded, list) else [loaded]
        except json.JSONDecodeError:
            pass

    entries: list[Any] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSONL trace at line {line_no}: {e}") from e
    return entries


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
