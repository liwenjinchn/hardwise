"""Prompt parsing and intent routing for the deterministic fake model."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from hardwise.workbench.chat_contracts import ChatMessage


class _FakeUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class _FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class _FakeToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]
    type: str = "tool_use"


@dataclass
class _FakeResponse:
    content: list[Any]
    usage: _FakeUsage = field(default_factory=_FakeUsage)


def _runner_prompt(
    question: str,
    selected_refdes: str | None,
    history: list[ChatMessage] | None = None,
) -> str:
    selected = selected_refdes or "(none)"
    history_block = _history_prompt_block(history or [])
    if history_block:
        return (
            f"Selected refdes: {selected}\n"
            f"Recent conversation:\n{history_block}\n"
            f"Question: {question.strip()}"
        )
    return f"Selected refdes: {selected}\nQuestion: {question.strip()}"


def _history_prompt_block(history: list[ChatMessage]) -> str:
    recent = [
        item
        for item in history[-6:]
        if item.content.strip() and item.content.strip() != "(stopped: iteration cap reached)"
    ]
    lines: list[str] = []
    for item in recent:
        content = re.sub(r"\s+", " ", item.content.strip())
        if len(content) > 500:
            content = content[:497].rstrip() + "..."
        lines.append(f"- {item.role}: {content}")
    return "\n".join(lines)


def _parse_runner_prompt(content: str) -> tuple[str, str]:
    selected_match = re.search(r"Selected refdes:\s*(.+)", content)
    question_match = re.search(r"Question:\s*(.*)", content, re.DOTALL)
    selected = selected_match.group(1).strip() if selected_match else ""
    question = question_match.group(1).strip() if question_match else content.strip()
    return question, "" if selected == "(none)" else selected


def _choose_refdes(question: str, selected: str) -> str:
    tokens = re.findall(r"\b[A-Z]{1,3}\d{1,4}\b", question.upper())
    for token in tokens:
        if token != selected:
            return token
    if tokens:
        return tokens[0]
    return selected or "U1"


def _tool_payloads(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for block in blocks:
        if block.get("type") != "tool_result":
            continue
        content = block.get("content")
        if not isinstance(content, str):
            continue
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def _search_payload(payloads: list[dict[str, Any]]) -> dict[str, Any] | None:
    for payload in payloads:
        if "hits" in payload and "query" in payload:
            return payload
    return None


def _validation_payload(payloads: list[dict[str, Any]]) -> dict[str, Any] | None:
    validation_statuses = {"validated", "not_found", "no_profile", "not_configured"}
    for payload in payloads:
        status = payload.get("status")
        if isinstance(status, str) and status in validation_statuses:
            return payload
    return None


def _document_payload(payloads: list[dict[str, Any]]) -> dict[str, Any] | None:
    document_statuses = {
        "matched",
        "no_result",
        "ambiguous",
        "manual_needed",
        "not_found",
        "not_configured",
        "configured",
    }
    for payload in payloads:
        status = payload.get("status")
        if isinstance(status, str) and status in document_statuses:
            if "document_index_file" in payload or "identity" in payload or "groups" in payload:
                return payload
            reason = str(payload.get("reason") or "")
            if status == "not_configured" and "document index" in reason.lower():
                return payload
    return None


def _evidence_locator_payload(payloads: list[dict[str, Any]]) -> dict[str, Any] | None:
    for payload in payloads:
        if "normalized_topic" in payload and "hits" in payload and "profile_part_number" in payload:
            return payload
    return None


def _topology_payload(payloads: list[dict[str, Any]]) -> dict[str, Any] | None:
    topology_statuses = {"found", "not_found", "not_configured", "summarized"}
    for payload in payloads:
        status = payload.get("status")
        if isinstance(status, str) and status in topology_statuses:
            if "component" in payload or "net_name" in payload or "component_count" in payload:
                return payload
            reason = str(payload.get("reason") or "")
            if status == "not_configured" and "topology" in reason.lower():
                return payload
    for payload in payloads:
        if "hits" in payload and "query" in payload:
            if "closest_matches" in payload or "sample_members" in json.dumps(payload):
                return payload
    return None


def _topology_tool_uses(question: str, refdes: str, turn: int) -> list[Any]:
    if _needs_project_topology(question):
        return [
            _FakeToolUseBlock(
                id=f"hw_fake_{turn}_topology_summary",
                name="summarize_project_topology",
                input={"component_limit": 10, "net_limit": 10, "gap_limit": 8},
            )
        ]
    if _needs_component_topology(question):
        return [
            _FakeToolUseBlock(
                id=f"hw_fake_{turn}_component_context",
                name="get_component_context",
                input={"refdes": refdes, "neighbor_limit": 24},
            )
        ]
    if _needs_net_topology_search(question):
        return [
            _FakeToolUseBlock(
                id=f"hw_fake_{turn}_net_search",
                name="search_nets",
                input={"query": _net_search_query(question), "limit": 12, "member_sample_limit": 6},
            )
        ]
    return []


def _needs_project_topology(question: str) -> bool:
    text = question.lower()
    needles = (
        "project topology",
        "board topology",
        "topology summary",
        "schematic overview",
        "project overview",
        "这张板",
        "整板",
        "项目概览",
        "原理图概览",
        "拓扑概览",
        "待补 profile",
        "profile 缺口",
    )
    return any(needle in text for needle in needles)


def _needs_component_topology(question: str) -> bool:
    text = question.lower()
    if not re.search(r"\b[A-Z]{1,3}\d{1,4}\b", question.upper()):
        return False
    needles = (
        "connected",
        "connects",
        "connection",
        "topology",
        "netlist",
        "接了哪些",
        "连接",
        "相连",
        "接到",
        "网络",
        "拓扑",
    )
    return any(needle in text for needle in needles)


def _needs_net_topology_search(question: str) -> bool:
    text = question.lower()
    if re.search(r"\b[A-Z]{1,3}\d{1,4}\b", question.upper()):
        return False
    topology_words = ("net", "network", "网络", "相关", "有哪些", "搜索", "查找")
    net_tokens = (
        "reset",
        "nrst",
        "rst",
        "boot",
        "vin",
        "3v3",
        "sda",
        "scl",
        "swd",
        "swclk",
        "swdio",
        "pwm",
    )
    return any(word in text for word in topology_words) and any(
        token in text for token in net_tokens
    )


def _net_search_query(question: str) -> str:
    known = (
        "RESET",
        "NRST",
        "RST",
        "BOOT",
        "VIN",
        "3V3",
        "SDA",
        "SCL",
        "SWD",
        "SWCLK",
        "SWDIO",
        "PWM",
    )
    upper = question.upper()
    found = [token for token in known if token in upper]
    return " ".join(found) if found else question


def _needs_document_coverage(question: str) -> bool:
    text = question.lower()
    if any(
        term in text
        for term in ("absolute maximum", "abs max", "rating", "rated", "绝对最大", "额定")
    ):
        return False
    needles = (
        "public document",
        "document coverage",
        "document gap",
        "datasheet gap",
        "has datasheet",
        "have datasheet",
        "matched document",
        "公开资料",
        "资料覆盖",
        "资料缺口",
        "文档缺口",
        "datasheet 缺口",
        "缺 datasheet",
        "有没有 datasheet",
        "有没有数据手册",
        "有没有资料",
        "匹配到公开",
    )
    return any(needle in text for needle in needles)


def _needs_document_summary(question: str) -> bool:
    text = question.lower()
    return any(term in text for term in ("gap", "coverage", "缺口", "哪些", "summary", "summarize"))


def _needs_evidence_locator(question: str) -> bool:
    if _is_evidence_chain_smoke(question):
        return False
    text = question.lower()
    exact_evidence_words = (
        "evidence",
        "locator",
        "where",
        "which page",
        "section",
        "table",
        "证据",
        "第几页",
        "哪一页",
        "出处",
        "定位",
    )
    exact_topics = (
        "absolute maximum",
        "abs max",
        "绝对最大",
        "耐压",
        "enable",
        "on/off",
        "boot0",
        "boot",
        "nrst",
        "reset",
        "swdio",
        "swclk",
        "swd",
        "pin function",
        "pinout",
        "引脚功能",
        "自举",
        "bootstrap",
        "decoupling",
        "去耦",
    )
    return any(word in text for word in exact_evidence_words) and any(
        topic in text for topic in exact_topics
    )


def _locator_topic(question: str) -> str:
    text = question.lower()
    if any(term in text for term in ("absolute maximum", "abs max", "绝对最大", "耐压", "额定")):
        return "abs_max"
    if any(term in text for term in ("enable", "on/off", "使能")):
        return "enable"
    if any(term in text for term in ("boot0", "boot", "启动")):
        return "boot"
    if any(term in text for term in ("nrst", "reset", "rst", "复位")):
        return "reset"
    if any(term in text for term in ("swdio", "swclk", "swd", "debug", "调试")):
        return "debug"
    if any(term in text for term in ("bootstrap", "自举")):
        return "bootstrap"
    if any(term in text for term in ("decoupling", "bypass", "去耦", "旁路")):
        return "decoupling"
    if any(term in text for term in ("pin function", "pinout", "引脚功能", "管脚功能")):
        return "pin_function"
    if any(
        term in text for term in ("recommended", "application", "topology", "推荐", "应用", "拓扑")
    ):
        return "recommended"
    return "all"


def _needs_datasheet_search(question: str) -> bool:
    text = question.lower()
    needles = (
        "datasheet",
        "data sheet",
        "absolute maximum",
        "abs max",
        "rating",
        "rated",
        "规格书",
        "数据手册",
        "手册",
        "绝对最大",
        "额定",
    )
    return any(needle in text for needle in needles)


def _is_evidence_chain_smoke(question: str) -> bool:
    text = question.lower()
    return "evidence-chain smoke" in text or "证据链" in question


def _wants_english(text: str) -> bool:
    return not re.search(r"[\u4e00-\u9fff]", text)


def _localized(question: str, english: str, chinese: str) -> str:
    return english if _wants_english(question) else chinese
