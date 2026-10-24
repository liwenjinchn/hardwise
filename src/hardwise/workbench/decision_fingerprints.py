"""Versioned semantic snapshots: component-local rules and explicit broad fallback."""

import hashlib
import json


# Audited local dependencies, bound to the producer's declared version.
LOCAL_RULES = {
    ("capacitor_rated_voltage_parse", "1"),
    ("capacitor_voltage_margin", "1"),
    ("resistor_power_estimate", "1"),
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
    return _digest([str(context.netlist_source.resolve()), str(context.bom.source_file.resolve())])


def _component(component):
    data = component.model_dump(
        mode="json", exclude={"findings", "decision", "datasheet_profile", "datasheet_path"}
    )
    # Provenance location can move without changing a parsed electrical premise.
    data["properties"] = {k: v for k, v in data["properties"].items() if k != "BOM_SOURCE"}
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
    Broader topology/auxiliary tasks currently use project-level semantic scope;
    per-rule dependency declarations must replace that fallback before A10 closes.
    """
    from hardwise.workbench.task_projection import build_review_tasks

    all_tasks = build_review_tasks(context)
    design = context.design
    project = review_project_key(context)
    profiles = {k: _profile(v) for k, v in context.validation_targets.items()}
    broad = {
        "components": {k: _component(v) for k, v in sorted(design.components.items())},
        "profiles": profiles,
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
            nets = {p.net for p in component.pins if p.net}
            facts = [
                f
                for f in design.voltage_facts.facts
                if f.net in nets and f.mode == design.voltage_facts.active_mode
            ]
            nets.update(f.reference_net for f in facts)
            payload = {
                "scope": "component",
                "component": _component(component),
                "profile": profiles.get(task.refdes),
                "active_mode": design.voltage_facts.active_mode,
                "facts": [
                    f.model_dump(mode="json")
                    for f in sorted(design.voltage_facts.facts, key=lambda f: (f.mode, f.net))
                    if f.net in nets and f.mode == design.voltage_facts.active_mode
                ],
            }
        else:
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
