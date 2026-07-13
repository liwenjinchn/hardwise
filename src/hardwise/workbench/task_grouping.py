"""Reviewer-facing task consolidation with raw-task audit preservation."""

from __future__ import annotations

from collections import defaultdict

from hardwise.bom.types import sort_refdes_key
from hardwise.workbench.projection_common import _status_rank
from hardwise.workbench.view_contracts import ReviewTask, ReviewTaskGroup


def build_review_task_groups(context, tasks: list[ReviewTask]) -> list[ReviewTaskGroup]:
    """Group repeated BOM/check tasks and attach derived uncertainty to roots."""

    task_by_id = {task.id: task for task in tasks}
    root_for = {task.id: task_by_id.get(task.derived_from_task_id, task) for task in tasks}
    buckets: dict[tuple[str, str], list[ReviewTask]] = defaultdict(list)
    for task in tasks:
        root = root_for[task.id]
        identity = _bom_identity(context, root.refdes)
        check = root.check or root.kind
        buckets[(identity, check)].append(task)

    groups: list[ReviewTaskGroup] = []
    for index, ((identity, check), grouped) in enumerate(buckets.items(), start=1):
        roots = [task for task in grouped if task.derived_from_task_id is None]
        primary = min(roots or grouped, key=lambda item: _status_rank(item.status_group))
        affected = sorted({task.refdes for task in grouped}, key=sort_refdes_key)
        root_refdes = sorted({task.refdes for task in roots}, key=sort_refdes_key)
        raw_keys = list(dict.fromkeys(task.stable_key for task in grouped))
        title = primary.title
        if len(root_refdes) > 1:
            title = f"{title}（{len(root_refdes)} 个同类器件）"
        stable_key = f"group|{identity}|{check}"
        groups.append(
            ReviewTaskGroup(
                id=f"G-{index:03d}",
                stable_key=stable_key,
                title=title,
                status_group=primary.status_group,
                trust_tier=primary.trust_tier,
                axis=(
                    "evidence"
                    if primary.kind in {"document_candidate", "manual_gap", "risk_hint"}
                    else "electrical"
                ),
                identity=identity,
                check=primary.check,
                affected_refdes=affected,
                task_ids=[task.id for task in grouped],
                stable_keys=raw_keys,
                raw_task_count=len(grouped),
                derived_task_count=sum(task.derived_from_task_id is not None for task in grouped),
                recommended_action=primary.recommended_action,
            )
        )
    groups.sort(
        key=lambda item: (
            _status_rank(item.status_group),
            sort_refdes_key(item.affected_refdes[0]),
            item.title,
        )
    )
    return [
        item.model_copy(update={"id": f"G-{index:03d}"}) for index, item in enumerate(groups, 1)
    ]


def _bom_identity(context, refdes: str) -> str:
    row = context.bom_report.rows_by_refdes.get(refdes)
    if row is None:
        return refdes
    manufacturer = (row.manufacturer or "unknown").strip().casefold()
    part_number = (row.part_number or row.value or refdes).strip().casefold()
    return f"{manufacturer}|{part_number}"
