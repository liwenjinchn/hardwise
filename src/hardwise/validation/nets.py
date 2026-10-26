"""Design-scoped net connectivity checks.

Net-level deterministic check family for the Allegro pre-Layout path.
The Allegro netlist/PST adapters already populate ``Design.nets`` with
``(refdes, pin_number)`` endpoints, but nothing consumed those facts at
net granularity until this module.

``net_single_endpoint`` reports nets with exactly one endpoint as a
conservative L1 connectivity fact: a one-node net cannot form a current
path, but test points, fiducials, and intentionally reserved nets are
legitimate single-endpoint nets — so the verdict is WARN and the
decision stays with the reviewer, never an automatic ERROR.

``design_missing_ground_net`` reports a design whose nets contain no
recognized ground reference (per ``pins.is_ground_net``). A schematic
export without any ground net usually signals a partial or filtered
export, but bench fixtures and single-stage exports are legitimate — so
this is also WARN. It only fires when net facts exist at all; an empty
``Design.nets`` means the source carried no connectivity to judge.
"""

from __future__ import annotations

from pydantic import Field

from hardwise.ir.types import Design
from hardwise.ir.connectivity_queries import observed_net_names, declaration_token
from hardwise.validation.pins import is_ground_net
from hardwise.validation.assessment import Assessment

CHECK_SINGLE_ENDPOINT = "net_single_endpoint"
CHECK_MISSING_GROUND = "design_missing_ground_net"


class NetValidation(Assessment):
    """Validation outcome for one design-level net check."""

    net_name: str
    check: str
    summary: str
    nodes: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


def validate_design_nets(design: Design, *, source_label: str | None = None) -> list[NetValidation]:
    """Run net-level connectivity checks over ``design.nets``.

    ``source_label`` names the netlist source in evidence tokens; it
    falls back to ``design.project_path.name`` because the Design only
    records the project directory, not the netlist file name.
    """

    label = source_label or design.project_path.name
    results: list[NetValidation] = []
    observed = observed_net_names(design)
    if design.connectivity:
        for name in design.connectivity.ambiguous_net_names:
            records = [
                (i, d) for i, d in enumerate(design.connectivity.declarations) if d.net_name == name
            ]
            results.append(
                NetValidation(
                    net_name=name,
                    check="net_connection_ambiguity",
                    result="UNKNOWN",
                    severity="WARNING",
                    needs_review=True,
                    evidence_kind="SOURCE_FACT",
                    rule_version="1.connection-isolation1",
                    summary=f"网络 {name} 的来源连接声明有歧义，相关端点已隔离；不确认成员数，不当作开路或单端网络。",
                    nodes=[],
                    evidence=[declaration_token(d, i) for i, d in records],
                )
            )
    if observed and not any(is_ground_net(net_name) for net_name in observed):
        results.append(
            NetValidation(
                net_name="-",
                check=CHECK_MISSING_GROUND,
                result="UNKNOWN",
                severity="WARNING",
                summary=(
                    f"No net in this design is a recognized ground reference "
                    f"(checked {len(observed)} nets). A schematic export "
                    "without any ground net usually means a partial or "
                    "filtered export. Reviewer to confirm the export scope "
                    "is intentional."
                ),
                nodes=[],
                evidence=[f"netlist:{label}#nets={len(observed)}"],
            )
        )
    for net_name in sorted(design.nets):
        net = design.nets[net_name]
        if len(net.nodes) != 1:
            continue
        refdes, pin_number = net.nodes[0]
        results.append(
            NetValidation(
                net_name=net_name,
                check=CHECK_SINGLE_ENDPOINT,
                result="UNKNOWN",
                severity="WARNING",
                summary=(
                    f"Net {net_name} has a single endpoint {refdes}.{pin_number}; "
                    "a one-node net cannot form a current path. Reviewer to "
                    "confirm it is intentional (test point, fiducial, or "
                    "reserved net)."
                ),
                nodes=[f"{refdes}.{pin_number}"],
                evidence=[f"netlist:{label}#net={net_name}"],
            )
        )
    return results
