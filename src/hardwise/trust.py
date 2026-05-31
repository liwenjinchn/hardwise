"""Shared trust-tier labels for reports, workbench traces, and agent evidence."""

from __future__ import annotations

from typing import Literal

TrustTier = Literal["l1", "l2", "l3"]

TRUST_LABELS: dict[TrustTier, str] = {
    "l1": "L1 deterministic",
    "l2": "L2 grounded",
    "l3": "L3 manual",
}


def trust_label_text(tier: TrustTier) -> str:
    """Return the stable UI label for a presentation-only trust tier."""

    return TRUST_LABELS[tier]
