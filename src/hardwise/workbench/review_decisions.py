"""Backend-owned reviewer decisions that never mutate validator truth."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from threading import RLock
from typing import Literal, TypeVar

from pydantic import BaseModel, Field, field_validator

ReviewDecisionStatus = Literal["open", "accepted", "waived", "resolved"]


class ReviewDecisionView(BaseModel):
    """One human workflow decision keyed by a stable finding key."""

    stable_key: str
    status: ReviewDecisionStatus
    reason: str
    updated_at: str


class ReviewDecisionRequest(BaseModel):
    """Mutation request used by the local workbench API."""

    stable_keys: list[str] = Field(min_length=1)
    status: ReviewDecisionStatus
    reason: str = ""

    @field_validator("stable_keys")
    @classmethod
    def unique_nonempty_keys(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("at least one stable finding key is required")
        return list(dict.fromkeys(cleaned))

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return value.strip()

    def require_reason(self) -> None:
        if self.status != "open" and not self.reason:
            raise ValueError(f"reason is required when review status is {self.status}")


class ReviewDecisionSummary(BaseModel):
    """Workflow counts kept separate from electrical task counts."""

    total_tasks: int
    open: int
    accepted: int
    waived: int
    resolved: int
    stale_removed_on_rerun: int = 0


TaskModel = TypeVar("TaskModel")


class ReviewDecisionStore:
    """Thread-safe in-memory decision store for one active imported project."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._items: dict[str, ReviewDecisionView] = {}
        self._stale_removed_on_rerun = 0

    def update(
        self,
        *,
        known_keys: Iterable[str],
        request: ReviewDecisionRequest,
    ) -> list[ReviewDecisionView]:
        """Apply a reviewer decision after validating every requested key."""

        request.require_reason()
        known = set(known_keys)
        unknown = [key for key in request.stable_keys if key not in known]
        if unknown:
            raise KeyError(", ".join(unknown))
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._lock:
            if request.status == "open":
                for key in request.stable_keys:
                    self._items.pop(key, None)
                return []
            updated = [
                ReviewDecisionView(
                    stable_key=key,
                    status=request.status,
                    reason=request.reason,
                    updated_at=now,
                )
                for key in request.stable_keys
            ]
            for item in updated:
                self._items[item.stable_key] = item
            return updated

    def reset(self) -> None:
        """Clear decisions when a different project import becomes active."""

        with self._lock:
            self._items.clear()
            self._stale_removed_on_rerun = 0

    def reconcile(self, known_keys: Iterable[str]) -> int:
        """Drop decisions whose stable finding disappeared after a real re-run."""

        known = set(known_keys)
        with self._lock:
            stale = [key for key in self._items if key not in known]
            for key in stale:
                self._items.pop(key, None)
            self._stale_removed_on_rerun = len(stale)
            return len(stale)

    def apply(self, tasks: Sequence[TaskModel]) -> list[TaskModel]:
        """Return task copies enriched with workflow decisions."""

        with self._lock:
            decisions = dict(self._items)
        return [
            task.model_copy(update={"review_decision": decisions.get(task.stable_key)})
            for task in tasks
        ]

    def summary(self, stable_keys: Sequence[str]) -> ReviewDecisionSummary:
        """Summarize decision state over the current raw task set."""

        with self._lock:
            items = dict(self._items)
            stale_removed = self._stale_removed_on_rerun
        statuses = [items[key].status if key in items else "open" for key in stable_keys]
        return ReviewDecisionSummary(
            total_tasks=len(stable_keys),
            open=statuses.count("open"),
            accepted=statuses.count("accepted"),
            waived=statuses.count("waived"),
            resolved=statuses.count("resolved"),
            stale_removed_on_rerun=stale_removed,
        )
