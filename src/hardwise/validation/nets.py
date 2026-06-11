"""Design-scoped net connectivity checks.

First net-level deterministic check family for the Allegro pre-Layout
path. The Allegro netlist/PST adapters already populate ``Design.nets``
with ``(refdes, pin_number)`` endpoints, but nothing consumed those
facts at net granularity until now.

``net_single_endpoint`` reports nets with exactly one endpoint as a
conservative L1 connectivity fact: a one-node net cannot form a current
path, but test points, fiducials, and intentionally reserved nets are
legitimate single-endpoint nets — so the verdict is WARN and the
decision stays with the reviewer, never an automatic ERROR.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from hardwise.ir.types import Design
from hardwise.validation.types import PinValidationStatus

CHECK_SINGLE_ENDPOINT = "net_single_endpoint"


class NetValidation(BaseModel):
    """Validation outcome for one design-level net check."""

    net_name: str
    check: str
    status: PinValidationStatus
    summary: str
    nodes: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


def validate_design_nets(
    design: Design, *, source_label: str | None = None
) -> list[NetValidation]:
    """Run net-level connectivity checks over ``design.nets``.

    ``source_label`` names the netlist source in evidence tokens; it
    falls back to ``design.project_path.name`` because the Design only
    records the project directory, not the netlist file name.
    """

    label = source_label or design.project_path.name
    results: list[NetValidation] = []
    for net_name in sorted(design.nets):
        net = design.nets[net_name]
        if len(net.nodes) != 1:
            continue
        refdes, pin_number = net.nodes[0]
        results.append(
            NetValidation(
                net_name=net_name,
                check=CHECK_SINGLE_ENDPOINT,
                status="WARN",
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
