"""Render a single-file offline snapshot for the React workbench."""

from __future__ import annotations

import csv
import io
import json
import re
from html import escape
from pathlib import Path

from hardwise.bom.types import sort_refdes_key
from hardwise.workbench.chat import ChatResponse, build_snapshot_responses
from hardwise.workbench.context import WorkbenchContext
from hardwise.workbench.prep_packet import (
    build_project_review_prep_packet,
    render_project_review_prep_packet_markdown,
)
from hardwise.workbench.view_model import (
    ComponentMiss,
    build_component_detail,
    build_review_prep_packet,
    build_review_tasks,
    build_workbench_state,
    render_review_prep_packet_markdown,
)

STATIC_DIR = Path(__file__).parents[1] / "workbench" / "static"
SNAPSHOT_GLOBAL = "__HARDWISE_OFFLINE_SNAPSHOT__"


def render_spa_snapshot(
    context: WorkbenchContext,
    *,
    datasheet_search_enabled: bool = False,
) -> str:
    """Return a standalone SPA HTML file backed by baked workbench data."""

    state = build_workbench_state(
        context,
        datasheet_search_enabled=datasheet_search_enabled,
    )
    snapshot = {
        "schema_version": "hardwise.workbench.offline_snapshot.v1",
        "mode": "snapshot",
        "state": state.model_dump(mode="json"),
        "components": _component_details(context),
        "component_prep_markdown": _component_prep_markdown(context),
        "project_prep_markdown": render_project_review_prep_packet_markdown(
            build_project_review_prep_packet(context)
        ),
        "chat_responses": _chat_responses(context),
        "exports": {
            "json": json.dumps(state.model_dump(mode="json"), ensure_ascii=False, indent=2),
            "csv": _tasks_csv(context),
            "annotations": _annotations(context),
        },
    }
    return _inline_spa_shell(snapshot, project_name=context.project_name)


def _component_details(context: WorkbenchContext) -> dict[str, object]:
    details: dict[str, object] = {}
    for refdes in sorted(context.design.refdes_set, key=sort_refdes_key):
        detail = build_component_detail(context, refdes)
        if not isinstance(detail, ComponentMiss):
            details[refdes] = detail.model_dump(mode="json")
    return details


def _component_prep_markdown(context: WorkbenchContext) -> dict[str, str]:
    packets: dict[str, str] = {}
    for refdes in sorted(context.design.refdes_set, key=sort_refdes_key):
        packet = build_review_prep_packet(context, refdes)
        if not isinstance(packet, ComponentMiss):
            packets[refdes] = render_review_prep_packet_markdown(packet)
    return packets


def _chat_responses(context: WorkbenchContext) -> dict[str, object]:
    responses: dict[str, ChatResponse] = build_snapshot_responses(context)
    return {
        question: response.model_dump(mode="json")
        for question, response in responses.items()
    }


def _tasks_csv(context: WorkbenchContext) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "id",
            "refdes",
            "status_group",
            "trust_tier",
            "title",
            "recommended_action",
            "source_classes",
        ],
    )
    writer.writeheader()
    for task in build_review_tasks(context):
        writer.writerow(
            {
                "id": task.id,
                "refdes": task.refdes,
                "status_group": task.status_group,
                "trust_tier": task.trust_tier,
                "title": task.title,
                "recommended_action": task.recommended_action,
                "source_classes": ";".join(task.source_classes),
            }
        )
    return buffer.getvalue()


def _annotations(context: WorkbenchContext) -> str:
    lines = [
        "# Hardwise EDA annotation export",
        "# format: refdes,status_group,task_id,title,recommended_action",
    ]
    for task in build_review_tasks(context):
        lines.append(
            ",".join(
                [
                    _annotation_cell(task.refdes),
                    _annotation_cell(task.status_group),
                    _annotation_cell(task.id),
                    _annotation_cell(task.title),
                    _annotation_cell(task.recommended_action),
                ]
            )
        )
    return "\n".join(lines) + "\n"


def _annotation_cell(value: object) -> str:
    return str(value).replace("\n", " ").replace(",", "；")


def _inline_spa_shell(snapshot: dict[str, object], *, project_name: str) -> str:
    index_path = STATIC_DIR / "index.html"
    if not index_path.is_file():
        raise FileNotFoundError(f"built workbench static index not found: {index_path}")
    html = index_path.read_text(encoding="utf-8")
    html = re.sub(
        r"<title>.*?</title>",
        f"<title>Hardwise 离线工作台 - {escape(project_name)}</title>",
        html,
        flags=re.DOTALL,
    )
    html = _inline_stylesheet(html)
    html = _inline_script(html, snapshot)
    return html


def _inline_stylesheet(html: str) -> str:
    match = re.search(r'<link rel="stylesheet"[^>]+href="([^"]+)"[^>]*>', html)
    if match is None:
        raise ValueError("built workbench stylesheet link not found")
    href = match.group(1)
    css_path = STATIC_DIR / href.removeprefix("./")
    css = css_path.read_text(encoding="utf-8")
    return html.replace(match.group(0), f"<style>\n{css}\n</style>")


def _inline_script(html: str, snapshot: dict[str, object]) -> str:
    match = re.search(r'<script type="module"[^>]+src="([^"]+)"[^>]*></script>', html)
    if match is None:
        raise ValueError("built workbench script tag not found")
    src = match.group(1)
    js_path = STATIC_DIR / src.removeprefix("./")
    js = js_path.read_text(encoding="utf-8")
    snapshot_json = json.dumps(snapshot, ensure_ascii=False).replace("</", "<\\/")
    replacement = (
        "<script>\n"
        f"window.{SNAPSHOT_GLOBAL} = {snapshot_json};\n"
        "</script>\n"
        "<script type=\"module\">\n"
        f"{js}\n"
        "</script>"
    )
    return html.replace(match.group(0), replacement)
