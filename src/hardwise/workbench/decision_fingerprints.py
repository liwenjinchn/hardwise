"""Versioned component/control-neighborhood scopes with explicit broad fallback."""

import hashlib
import json

from hardwise.ir.identity_sources import MPN_RECORDS, is_mpn_field, netlist_mpn_sources
from hardwise.validation.passive_ratings import resolve_passive_rating
from hardwise.bom.source_fields import RATING_SOURCES
from hardwise.workbench.control_dependencies import control_dependency_payload, local_voltage_facts

REVIEW_DEPENDENCY_CONTRACT = "hardwise.review_dependencies.v2"

RATING_CHECKS = {
    "capacitor_rated_voltage_parse": "voltage",
    "capacitor_voltage_margin": "voltage",
    "resistor_power_estimate": "power",
}


# Audited local dependencies, bound to the producer's declared version.
LOCAL_RULES = {
    ("capacitor_rated_voltage_parse", "1"),
    ("capacitor_voltage_margin", "1"),
    ("resistor_power_estimate", "1"),
    ("capacitor_rated_voltage_parse", "2"),
    ("capacitor_voltage_margin", "2"),
    ("resistor_power_estimate", "2"),
    ("diode_reverse_voltage", "2"),
    ("tvs_working_standoff", "2"),
    ("mosfet_vgs_rating", "2"),
    ("mosfet_vds_rating", "2"),
    ("bjt_vebo_rating", "2"),
    ("bjt_vceo_rating", "2"),
    ("led_indicator_polarity", "2"),
}


def _digest(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str
        ).encode()
    ).hexdigest()


def review_project_key(context) -> str:
    """Source identity is separate from source contents and finding identity."""
    if context.managed_project_key:
        return context.managed_project_key
    return _digest([str(context.netlist_source.resolve()), str(context.bom.source_file.resolve())])


def _component(component):
    data = component.model_dump(
        mode="json", exclude={"findings", "decision", "datasheet_profile", "datasheet_path"}
    )
    # Provenance location can move without changing a parsed electrical premise.
    records = netlist_mpn_sources(component)
    data["properties"] = {
        k: v
        for k, v in data["properties"].items()
        if k not in {"BOM_SOURCE", MPN_RECORDS, RATING_SOURCES}
        and not (records and is_mpn_field(k))
    }
    if records:
        data["properties"][MPN_RECORDS] = sorted(
            {record["value"].strip().casefold() for record in records}
        )
    data["pins"] = sorted(data["pins"], key=lambda p: p["number"])
    return data


def _profile(profile):
    return (
        profile.model_dump(mode="json", exclude={"extracted_at", "extracted_model", "description"})
        if profile
        else None
    )


def review_fingerprints(context, tasks) -> dict[str, str]:
    """No guessed graph dependency for unmodeled rules: use a marked broad snapshot.

    Local pin and two-terminal numeric checks do not depend on unrelated devices.
    Audited v2 control observations use immediate control-net neighborhoods.
    Other topology/auxiliary tasks keep project-level semantic fallback;
    these declarations do not establish complete A10 coverage.
    """
    from hardwise.workbench.task_projection import build_review_tasks

    all_tasks = build_review_tasks(context)
    design = context.design
    project = review_project_key(context)
    profiles = {k: _profile(v) for k, v in context.validation_targets.items()}
    ratings = {}
    for row in context.index.validated_rows:
        component = design.components[row.refdes]
        bom_row = context.bom_report.rows_by_refdes.get(row.refdes)
        value = (bom_row.value if bom_row and bom_row.value else component.value) or ""
        dimensions = {
            RATING_CHECKS[check.check]
            for check in row.validation.component_checks
            if check.check in RATING_CHECKS
        }
        if dimensions:
            ratings[row.refdes] = {
                dimension: resolve_passive_rating(value, bom_row, dimension, component).signature()
                for dimension in sorted(dimensions)
            }
    broad = {
        "components": {k: _component(v) for k, v in sorted(design.components.items())},
        "profiles": profiles,
        "passive_rating_premises": ratings,
        "voltage_facts": design.voltage_facts.model_dump(mode="json"),
        "net_checks": [c.model_dump(mode="json") for c in context.index.net_checks],
        "auxiliary_tasks": [
            (t.stable_key, t.assessment.model_dump(mode="json") if t.assessment else None, t.body)
            for t in all_tasks
            if t.kind not in {"component_check", "pin_check"}
        ],
    }
    broad_hash = _digest(broad)
    output = {}
    for task in tasks:
        component = design.components.get(task.refdes)
        check = task.check or ""
        version = task.assessment.rule_version if task.assessment else None
        local = (task.kind == "pin_check" and version in {"1", "2"}) or (
            task.kind == "component_check" and (check, version) in LOCAL_RULES
        )
        if local and component:
            payload = {
                "scope": "component",
                "component": _component(component),
                "profile": profiles.get(task.refdes),
                "active_mode": design.voltage_facts.active_mode,
                "facts": local_voltage_facts(design, component),
            }
            if check in RATING_CHECKS:
                payload["passive_rating_premises"] = ratings.get(task.refdes, {}).get(
                    RATING_CHECKS[check]
                )
        else:
            payload = control_dependency_payload(
                context, task, _component, profiles.get(task.refdes)
            )
            if payload is None:
                payload = {"scope": "project_snapshot", "snapshot": broad_hash}
        output[task.stable_key] = _digest(
            {
                "version": 1,
                "project": project,
                "key": task.stable_key,
                "assessment": task.assessment.model_dump(mode="json") if task.assessment else None,
                "dependencies": payload,
            }
        )
    return output
