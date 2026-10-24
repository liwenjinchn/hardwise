"""Overlay captured reviewer decisions consistently across offline report views."""

import json
from hardwise.workbench.prep_packet import (
    build_project_review_prep_packet,
    render_project_review_prep_packet_markdown,
)
from hardwise.workbench.view_model import (
    build_review_prep_packet,
    ComponentMiss,
    render_review_prep_packet_markdown,
)
from hardwise.workbench.server_io import _task_csv_response, _annotations_response


def attach_review_history(snapshot, context, state, history):
    if (history.project_id, history.run_id) != (
        state.review_decisions.project_id,
        state.review_decisions.run_id,
    ):
        raise ValueError("offline state and history belong to different projects/runs")
    decisions = {task.stable_key: task.review_decision for task in state.review_tasks}

    def apply(tasks):
        return [
            task.model_copy(update={"review_decision": decisions.get(task.stable_key)})
            for task in tasks
        ]

    snapshot["review_history"] = history.model_dump(mode="json")
    snapshot["exports"]["review_history"] = history.model_dump_json(indent=2)
    snapshot["exports"]["json"] = json.dumps(
        state.model_dump(mode="json"), ensure_ascii=False, indent=2
    )
    snapshot["exports"]["csv"] = bytes(
        _task_csv_response(context, tasks=state.review_tasks).body
    ).decode()
    snapshot["exports"]["annotations"] = bytes(
        _annotations_response(context, tasks=state.review_tasks).body
    ).decode()
    for refdes, detail in snapshot["components"].items():
        for task in detail["tasks"]:
            decision = decisions.get(task["stable_key"])
            task["review_decision"] = decision.model_dump(mode="json") if decision else None
        packet = build_review_prep_packet(context, refdes)
        if not isinstance(packet, ComponentMiss):
            packet.tasks = apply(packet.tasks)
            packet.component.tasks = apply(packet.component.tasks)
            snapshot["component_prep_markdown"][refdes] = render_review_prep_packet_markdown(packet)
    packet = build_project_review_prep_packet(context)
    packet.priority_tasks = apply(packet.priority_tasks)
    packet.review_decisions = state.review_decisions
    snapshot["project_prep_markdown"] = render_project_review_prep_packet_markdown(packet)
