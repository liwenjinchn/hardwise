"""Tool-payload interpretation helpers for deterministic fake responses."""

from __future__ import annotations

from typing import Any

from hardwise.agent.runner import ToolCallTrace
from hardwise.guards.refdes import sanitize_text
from hardwise.report.ui_terms import check_label, validation_summary_label
from hardwise.validation.project_index import ProjectValidationRow
from hardwise.workbench.context import WorkbenchContext
from hardwise.workbench.chat_fake_parsing import _localized, _wants_english


def _summarize_component_context_payload(question: str, payload: dict[str, Any]) -> str:
    status = str(payload.get("status") or "")
    component = payload.get("component") if isinstance(payload.get("component"), dict) else {}
    refdes = str(component.get("refdes") or payload.get("refdes") or "")
    if status == "not_found":
        matches = payload.get("closest_matches")
        suggestions = ", ".join(matches[:3]) if isinstance(matches, list) else ""
        return _localized(
            question,
            f"I could not find {refdes}. Closest matches: {suggestions}.",
            f"我没有在当前设计里找到 {refdes}。最接近的是: {suggestions}。",
        )

    value = str(component.get("value") or component.get("part_number") or "")
    validation = str(payload.get("validation_status") or "-")
    pins = payload.get("pins") if isinstance(payload.get("pins"), list) else []
    pin_text = _format_pin_nets(pins[:8], english=_wants_english(question))
    neighbors = payload.get("neighbors") if isinstance(payload.get("neighbors"), list) else []
    neighbor_text = _format_neighbor_nets(neighbors[:4], english=_wants_english(question))
    if _wants_english(question):
        return (
            f"{refdes} ({value}) is from parsed Allegro/PST topology; validation status is {validation}. "
            f"Pin nets: {pin_text}. Neighbor nets: {neighbor_text}."
        )
    return (
        f"{refdes}（{value}）来自已解析的 Allegro/PST 原理图拓扑，验证状态是 {validation}。"
        f"引脚网络: {pin_text}。相邻网络: {neighbor_text}。"
    )


def _summarize_net_context_payload(question: str, payload: dict[str, Any]) -> str:
    status = str(payload.get("status") or "")
    net_name = str(payload.get("net_name") or "")
    if status == "not_found":
        matches = payload.get("closest_matches")
        suggestions = ", ".join(matches[:3]) if isinstance(matches, list) else ""
        return _localized(
            question,
            f"I could not find net {net_name}. Closest matches: {suggestions}.",
            f"我没有在当前 netlist 里找到网络 {net_name}。最接近的是: {suggestions}。",
        )
    members = payload.get("members") if isinstance(payload.get("members"), list) else []
    member_text = _format_members(members[:8])
    count = int(payload.get("member_count") or len(members))
    return _localized(
        question,
        f"Net {net_name} has {count} parsed member pins. Sample: {member_text}.",
        f"网络 {net_name} 有 {count} 个已解析成员引脚。样例: {member_text}。",
    )


def _summarize_net_search_payload(question: str, payload: dict[str, Any]) -> str:
    query = str(payload.get("query") or "")
    hits = payload.get("hits") if isinstance(payload.get("hits"), list) else []
    if not hits:
        matches = payload.get("closest_matches")
        suggestions = ", ".join(matches[:3]) if isinstance(matches, list) else ""
        return _localized(
            question,
            f"No parsed net names matched {query}. Closest matches: {suggestions}.",
            f"没有解析到匹配 {query} 的网络名。最接近的是: {suggestions}。",
        )
    rendered = []
    for hit in hits[:5]:
        if not isinstance(hit, dict):
            continue
        sample = _format_members(
            hit.get("sample_members") if isinstance(hit.get("sample_members"), list) else []
        )
        rendered.append(f"{hit.get('net_name')}({hit.get('member_count')}): {sample}")
    joined = "; ".join(rendered)
    return _localized(
        question,
        f"Parsed net search for {query} returned: {joined}.",
        f"按已解析 netlist 搜索 {query}，命中: {joined}。",
    )


def _summarize_topology_payload(question: str, payload: dict[str, Any]) -> str:
    totals = (
        payload.get("validation_totals")
        if isinstance(payload.get("validation_totals"), dict)
        else {}
    )
    power = _format_net_hits(
        payload.get("power_like_nets") if isinstance(payload.get("power_like_nets"), list) else []
    )
    interface = _format_net_hits(
        payload.get("interface_like_nets")
        if isinstance(payload.get("interface_like_nets"), list)
        else []
    )
    control = _format_net_hits(
        payload.get("control_like_nets")
        if isinstance(payload.get("control_like_nets"), list)
        else []
    )
    gaps = (
        payload.get("profile_gap_groups")
        if isinstance(payload.get("profile_gap_groups"), list)
        else []
    )
    first_gap = gaps[0] if gaps and isinstance(gaps[0], dict) else {}
    if _wants_english(question):
        return (
            "Topology summary is schematic/netlist-only: "
            f"{payload.get('component_count')} components, {payload.get('net_count')} nets, "
            f"validated={payload.get('validated_count')}, manual={payload.get('manual_count')}, "
            f"PASS/WARN/ERROR={totals.get('PASS', 0)}/{totals.get('WARN', 0)}/{totals.get('ERROR', 0)}. "
            f"Power-like nets: {power}. Interface-like nets: {interface}. Control-like nets: {control}. "
            f"First profile gap: {first_gap.get('identity', '-')} ({first_gap.get('refdes_count', 0)} refs)."
        )
    return (
        "拓扑摘要只基于解析后的原理图/netlist："
        f"{payload.get('component_count')} 个器件，{payload.get('net_count')} 条网络，"
        f"已验证 {payload.get('validated_count')} 个，待人工补档案 {payload.get('manual_count')} 个，"
        f"PASS/WARN/ERROR={totals.get('PASS', 0)}/{totals.get('WARN', 0)}/{totals.get('ERROR', 0)}。"
        f"电源类网络: {power}。接口类网络: {interface}。控制类网络: {control}。"
        f"首个器件档案缺口: {first_gap.get('identity', '-')}（{first_gap.get('refdes_count', 0)} 个位号）。"
    )


def _format_pin_nets(pins: list[Any], *, english: bool) -> str:
    rendered = []
    for pin in pins:
        if isinstance(pin, dict):
            rendered.append(
                f"{pin.get('pin_number')}/{pin.get('pin_name') or '-'}->{pin.get('net') or '-'}"
            )
    if not rendered:
        return "none" if english else "无"
    return ", ".join(rendered)


def _format_neighbor_nets(neighbors: list[Any], *, english: bool) -> str:
    rendered = []
    for net in neighbors:
        if not isinstance(net, dict):
            continue
        members = net.get("members") if isinstance(net.get("members"), list) else []
        rendered.append(f"{net.get('net_name')}[{_format_members(members[:4])}]")
    if not rendered:
        return "none" if english else "无"
    return "; ".join(rendered)


def _format_members(members: list[Any]) -> str:
    rendered = []
    for member in members:
        if isinstance(member, dict):
            rendered.append(f"{member.get('refdes')}.{member.get('pin_number')}")
    return ", ".join(rendered) if rendered else "-"


def _format_net_hits(hits: list[Any]) -> str:
    rendered = []
    for hit in hits[:5]:
        if isinstance(hit, dict):
            rendered.append(f"{hit.get('net_name')}({hit.get('member_count')})")
    return ", ".join(rendered) if rendered else "-"


def _important_checks(checks: list[Any], *, localized: bool = False) -> list[str]:
    rendered: list[str] = []
    for status in ("ERROR", "WARN"):
        for check in checks:
            if not isinstance(check, dict) or check.get("status") != status:
                continue
            name = str(check.get("check") or "check")
            summary = str(check.get("summary") or "")
            if localized:
                name = check_label(name)
            if localized:
                summary = validation_summary_label(summary)
            rendered.append(f"{name}: {summary}")
    return rendered


def _evidence_from_checks(checks: list[Any]) -> list[str]:
    evidence: list[str] = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        raw = check.get("evidence")
        if isinstance(raw, list):
            for item in raw:
                token = str(item)
                if token and token not in evidence:
                    evidence.append(token)
    return evidence


def _row_evidence(row: ProjectValidationRow | None) -> list[str]:
    if row is None or row.validation is None:
        return []
    checks = [
        *[
            {"status": item.status, "evidence": item.evidence}
            for item in row.validation.pin_results
        ],
        *[
            {"status": item.status, "evidence": item.evidence}
            for item in row.validation.component_checks
        ],
    ]
    return _evidence_from_checks(checks)


def _trace_refdes(trace: ToolCallTrace) -> str | None:
    value = trace.input.get("refdes")
    return value if isinstance(value, str) and "?" not in value else None


def _sanitize_chat_copy(text: str, context: WorkbenchContext) -> str:
    clean, _wrapped = sanitize_text(text, context.registry)
    return clean
