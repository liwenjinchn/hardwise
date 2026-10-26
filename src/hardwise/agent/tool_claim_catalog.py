"""Convert dispatched typed tool output into scoped facts without parsing prose."""

import json

from pydantic import TypeAdapter, ValidationError

from hardwise.agent.claim_contract import ClaimBinding, make_evidence_fact
from hardwise.agent import tools, topology_tools as topology, document_tools as documents
from hardwise.agent.evidence_locator import LocateComponentEvidenceResult


RESULTS = {
    "list_components": tools.ListComponentsResult,
    "get_component": tools.ComponentFound | tools.ComponentNotFound,
    "get_nc_pins": tools.GetNcPinsResult,
    "search_datasheet": tools.SearchDatasheetResult,
    "run_component_validation": (
        tools.ValidationRan | tools.ValidationNoProfile | tools.ValidationRefdesNotFound
    ),
    "get_component_context": (
        topology.ComponentContextFound
        | topology.ComponentContextNotFound
        | topology.TopologyNotConfigured
    ),
    "get_net_context": (
        topology.NetContextFound | topology.NetContextNotFound | topology.TopologyNotConfigured
    ),
    "search_nets": topology.SearchNetsResult | topology.TopologyNotConfigured,
    "summarize_project_topology": topology.ProjectTopologySummary | topology.TopologyNotConfigured,
    "get_component_documents": documents.ComponentDocumentsResult | documents.DocumentNotConfigured,
    "summarize_document_coverage": documents.DocumentCoverageSummary
    | documents.DocumentNotConfigured,
    "locate_component_evidence": LocateComponentEvidenceResult,
}


def tool_claim_catalog(name, payload, *, arguments, scope_id, call_id, project_id, known_objects):
    """Accept only server-dispatched payloads; never pass a model's alleged result.

    The catalog does not authorize new assessments. Misses, coverage, identity
    observations and existing machine rows keep separate kinds. It never reads
    an index/profile outside the tool response to fill missing evidence.
    """
    if name not in RESULTS or "error" in payload:
        return ()
    try:
        result = TypeAdapter(RESULTS[name]).validate_json(
            json.dumps(payload, allow_nan=False), strict=True
        )
        data = result.model_dump(mode="json")
        if data.get("status") == "not_configured":
            return ()
        # An outcome may describe an unknown requested identity, but that
        # identity must never become the subject of a positive registry fact.
        requested = arguments.get("refdes")
        returned = data.get("refdes", data.get("component", {}).get("refdes"))
        if requested is not None and returned is not None and requested != returned:
            return ()
        if name == "get_net_context" and arguments.get("net_name") != data.get("net_name"):
            return ()
        builder = _Catalog(scope_id, call_id, project_id, known_objects, arguments)
        status = data.get("status") or ("found" if data.get("found") else "empty")
        builder.add("project", project_id, "lookup." + name, status, kind="lookup_result")
        _project_result(builder, name, data)
        _object_result(builder, name, data, arguments)
        return tuple(builder.facts)
    except (ValueError, TypeError, RecursionError, ValidationError):
        # A malformed or nonfinite tool response cannot bootstrap authority.
        return ()


class _Catalog:
    def __init__(self, scope_id, call_id, project_id, known_objects, arguments):
        self.scope_id, self.call_id, self.project_id = scope_id, call_id, project_id
        self.known_objects, self.arguments, self.facts = known_objects, arguments, []

    def bind(self, binding):
        if (binding.object_kind, binding.object_id) not in self.known_objects:
            raise ValueError("tool result object is not in the parsed registry")
        self.facts.append(
            make_evidence_fact(binding=binding, scope_id=self.scope_id, call_id=self.call_id)
        )

    def add(
        self,
        kind_of_object,
        object_id,
        key,
        value,
        *,
        kind="observation",
        conditions=None,
        tokens=(),
        version=None,
    ):
        self.bind(
            ClaimBinding(
                object_kind=kind_of_object,
                object_id=object_id,
                property_key=key,
                kind=kind,
                value=value,
                unit=None,
                conditions={"request": self.arguments, **(conditions or {})},
                conditions_status="explicit",
                source_tokens=tuple(dict.fromkeys(tokens)),
                rule_version=version,
            )
        )

    def identity(self, component):
        refdes = component["refdes"]
        for field in ("value", "part_number", "manufacturer", "package", "footprint", "datasheet"):
            if field in component:
                self.add("component", refdes, "identity." + field, component[field])


def _project_result(b, name, data):
    project = b.project_id
    if name == "list_components":
        b.add("project", project, "components.match_count", data["total"])
        for component in data["components"]:
            b.identity(component)
    elif name == "get_nc_pins":
        b.add("project", project, "nc_pins.match_count", data["total"])
        for pin in data["pins"]:
            b.add("component", pin["refdes"], "nc_pin." + pin["pin_number"], pin)
    elif name == "search_datasheet":
        # Retrieved text is a source excerpt, never an approved numeric fact.
        b.add("project", project, "datasheets.retrieved_hits", data["hits"], kind="source_coverage")
    elif name == "search_nets":
        b.add("project", project, "nets.returned_match_count", len(data["hits"]))
        for hit in data["hits"]:
            b.add("net", hit["net_name"], "connectivity.search_hit", hit)
    elif name == "summarize_project_topology":
        for field in (
            "component_count",
            "net_count",
            "bom_matched",
            "validated_count",
            "manual_count",
            "validation_totals",
            "high_signal_components",
            "power_like_nets",
            "interface_like_nets",
            "control_like_nets",
            "profile_gap_groups",
        ):
            b.add("project", project, "topology." + field, data[field])
    elif name == "summarize_document_coverage":
        b.add("project", project, "documents.coverage", data, kind="source_coverage")


def _object_result(b, name, data, arguments):
    if name in {"get_component", "get_component_context"} and data.get("status") == "found":
        b.identity(data["component"])
        if name == "get_component_context":
            refdes = data["component"]["refdes"]
            for field in ("pins", "neighbors", "issues", "profile_status"):
                b.add("component", refdes, "context." + field, data[field])
    elif name == "get_net_context" and data.get("status") == "found":
        for field in ("member_count", "members"):
            b.add("net", data["net_name"], "connectivity." + field, data[field])
    elif name == "run_component_validation" and data.get("status") == "validated":
        for index, check in enumerate(data["checks"]):
            conditions = {
                "check": check["check"],
                "row": index,
                "severity": check["severity"],
                "needs_review": check["needs_review"],
                "evidence_kind": check["evidence_kind"],
                "profile_part_number": data["profile_part_number"],
            }
            b.add(
                "component",
                data["refdes"],
                f"validation.{index}.result",
                check["result"],
                kind="assessment",
                conditions=conditions,
                tokens=check["evidence"],
                version=check["rule_version"],
            )
            # This is a quoted machine-produced reason, not a model explanation
            # or a second inference of a physical parameter from its prose.
            b.add(
                "component",
                data["refdes"],
                f"validation.{index}.reason",
                check["summary"],
                conditions=conditions,
                tokens=check["evidence"],
                version=check["rule_version"],
            )
    elif name == "get_component_documents":
        if ("component", data["refdes"]) in b.known_objects:
            b.add("component", data["refdes"], "documents.coverage", data, kind="source_coverage")
    elif name == "locate_component_evidence":
        refdes = arguments.get("refdes")
        if ("component", refdes) not in b.known_objects:
            return
        for index, hit in enumerate(data["hits"]):
            if hit["source_kind"] in {"profile_fact", "profile_pin"} and data["status"] == "found":
                for raw in hit.get("claim_bindings", []):
                    binding = ClaimBinding.model_validate_json(json.dumps(raw))
                    if binding.object_kind != "component" or binding.object_id != refdes:
                        raise ValueError("locator binding does not match queried component")
                    b.bind(binding)
            # Even a true token or a legacy hit with no typed binding remains
            # source coverage; never parse its display value to certify a spec.
            b.add(
                "component",
                refdes,
                f"evidence_locator.{index}.source",
                hit,
                kind="source_coverage",
                tokens=hit["evidence"],
            )
