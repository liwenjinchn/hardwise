"""Tiered Model Router — pick an upstream model by tier.

Slice 3 minimum: read `HARDWISE_MODEL_FAST/NORMAL/DEEP` from the
environment, fall back to NORMAL if a tier slot is missing, and a final
hard-coded fallback if NORMAL is also unset. The agent code never
hard-codes a specific model name — that decision lives in `.env`.

Why tiers exist at all when the upstream may serve only one model today:
keeping the 3-slot structure preserves the cost-aware-routing pattern
borrowed from Wrench Board. The day MiMo (or another upstream) ships
fast/normal/deep variants, only `.env` flips — no code change.

See DR-005 in docs/PLAN.md for rationale.
"""

from __future__ import annotations

import os
from typing import Literal

Tier = Literal["fast", "normal", "deep"]

_TIER_ENV_VAR: dict[Tier, str] = {
    "fast": "HARDWISE_MODEL_FAST",
    "normal": "HARDWISE_MODEL_NORMAL",
    "deep": "HARDWISE_MODEL_DEEP",
}

_FINAL_FALLBACK = "mimo-v2.5"


class ModelRouter:
    """Resolve a tier name to an upstream model id by reading env vars.

    Construction is cheap and stateless; readers should not cache instances.
    Passing an `env` dict (instead of letting the router read os.environ)
    is how the tests pin behavior without monkey-patching the OS.
    """

    def __init__(self, env: dict[str, str] | None = None) -> None:
        self._env = env if env is not None else dict(os.environ)

    def select(self, tier: Tier = "normal") -> str:
        """Return the model id for `tier`, falling back through normal → fallback."""
        var = _TIER_ENV_VAR.get(tier, "HARDWISE_MODEL_NORMAL")
        value = self._env.get(var, "").strip()
        if value:
            return value
        normal = self._env.get("HARDWISE_MODEL_NORMAL", "").strip()
        if normal:
            return normal
        return _FINAL_FALLBACK
