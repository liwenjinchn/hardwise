"""Refdes Guard — wrap any refdes-shaped token not in the EDA registry as `⟨?XXX⟩`.

Per `CLAUDE.md` Hard rule #3: no refdes leaves Hardwise without registry verification.
This is the second of two defense layers. The first layer is tool discipline (tools
return `{found: false, ...}` for unknown refdes); this layer regex-scans every output
text just before it reaches the user.

Pattern `\\b[A-Z]{1,3}\\d{1,4}\\b` catches U23, R10, J5, IC1, BAT1 and similar
KiCad-style designators. Hits not present in `BoardRegistry.refdes_set` are wrapped.
"""

from __future__ import annotations

import re

from hardwise.adapters.base import BoardRegistry
from hardwise.checklist.finding import Finding

REFDES_PATTERN = re.compile(r"\b[A-Z]{1,3}\d{1,4}\b")


def sanitize_text(text: str, registry: BoardRegistry) -> tuple[str, int]:
    """Wrap unverified refdes-shaped tokens. Return (sanitized_text, num_wrapped)."""

    wrapped = 0

    def _wrap(match: re.Match[str]) -> str:
        nonlocal wrapped
        token = match.group(0)
        if registry.has_refdes(token):
            return token
        wrapped += 1
        return f"⟨?{token}⟩"

    return REFDES_PATTERN.sub(_wrap, text), wrapped


def sanitize_args(args: dict, registry: BoardRegistry) -> tuple[dict, int]:
    """Wrap unverified refdes in string-valued fields of a tool-args dict.

    Used when assembling user-visible *copies* of tool calls (e.g. `ToolCallTrace.input`).
    The tool itself sees the raw, untouched `args` — this function only sanitizes the
    display copy. Non-string values pass through unchanged.
    """

    wrapped_total = 0
    new_args: dict = {}
    for key, value in args.items():
        if isinstance(value, str):
            new_value, wrapped = sanitize_text(value, registry)
            new_args[key] = new_value
            wrapped_total += wrapped
        else:
            new_args[key] = value
    return new_args, wrapped_total


def sanitize_finding(f: Finding, registry: BoardRegistry) -> tuple[Finding, int]:
    """Apply the refdes guard to every text-bearing field of a Finding.

    Returns the sanitized Finding plus the total number of unverified tokens wrapped
    across all fields (used for the report's sanitizer note).
    """

    wrapped_total = 0

    new_message, w = sanitize_text(f.message, registry)
    wrapped_total += w

    new_action, w = sanitize_text(f.suggested_action, registry)
    wrapped_total += w

    new_refdes = f.refdes
    if f.refdes and not registry.has_refdes(f.refdes):
        new_refdes = f"⟨?{f.refdes}⟩"
        wrapped_total += 1

    return (
        f.model_copy(
            update={
                "message": new_message,
                "suggested_action": new_action,
                "refdes": new_refdes,
            }
        ),
        wrapped_total,
    )
