"""Lossless connection declarations and a fail-closed projection.

Design retains this projection separately from its resolved connectivity graph.
Consumers must handle the quarantine explicitly, never infer missing edges.
"""

from collections import defaultdict
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Name = Annotated[str, Field(min_length=1)]
Endpoint = tuple[Name, Name]


class ConnectionDeclaration(BaseModel):
    """One logical source record; continuation lines remain one declaration."""

    model_config = ConfigDict(extra="forbid")
    source: Name
    line: int | None = Field(default=None, ge=1)
    net_name: Name
    nodes: list[Endpoint] = Field(min_length=1)


class ConnectionAmbiguity(BaseModel):
    kind: Literal["duplicate_net_name", "repeated_endpoint", "multiple_declarations"]
    net_names: list[str]
    endpoints: list[Endpoint]
    declaration_indices: list[int]


class ConnectivityProjection(BaseModel):
    schema_version: Literal["hardwise.connectivity.v1"] = "hardwise.connectivity.v1"
    declarations: list[ConnectionDeclaration]
    resolved_nets: dict[str, list[Endpoint]]
    ambiguous_net_names: list[str]
    ambiguous_endpoints: list[Endpoint]
    ambiguities: list[ConnectionAmbiguity]


def project_connectivity(
    declarations: list[ConnectionDeclaration],
) -> ConnectivityProjection:
    """Preserve all evidence and isolate entire conflicting net declarations.

    Names are exact source identifiers, never shortened or case-folded. No
    duplicate, including an identical repeated record, authorizes merging.
    Source order is retained for evidence, not used to resolve conflicts.
    """
    by_name: dict[str, list[int]] = defaultdict(list)
    by_endpoint: dict[Endpoint, list[int]] = defaultdict(list)
    issues: list[ConnectionAmbiguity] = []
    for index, declaration in enumerate(declarations):
        by_name[declaration.net_name].append(index)
        seen: set[Endpoint] = set()
        repeated: set[Endpoint] = set()
        for endpoint in declaration.nodes:
            if endpoint in seen:
                repeated.add(endpoint)
            else:
                by_endpoint[endpoint].append(index)
                seen.add(endpoint)
        if repeated:
            issues.append(
                ConnectionAmbiguity(
                    kind="repeated_endpoint",
                    net_names=[declaration.net_name],
                    endpoints=sorted(repeated),
                    declaration_indices=[index],
                )
            )
    for name, indices in sorted(by_name.items()):
        if len(indices) > 1:
            issues.append(
                ConnectionAmbiguity(
                    kind="duplicate_net_name",
                    net_names=[name],
                    endpoints=[],
                    declaration_indices=indices,
                )
            )
    for endpoint, indices in sorted(by_endpoint.items()):
        if len(indices) > 1:
            issues.append(
                ConnectionAmbiguity(
                    kind="multiple_declarations",
                    net_names=sorted({declarations[i].net_name for i in indices}),
                    endpoints=[endpoint],
                    declaration_indices=indices,
                )
            )
    blocked_names = {name for issue in issues for name in issue.net_names}
    blocked_endpoints = {
        endpoint
        for declaration in declarations
        if declaration.net_name in blocked_names
        for endpoint in declaration.nodes
    }
    return ConnectivityProjection(
        declarations=[record.model_copy(deep=True) for record in declarations],
        resolved_nets={
            declaration.net_name: list(declaration.nodes)
            for declaration in declarations
            if declaration.net_name not in blocked_names
        },
        ambiguous_net_names=sorted(blocked_names),
        ambiguous_endpoints=sorted(blocked_endpoints),
        ambiguities=issues,
    )
