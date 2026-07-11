"""Lease-aware lifecycle management for mutable workbench contexts."""

from __future__ import annotations

import logging
import shutil
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Callable, Iterator

from hardwise.workbench.context import WorkbenchContext, close_workbench_context

LOGGER = logging.getLogger(__name__)


@dataclass
class _ManagedContext:
    context: WorkbenchContext
    import_dir: Path | None = None
    leases: int = 0
    retired: bool = False
    closed: bool = False


class WorkbenchContextManager:
    """Atomically swap contexts without closing resources held by requests."""

    def __init__(
        self,
        context: WorkbenchContext,
        *,
        close_context: Callable[[WorkbenchContext], None] = close_workbench_context,
        remove_dir: Callable[[Path], None] | None = None,
    ) -> None:
        self._lock = RLock()
        self._close_context = close_context
        self._remove_dir = remove_dir or self._remove_import_dir
        self._current = _ManagedContext(context=context)
        self._retired: list[_ManagedContext] = []
        self._shutdown = False
        self._leased: ContextVar[_ManagedContext | None] = ContextVar(
            "hardwise_workbench_context", default=None
        )

    def __getitem__(self, key: str) -> WorkbenchContext:
        """Keep the former ``{"value": context}`` app-state access compatible."""

        if key != "value":
            raise KeyError(key)
        return self.current

    @property
    def current(self) -> WorkbenchContext:
        leased = self._leased.get()
        if leased is not None:
            return leased.context
        with self._lock:
            return self._current.context

    @contextmanager
    def lease(self) -> Iterator[WorkbenchContext]:
        """Hold a stable request snapshot until the caller finishes using it."""

        with self._lock:
            if self._shutdown:
                raise RuntimeError("workbench context manager is shut down")
            managed = self._leased.get() or self._current
            managed.leases += 1
        token = self._leased.set(managed)
        try:
            yield managed.context
        finally:
            self._leased.reset(token)
            with self._lock:
                managed.leases -= 1
                self._close_if_ready(managed)

    def swap(self, context: WorkbenchContext, *, import_dir: Path | None = None) -> None:
        """Publish a new context and retire the previous one atomically."""

        with self._lock:
            if self._shutdown:
                raise RuntimeError("workbench context manager is shut down")
            previous = self._current
            previous.retired = True
            self._retired.append(previous)
            self._current = _ManagedContext(context=context, import_dir=import_dir)
            try:
                self._close_if_ready(previous)
            except Exception:
                # The new context is already published and owned by this
                # manager. A retired-resource cleanup failure must not make the
                # caller close the new active context as if publication failed.
                LOGGER.exception("retired workbench context cleanup failed after swap")

    def shutdown(self) -> None:
        """Retire every context and close each one after its final lease exits."""

        with self._lock:
            if self._shutdown:
                return
            self._shutdown = True
            self._current.retired = True
            managed_contexts = [*self._retired, self._current]
            errors: list[Exception] = []
            for managed in managed_contexts:
                try:
                    self._close_if_ready(managed)
                except Exception as exc:
                    errors.append(exc)
            if errors:
                raise errors[0]

    def _close_if_ready(self, managed: _ManagedContext) -> None:
        if managed.retired and managed.leases == 0:
            self._close(managed)

    def _close(self, managed: _ManagedContext) -> None:
        if managed.closed:
            return
        managed.closed = True
        try:
            self._close_context(managed.context)
        finally:
            try:
                if managed.import_dir is not None:
                    self._remove_dir(managed.import_dir)
            finally:
                self._retired = [item for item in self._retired if item is not managed]

    @staticmethod
    def _remove_import_dir(path: Path) -> None:
        shutil.rmtree(path, ignore_errors=True)
