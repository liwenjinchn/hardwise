"""Workbench topology tools for Allegro/PST Design facts.

These tools expose the existing ``Design`` component/pin/net graph to the
agent as bounded structured facts. They do not infer schematic modules, layout,
boardview geometry, PLM status, or datasheet facts.
"""

from __future__ import annotations

import difflib
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from hardwise.bom.types import sort_refdes_key
from hardwise.ir.types import Component, Design
from hardwise.validation.project_index import ProjectValidationIndex, ProjectValidationRow
from hardwise.validation.project_index import profile_gap_groups


POWER_NET_PATTERN = re.compile(r"(^|\b|[_+-])(VCC|VDD|VIN|VBAT|VBUS|GND|PGND|AGND|\+?\d+V\d*)", re.I)
INTERFACE_NET_PATTERN = re.compile(
    r"(SDA|SCL|SPI|MISO|MOSI|SCK|UART|TXD?|RXD?|CAN|USB|SWD|SWCLK|SWDIO)",
    re.I,
)
CONTROL_NET_PATTERN = re.compile(r"(RESET|RST|NRST|BOOT|EN|ENABLE|CLK|XTAL|PWM)", re.I)


class TopologyNotConfigured(BaseModel):
    """Returned when a topology tool is called without an IR design."""

    status: Literal["not_configured"] = "not_configured"
    reason: str = "No Allegro/PST Design topology is loaded for this run."


class ComponentIdentity(BaseModel):
    """Bounded identity fields for one component."""

    refdes: str
    value: str = ""
    part_number: str = ""
    manufacturer: str = ""
    package: str = ""


class PinNetSummary(BaseModel):
    """One schematic pin and its parsed net."""

    pin_number: str
    pin_name: str = ""
    net: str | None = None


class NetMemberSummary(BaseModel):
    """One component pin participating in a net."""

    refdes: str
    pin_number: str
    pin_name: str = ""
    value: str = ""
    part_number: str = ""
    manufacturer: str = ""


class NeighborNetSummary(BaseModel):
    """Bounded neighboring components on one component pin's net."""

    net_name: str
    member_count: int
    members: list[NetMemberSummary] = Field(default_factory=list)


class ValidationIssueSummary(BaseModel):
    """Important validation issue copied from ProjectValidationIndex."""

    check: str
    status: Literal["WARN", "ERROR"]
    summary: str
    evidence: list[str] = Field(default_factory=list)


class GetComponentContextInput(BaseModel):
    """Lookup parsed topology context for one component refdes."""

    refdes: str
    neighbor_limit: int = Field(default=24, ge=0, le=200)


class ComponentContextFound(BaseModel):
    """Component topology context from Design + optional validation index."""

    status: Literal["found"] = "found"
    component: ComponentIdentity
    profile_status: str = ""
    validation_status: str = ""
    profile_path: str | None = None
    pins: list[PinNetSummary] = Field(default_factory=list)
    neighbors: list[NeighborNetSummary] = Field(default_factory=list)
    issues: list[ValidationIssueSummary] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class ComponentContextNotFound(BaseModel):
    """Unknown refdes branch with registry-derived closest matches."""

    status: Literal["not_found"] = "not_found"
    refdes: str
    closest_matches: list[str] = Field(default_factory=list)


class GetNetContextInput(BaseModel):
    """Lookup parsed membership for one exact net name."""

    net_name: str
    member_limit: int = Field(default=40, ge=1, le=300)


class NetContextFound(BaseModel):
    """Exact net membership context."""

    status: Literal["found"] = "found"
    net_name: str
    member_count: int
    members: list[NetMemberSummary] = Field(default_factory=list)


class NetContextNotFound(BaseModel):
    """Unknown net branch with closest net-name matches."""

    status: Literal["not_found"] = "not_found"
    net_name: str
    closest_matches: list[str] = Field(default_factory=list)


class SearchNetsInput(BaseModel):
    """Search parsed net names by deterministic substring matching."""

    query: str
    limit: int = Field(default=30, ge=1, le=200)
    member_sample_limit: int = Field(default=6, ge=0, le=30)


class NetSearchHit(BaseModel):
    """One net search result."""

    net_name: str
    member_count: int
    sample_members: list[NetMemberSummary] = Field(default_factory=list)


class SearchNetsResult(BaseModel):
    """Search result for net-name queries."""

    found: bool
    query: str
    hits: list[NetSearchHit] = Field(default_factory=list)
    closest_matches: list[str] = Field(default_factory=list)


class SummarizeProjectTopologyInput(BaseModel):
    """Bounded project topology summary knobs."""

    component_limit: int = Field(default=12, ge=1, le=80)
    net_limit: int = Field(default=12, ge=1, le=80)
    gap_limit: int = Field(default=10, ge=0, le=50)


class ProjectTopologySummary(BaseModel):
    """Facts-only project topology overview."""

    status: Literal["summarized"] = "summarized"
    component_count: int
    net_count: int
    bom_matched: int | None = None
    validated_count: int | None = None
    manual_count: int | None = None
    validation_totals: dict[str, int] = Field(default_factory=dict)
    high_signal_components: list[ComponentIdentity] = Field(default_factory=list)
    power_like_nets: list[NetSearchHit] = Field(default_factory=list)
    interface_like_nets: list[NetSearchHit] = Field(default_factory=list)
    control_like_nets: list[NetSearchHit] = Field(default_factory=list)
    profile_gap_groups: list[dict[str, Any]] = Field(default_factory=list)


def get_component_context(
    design: Design | None,
    project_index: ProjectValidationIndex | None,
    tool_input: GetComponentContextInput,
) -> ComponentContextFound | ComponentContextNotFound | TopologyNotConfigured:
    """Return one component's parsed pins, nets, neighbors, and validation state."""

    if design is None:
        return TopologyNotConfigured()
    refdes = tool_input.refdes
    component = design.components.get(refdes)
    if component is None:
        return ComponentContextNotFound(
            refdes=refdes,
            closest_matches=_closest(refdes, design.components.keys()),
        )
    row = _row_by_refdes(project_index).get(refdes) if project_index is not None else None
    pins = [
        PinNetSummary(pin_number=pin.number, pin_name=pin.name, net=pin.net)
        for pin in sorted(component.pins, key=lambda pin: _pin_sort_key(pin.number))
    ]
    return ComponentContextFound(
        component=_component_identity(component),
        profile_status=row.match_status if row is not None else "",
        validation_status=row.status if row is not None else "",
        profile_path=row.profile_path if row is not None else None,
        pins=pins,
        neighbors=_neighbor_summaries(design, component, tool_input.neighbor_limit),
        issues=_validation_issues(row),
        evidence=_row_evidence(row),
    )


def get_net_context(
    design: Design | None,
    tool_input: GetNetContextInput,
) -> NetContextFound | NetContextNotFound | TopologyNotConfigured:
    """Return exact net membership with bounded component identity facts."""

    if design is None:
        return TopologyNotConfigured()
    net = design.nets.get(tool_input.net_name)
    if net is None:
        return NetContextNotFound(
            net_name=tool_input.net_name,
            closest_matches=_closest(tool_input.net_name, design.nets.keys()),
        )
    return NetContextFound(
        net_name=net.name,
        member_count=len(net.nodes),
        members=_member_summaries(design, net.nodes, limit=tool_input.member_limit),
    )


def search_nets(
    design: Design | None,
    tool_input: SearchNetsInput,
) -> SearchNetsResult | TopologyNotConfigured:
    """Search net names by deterministic case-insensitive token matching."""

    if design is None:
        return TopologyNotConfigured()
    tokens = _query_tokens(tool_input.query)
    scored: list[tuple[int, str]] = []
    for name in design.nets:
        score = _net_match_score(name, tokens)
        if score:
            scored.append((score, name))
    scored.sort(key=lambda item: (-item[0], _net_sort_key(item[1])))
    hits = [
        _net_search_hit(design, name, tool_input.member_sample_limit)
        for _score, name in scored[: tool_input.limit]
    ]
    return SearchNetsResult(
        found=bool(hits),
        query=tool_input.query,
        hits=hits,
        closest_matches=[] if hits else _closest(tool_input.query, design.nets.keys()),
    )


def summarize_project_topology(
    design: Design | None,
    project_index: ProjectValidationIndex | None,
    tool_input: SummarizeProjectTopologyInput,
) -> ProjectTopologySummary | TopologyNotConfigured:
    """Return a bounded facts-only topology summary."""

    if design is None:
        return TopologyNotConfigured()
    return ProjectTopologySummary(
        component_count=len(design.components),
        net_count=len(design.nets),
        bom_matched=project_index.bom_matched if project_index is not None else None,
        validated_count=len(project_index.validated_rows) if project_index is not None else None,
        manual_count=len(project_index.manual_rows) if project_index is not None else None,
        validation_totals=project_index.totals if project_index is not None else {},
        high_signal_components=_high_signal_components(design, project_index, tool_input.component_limit),
        power_like_nets=_pattern_net_hits(design, POWER_NET_PATTERN, tool_input.net_limit),
        interface_like_nets=_pattern_net_hits(design, INTERFACE_NET_PATTERN, tool_input.net_limit),
        control_like_nets=_pattern_net_hits(design, CONTROL_NET_PATTERN, tool_input.net_limit),
        profile_gap_groups=_profile_gap_payload(project_index, tool_input.gap_limit),
    )


TOPOLOGY_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "get_component_context",
        "description": (
            "Return one component's Allegro/PST schematic topology context: identity, "
            "profile/validation state, pin-to-net rows, neighboring components by net, "
            "and important validation evidence. Use for questions like 'what is U8 "
            "connected to?' or 'explain this selected component'. On unknown refdes, "
            "returns closest matches; never fabricate refdes."
        ),
        "input_schema": GetComponentContextInput.model_json_schema(),
    },
    {
        "name": "get_net_context",
        "description": (
            "Return exact parsed net membership from the schematic netlist. Use when "
            "the user names a specific net and asks what components/pins are on it. "
            "On unknown net, returns closest net-name matches; do not invent nets."
        ),
        "input_schema": GetNetContextInput.model_json_schema(),
    },
    {
        "name": "search_nets",
        "description": (
            "Search parsed schematic net names by substring tokens such as RESET, SDA, "
            "BOOT, VIN, 3V3, SWD, or PWM. Returns bounded net membership samples from "
            "the Allegro/PST Design topology."
        ),
        "input_schema": SearchNetsInput.model_json_schema(),
    },
    {
        "name": "summarize_project_topology",
        "description": (
            "Return a bounded project topology overview: component/net counts, validation "
            "coverage, high-signal components, conservative power/interface/control-like "
            "net buckets, and profile gaps. This does not infer schematic module names."
        ),
        "input_schema": SummarizeProjectTopologyInput.model_json_schema(),
    },
]


def _row_by_refdes(project_index: ProjectValidationIndex | None) -> dict[str, ProjectValidationRow]:
    if project_index is None:
        return {}
    return {row.refdes: row for row in project_index.rows}


def _component_identity(component: Component) -> ComponentIdentity:
    return ComponentIdentity(
        refdes=component.refdes,
        value=component.value or "",
        part_number=component.part_number or "",
        manufacturer=component.manufacturer or "",
        package=component.package or "",
    )


def _member_summary(design: Design, refdes: str, pin_number: str) -> NetMemberSummary:
    component = design.components.get(refdes)
    pin = component.pin_by_number(pin_number) if component is not None else None
    return NetMemberSummary(
        refdes=refdes,
        pin_number=pin_number,
        pin_name=pin.name if pin is not None else "",
        value=component.value if component is not None else "",
        part_number=(component.part_number or "") if component is not None else "",
        manufacturer=(component.manufacturer or "") if component is not None else "",
    )


def _member_summaries(
    design: Design,
    nodes: list[tuple[str, str]],
    *,
    limit: int,
) -> list[NetMemberSummary]:
    sorted_nodes = sorted(nodes, key=lambda node: (sort_refdes_key(node[0]), _pin_sort_key(node[1])))
    return [_member_summary(design, refdes, pin_number) for refdes, pin_number in sorted_nodes[:limit]]


def _neighbor_summaries(
    design: Design,
    component: Component,
    limit: int,
) -> list[NeighborNetSummary]:
    out: list[NeighborNetSummary] = []
    remaining = limit
    for pin in sorted(component.pins, key=lambda item: _pin_sort_key(item.number)):
        if not pin.net:
            continue
        net = design.nets.get(pin.net)
        if net is None:
            continue
        neighbor_nodes = [(refdes, number) for refdes, number in net.nodes if refdes != component.refdes]
        sample_limit = max(0, remaining)
        members = _member_summaries(design, neighbor_nodes, limit=sample_limit)
        out.append(
            NeighborNetSummary(
                net_name=net.name,
                member_count=len(net.nodes),
                members=members,
            )
        )
        remaining = max(0, remaining - len(members))
    return out


def _validation_issues(row: ProjectValidationRow | None) -> list[ValidationIssueSummary]:
    if row is None or row.validation is None:
        return []
    issues: list[ValidationIssueSummary] = []
    for pin in row.validation.pin_results:
        if pin.status in {"WARN", "ERROR"}:
            issues.append(
                ValidationIssueSummary(
                    check=pin.pin_name or pin.pin_number,
                    status=pin.status,
                    summary=pin.summary,
                    evidence=pin.evidence,
                )
            )
    for check in row.validation.component_checks:
        if check.status in {"WARN", "ERROR"}:
            issues.append(
                ValidationIssueSummary(
                    check=check.check,
                    status=check.status,
                    summary=check.summary,
                    evidence=check.evidence,
                )
            )
    return issues


def _row_evidence(row: ProjectValidationRow | None) -> list[str]:
    if row is None or row.validation is None:
        return []
    tokens: list[str] = []
    for issue in _validation_issues(row):
        for token in issue.evidence:
            if token and token not in tokens:
                tokens.append(token)
    return tokens


def _net_search_hit(design: Design, name: str, member_sample_limit: int) -> NetSearchHit:
    net = design.nets[name]
    return NetSearchHit(
        net_name=name,
        member_count=len(net.nodes),
        sample_members=_member_summaries(design, net.nodes, limit=member_sample_limit),
    )


def _pattern_net_hits(
    design: Design,
    pattern: re.Pattern[str],
    limit: int,
) -> list[NetSearchHit]:
    names = [name for name in design.nets if pattern.search(name)]
    names.sort(key=_net_bucket_sort_key)
    return [_net_search_hit(design, name, 4) for name in names[:limit]]


def _high_signal_components(
    design: Design,
    project_index: ProjectValidationIndex | None,
    limit: int,
) -> list[ComponentIdentity]:
    selected: list[str] = []
    if project_index is not None:
        for status in ("ERROR", "WARN", "PASS"):
            for row in project_index.validated_rows:
                if row.validation is not None and row.validation.status == status:
                    selected.append(row.refdes)
                    if len(selected) >= limit:
                        return [_component_identity(design.components[refdes]) for refdes in selected]
    for refdes in sorted(design.components, key=sort_refdes_key):
        if refdes.startswith("U") and refdes not in selected:
            selected.append(refdes)
            if len(selected) >= limit:
                break
    return [_component_identity(design.components[refdes]) for refdes in selected]


def _profile_gap_payload(
    project_index: ProjectValidationIndex | None,
    limit: int,
) -> list[dict[str, Any]]:
    if project_index is None or limit <= 0:
        return []
    return [group.model_dump(mode="json") for group in profile_gap_groups(project_index, limit=limit)]


def _closest(value: str, candidates: Any) -> list[str]:
    return difflib.get_close_matches(value, sorted(candidates), n=5, cutoff=0.45)


def _query_tokens(query: str) -> list[str]:
    tokens = [token.upper() for token in re.findall(r"[A-Za-z0-9_+.-]+", query)]
    if not tokens:
        tokens = [query.upper()]
    expanded: list[str] = []
    aliases = {
        "RESET": ["RESET", "RST", "NRST"],
        "RST": ["RST", "RESET", "NRST"],
        "BOOT": ["BOOT", "BOOT0"],
        "SWD": ["SWD", "SWCLK", "SWDIO"],
    }
    for token in tokens:
        for expanded_token in aliases.get(token, [token]):
            if expanded_token and expanded_token not in expanded:
                expanded.append(expanded_token)
    return expanded


def _net_match_score(name: str, tokens: list[str]) -> int:
    haystack = name.upper()
    score = 0
    for token in tokens:
        if token and token in haystack:
            score += len(token)
    return score


def _pin_sort_key(value: str) -> tuple[int, int | str, str]:
    if value.isdigit():
        return (0, int(value), value)
    return (1, value, value)


def _net_sort_key(name: str) -> tuple[str, int, str]:
    return (re.sub(r"\d+", "", name), len(name), name)


def _net_bucket_sort_key(name: str) -> tuple[int, str]:
    return (-_net_bucket_priority(name), name)


def _net_bucket_priority(name: str) -> int:
    """Give common rails a stable lead position in bounded net buckets."""
    compact = name.upper()
    if compact in {"GND", "PGND", "AGND"}:
        return 3
    if compact.startswith(("+", "V")):
        return 2
    return 1
