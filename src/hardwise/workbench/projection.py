"""Context-owned indexes for repeated workbench view projection."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from threading import Lock
from types import MappingProxyType
from typing import TYPE_CHECKING

from hardwise.bom.types import sort_refdes_key
from hardwise.ir.types import Component
from hardwise.validation.component_groups import ProjectComponentGroup
from hardwise.validation.project_index import ProjectValidationRow
from hardwise.validation.risk_hints import RiskHint

if TYPE_CHECKING:
    from hardwise.workbench.context import WorkbenchContext
    from hardwise.workbench.view_contracts import ReviewTask


@dataclass(slots=True)
class WorkbenchProjectionIndex:
    """Stable context indexes plus the lazily built review-task projection."""

    rows_by_refdes: Mapping[str, ProjectValidationRow]
    document_group_by_refdes: Mapping[str, ProjectComponentGroup]
    risk_hints_by_refdes: Mapping[str, tuple[RiskHint, ...]]
    risk_hint_counts: Mapping[str, int]
    components: tuple[Component, ...]
    validated_count: int
    manual_count: int
    validation_totals: Mapping[str, int]
    _review_tasks: tuple[ReviewTask, ...] | None = field(
        default=None,
        init=False,
        repr=False,
    )
    _tasks_by_refdes: Mapping[str, tuple[ReviewTask, ...]] | None = field(
        default=None,
        init=False,
        repr=False,
    )
    _review_task_lock: Lock = field(
        default_factory=Lock,
        init=False,
        repr=False,
        compare=False,
    )

    @classmethod
    def from_context(cls, context: WorkbenchContext) -> WorkbenchProjectionIndex:
        """Index immutable-by-contract inputs exactly once for one context."""

        rows_by_refdes = {row.refdes: row for row in context.index.rows}
        document_group_by_refdes: dict[str, ProjectComponentGroup] = {}
        for group in context.index.component_groups:
            for refdes in group.refdes:
                # Preserve the former ``next(...)`` behavior if malformed input
                # ever places one refdes in more than one group.
                document_group_by_refdes.setdefault(refdes, group)

        risk_hints_by_refdes: dict[str, list[RiskHint]] = {}
        for hint in context.risk_hints.accepted:
            risk_hints_by_refdes.setdefault(hint.refdes, []).append(hint)
        frozen_risk_hints = {refdes: tuple(hints) for refdes, hints in risk_hints_by_refdes.items()}

        totals = {"PASS": 0, "WARN": 0, "ERROR": 0}
        validated_count = 0
        for row in context.index.rows:
            if row.validation is None:
                continue
            validated_count += 1
            totals[row.validation.status] += 1

        return cls(
            rows_by_refdes=MappingProxyType(rows_by_refdes),
            document_group_by_refdes=MappingProxyType(document_group_by_refdes),
            risk_hints_by_refdes=MappingProxyType(frozen_risk_hints),
            risk_hint_counts=MappingProxyType(
                {refdes: len(hints) for refdes, hints in frozen_risk_hints.items()}
            ),
            components=tuple(
                sorted(
                    context.design.components.values(),
                    key=lambda component: sort_refdes_key(component.refdes),
                )
            ),
            validated_count=validated_count,
            manual_count=len(context.index.rows) - validated_count,
            validation_totals=MappingProxyType(totals),
        )

    def review_task_projection(
        self,
        builder: Callable[[], list[ReviewTask]],
    ) -> tuple[tuple[ReviewTask, ...], Mapping[str, tuple[ReviewTask, ...]]]:
        """Return one thread-safe review-task build and its refdes index."""

        tasks = self._review_tasks
        tasks_by_refdes = self._tasks_by_refdes
        if tasks is not None and tasks_by_refdes is not None:
            return tasks, tasks_by_refdes

        with self._review_task_lock:
            tasks = self._review_tasks
            tasks_by_refdes = self._tasks_by_refdes
            if tasks is None or tasks_by_refdes is None:
                tasks = tuple(builder())
                grouped: dict[str, list[ReviewTask]] = {}
                for task in tasks:
                    grouped.setdefault(task.refdes, []).append(task)
                tasks_by_refdes = MappingProxyType(
                    {refdes: tuple(items) for refdes, items in grouped.items()}
                )
                self._tasks_by_refdes = tasks_by_refdes
                self._review_tasks = tasks

        return tasks, tasks_by_refdes
