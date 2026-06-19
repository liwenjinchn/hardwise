"""Last-mile report safety helpers.

Report renderers are user-facing exits. Callers should still run the guards
before rendering, but this module lets renderers enforce the same invariant at
the boundary: no unsupported findings, and no unverified refdes when a registry
is available.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hardwise.checklist.finding import Finding
from hardwise.guards.evidence import strip_unsupported
from hardwise.guards.refdes import sanitize_finding


@dataclass(frozen=True)
class ReportSafetyResult:
    findings: list[Finding]
    dropped: int = 0
    wrapped: int = 0


def prepare_findings(
    findings: list[Finding], registry: Any | None = None
) -> ReportSafetyResult:
    """Strip unsupported findings and optionally sanitize refdes-shaped text."""

    kept, dropped = strip_unsupported(findings)
    if registry is None:
        return ReportSafetyResult(findings=kept, dropped=dropped)

    sanitized: list[Finding] = []
    wrapped_total = 0
    for finding in kept:
        clean, wrapped = sanitize_finding(finding, registry)
        sanitized.append(clean)
        wrapped_total += wrapped
    return ReportSafetyResult(findings=sanitized, dropped=dropped, wrapped=wrapped_total)
