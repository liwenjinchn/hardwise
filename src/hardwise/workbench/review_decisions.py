"""Backend-owned reviewer decisions that never mutate validator truth."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import TypeVar
from uuid import uuid4

from hardwise.workbench.decision_journal import DecisionJournal, ReviewConflictError
from hardwise.workbench.run_provenance import load_run_provenance

# Retain the public imports used by existing API/CLI callers.
from hardwise.workbench.review_decision_contracts import (
    ReviewDecisionStatus as ReviewDecisionStatus,
    ReviewDecisionView,
    ReviewDecisionRequest,
    ReviewDecisionSummary,
)


TaskModel = TypeVar("TaskModel")


class ReviewDecisionStore:
    """Atomic reviewer state with optional durable append-only history."""

    def __init__(self, path: Path | None = None) -> None:
        self._lock = RLock()
        self._items: dict[str, ReviewDecisionView] = {}
        self._stale_removed_on_rerun = 0
        self._journal = DecisionJournal(path) if path else None
        self._history: list[dict] = []
        self._runs: dict[str, dict] = {}
        self._revision = 0
        self._project = "memory"
        self._run_id = str(uuid4())
        self._fingerprints: dict[str, str] = {}

    def checkpoint(self):
        with self._lock:
            return (
                self._project,
                self._revision,
                self._run_id,
                dict(self._items),
                dict(self._fingerprints),
                self._stale_removed_on_rerun,
                len(self._history),
                set(self._runs),
            )

    def restore_checkpoint(self, checkpoint):
        """Restore the previous active namespace after failed project publication."""
        with self._lock:
            (
                self._project,
                self._revision,
                self._run_id,
                self._items,
                self._fingerprints,
                self._stale_removed_on_rerun,
                length,
                runs,
            ) = checkpoint
            del self._history[length:]
            self._runs = {key: value for key, value in self._runs.items() if key in runs}

    def _save(self, items, events, *, run=None, run_id=None):
        rid = run_id or self._run_id
        if self._journal:
            self._revision = self._journal.save(
                self._project,
                rid,
                {k: v.model_dump(mode="json") for k, v in items.items()},
                events,
                run,
                expected_revision=self._revision,
            )
        else:
            for event in events:
                self._history.append(
                    dict(id=len(self._history) + 1, run_id=rid, project=self._project, **event)
                )
        if run is not None and self._journal is None:
            self._runs[rid] = {
                "project": self._project,
                "created_at": run["created_at"],
                "provenance": run.get("provenance"),
            }
        self._items = items

    def begin_run(
        self,
        project: str,
        fingerprints: dict[str, str],
        *,
        tasks: list[dict] | None = None,
        provenance: dict | None = None,
    ) -> int:
        """Restore a project and invalidate changed facts without discarding reasons."""
        with self._lock:
            previous_project, previous_revision = self._project, self._revision
            old = self._items
            if project != self._project:
                data, self._revision = self._journal.load(project) if self._journal else ({}, 0)
                old = {k: ReviewDecisionView.model_validate(v) for k, v in data.items()}
            items, events, missing = dict(old), [], 0
            for key, item in old.items():
                if key not in fingerprints:
                    items.pop(key)
                    missing += 1
                    events.append(self._event("disappeared", key, item))
                elif (
                    item.status == "needs_review"
                    or not item.fingerprint
                    or item.fingerprint != fingerprints[key]
                ):
                    updated = self._review_needed(item, fingerprints[key])
                    items[key] = updated
                    if (
                        item.status != "needs_review"
                        or item.current_fingerprint != fingerprints[key]
                    ):
                        events.append(self._event("inputs_changed", key, updated))
            self._project = project
            rid = str(uuid4())
            try:
                self._save(
                    items,
                    events,
                    run={
                        "fingerprints": fingerprints,
                        "provenance": provenance,
                        "tasks": tasks or [],
                        "created_at": self._now(),
                    },
                    run_id=rid,
                )
            except Exception:
                self._project, self._revision = previous_project, previous_revision
                raise
            self._run_id = rid
            self._fingerprints = dict(fingerprints)
            self._stale_removed_on_rerun = missing
            return missing

    def update(
        self,
        *,
        known_keys: Iterable[str],
        request: ReviewDecisionRequest,
        fingerprints: dict[str, str] | None = None,
    ) -> list[ReviewDecisionView]:
        request.require_reason()
        with self._lock:
            if self._journal and request.expected_run_id is None:
                raise ValueError("current run identifier is required for durable review decisions")
            if request.expected_run_id is not None and request.expected_run_id != self._run_id:
                raise ReviewConflictError("review run changed; reload before deciding")
            known = set(known_keys)
            unknown = [key for key in request.stable_keys if key not in known]
            if unknown:
                raise KeyError(", ".join(unknown))
            fps = fingerprints or {}
            if any(
                self._fingerprints and fps.get(k) != self._fingerprints.get(k)
                for k in request.stable_keys
            ):
                raise ReviewConflictError(
                    "review inputs changed; reload the current run before deciding"
                )
            items, updated, events = dict(self._items), [], []
            for key in request.stable_keys:
                view = ReviewDecisionView(
                    stable_key=key,
                    status=request.status,
                    reason=request.reason,
                    updated_at=self._now(),
                    fingerprint=fps.get(key),
                    current_fingerprint=fps.get(key),
                )
                if request.status == "open":
                    items.pop(key, None)
                else:
                    items[key] = view
                    updated.append(view)
                events.append(self._event("human_decision", key, view))
            self._save(items, events)
            return updated

    @staticmethod
    def _review_needed(item, fingerprint):
        previous = item.previous_status if item.status == "needs_review" else item.status
        return item.model_copy(
            update={
                "status": "needs_review",
                "previous_status": previous,
                "current_fingerprint": fingerprint,
            }
        )

    def apply(
        self,
        tasks: Sequence[TaskModel],
        *,
        fingerprints: dict[str, str] | None = None,
        project: str | None = None,
    ) -> list[TaskModel]:
        with self._lock:
            decisions = dict(self._items) if project is None or project == self._project else {}
        output = []
        for task in tasks:
            item = decisions.get(task.stable_key)
            current = (fingerprints or {}).get(task.stable_key)
            if item and (
                not item.fingerprint or (fingerprints is not None and item.fingerprint != current)
            ):
                item = self._review_needed(item, current)
            output.append(task.model_copy(update={"review_decision": item}))
        return output

    def summary(
        self, stable_keys: Sequence[str], *, project: str | None = None
    ) -> ReviewDecisionSummary:
        with self._lock:
            selected_project = project or self._project
            items = self._items if selected_project == self._project else {}
            statuses = [items[k].status if k in items else "open" for k in stable_keys]
            return ReviewDecisionSummary(
                total_tasks=len(stable_keys),
                open=statuses.count("open"),
                accepted=statuses.count("accepted"),
                waived=statuses.count("waived"),
                resolved=statuses.count("resolved"),
                needs_review=statuses.count("needs_review"),
                stale_removed_on_rerun=self._stale_removed_on_rerun,
                storage="local_file" if self._journal else "memory",
                history_count=self._journal.history_count(selected_project)
                if self._journal
                else sum(e["project"] == selected_project for e in self._history),
                project_id=selected_project,
                run_id=self._run_id if selected_project == self._project else None,
            )

    def history(self, limit=100, offset=0):
        with self._lock:
            return (
                self._journal.history(self._project, limit, offset)
                if self._journal
                else [e for e in reversed(self._history) if e["project"] == self._project][
                    offset : offset + limit
                ]
            )

    def history_page(self, limit=100, offset=0, expected_project_id=None):
        with self._lock:
            if expected_project_id is not None and expected_project_id != self._project:
                raise ReviewConflictError("active project changed; reload before reading history")
            if self._journal:
                page = self._journal.history_page(self._project, limit, offset)
            else:
                events = [e for e in reversed(self._history) if e["project"] == self._project]
                page = {"events": events[offset : offset + limit], "total": len(events)}
            return dict(
                project_id=self._project, run_id=self._run_id, limit=limit, offset=offset, **page
            )

    def run_provenance(self, run_id, expected_project_id=None):
        with self._lock:
            if expected_project_id is not None and expected_project_id != self._project:
                raise ReviewConflictError(
                    "active project changed; reload before reading run provenance"
                )
            return load_run_provenance(self._journal, self._runs, self._project, run_id)

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")

    @classmethod
    def _event(cls, event, key, decision):
        return {
            "event": event,
            "stable_key": key,
            "created_at": cls._now(),
            "decision": decision.model_dump(mode="json"),
        }
