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
    """Wrap unverified refdes-shaped tokens. Return (sanitized_text, num_wrapped).

    A token is left untouched when it is a verified refdes, a pin name (see
    `_looks_like_pin_name`), or a refdes-shaped identifier that literally appears
    in a parsed component's identity fields — a part number or package such as
    `EG2132` or `SOP8`. Those are verified board facts, not hallucinated refdes;
    a hallucinated designator like `U999` is absent from the board and stays
    wrapped, so anti-hallucination is preserved.
    """

    wrapped = 0
    verified_identifiers = _identity_tokens(registry)

    def _wrap(match: re.Match[str]) -> str:
        nonlocal wrapped
        token = match.group(0)
        if _looks_like_pin_name(text, match.start(), match.end()):
            return token
        if registry.has_refdes(token):
            return token
        if token in verified_identifiers:
            return token
        wrapped += 1
        return f"⟨?{token}⟩"

    return REFDES_PATTERN.sub(_wrap, text), wrapped


def _identity_tokens(registry: BoardRegistry) -> set[str]:
    """Refdes-shaped tokens that occur in parsed component identity fields.

    Part numbers and packages such as `EG2132` or `SOP8` match the refdes regex
    but are verified board facts, not reference designators. When such a token is
    literally present in a component's value / footprint / datasheet, the guard
    treats it as verified-from-source and does not wrap it. Hallucinated refdes
    never appear here, so they stay wrapped — this removes the false positive
    without weakening refdes anti-hallucination (the 2026-05-14 learning_log
    entry pointed to exactly this: disambiguate via parsed facts, not the regex).
    """
    tokens: set[str] = set()
    for component in registry.components:
        for field_value in (component.value, component.footprint, component.datasheet):
            if field_value:
                tokens.update(REFDES_PATTERN.findall(field_value))
    return tokens


def _looks_like_pin_name(text: str, start: int, end: int) -> bool:
    """Skip tokens inside a pin-name parenthetical: `pin 17 (RA0)` or `pin 12 (ICSPC/RB6)`.

    Handles both single-function pins `(RA0)` and multi-function pins `(GP4/OSC2)`.
    """

    direct_prefix = text[max(0, start - 8) : start]
    if re.search(r"\bpin\s*$", direct_prefix, re.IGNORECASE):
        return True

    # Look backward for the opening paren and forward for the closing paren
    open_paren = text.rfind("(", 0, start)
    close_paren = text.find(")", end)

    if open_paren == -1 or close_paren == -1:
        return False

    # Check if there's a "pin N/name" pattern before the opening paren
    prefix = text[max(0, open_paren - 18) : open_paren]
    if re.search(r"\bpin\s+[A-Z0-9_/-]+\s*$", prefix, re.IGNORECASE):
        return True

    # Connector pin names can be alphanumeric (`A4`, `B7`) and appear in
    # generated R003 connector summaries as `NC pins (A4, B7)`.
    return bool(re.search(r"\bNC\s+pins?\s*$", prefix, re.IGNORECASE))


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
