"""Spreadsheet formula-injection neutralization for CSV/TSV export exits.

A CSV cell whose text begins with ``=``, ``+``, ``-``, ``@`` (or a leading tab /
carriage return) can execute as a formula when the file is opened in Excel or
Google Sheets — the OWASP "CSV Injection" / "Formula Injection" class. Exported
cells carry BOM titles, component descriptions, refdes, and external
datasheet-API fields, none of which are fully trusted, so every render exit that
writes CSV must pass cell text through :func:`csv_safe_cell` first.

Note this also protects *legitimate* hardware data: rail labels such as ``+5V``,
``-12V``, or a tolerance like ``-10%`` start with ``+``/``-`` and would otherwise
render as broken formulas. Prefixing a single quote makes the spreadsheet show
the literal text.
"""

from __future__ import annotations

_DANGEROUS_LEADING = frozenset({"=", "+", "-", "@", "\t", "\r"})


def csv_safe_cell(value: object) -> str:
    """Return cell text, quote-prefixed when it could be read as a formula."""

    text = str(value)
    if text[:1] in _DANGEROUS_LEADING:
        return "'" + text
    return text
