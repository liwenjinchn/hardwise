"""Deterministic single-component validation against a pin profile."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.identity_scope import (
    identity_conflict_report,
    scope_topology_identities,
    profile_identity_conflict_report,
)
from hardwise.validation.pins import validate_pin
from hardwise.validation.profile_approval import approval_reason, scope_result, approved_tokens
from hardwise.validation.pin_voltage import profile_reference_pin
from hardwise.validation.profile_conditions import validate_voltage_relations
from hardwise.validation.types import ComponentValidation, ValidationReport


def validate_component_against_profile(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ValidationReport:
    """Validate one component's schematic pins against a structured pin profile."""

    conflict = identity_conflict_report(component) or profile_identity_conflict_report(
        component, profile
    )
    if conflict is not None:
        return conflict

    lifecycle = profile.lifecycle
    reason = approval_reason(component, profile, lifecycle=lifecycle)
    relation_targets = {relation.target_pin for relation in profile.voltage_relations}
    reference = profile_reference_pin(component, profile)
    results = [validate_pin(component, p, design, reference_pin=reference) for p in profile.pins]
    results = [
        item.model_copy(
            update={
                "result": "UNKNOWN",
                "summary": "此引脚的电压约束由独立关系式检查评估；连接不能证明电压合规。",
            }
        )
        if item.pin_number in relation_targets and item.result == "PASS"
        else item
        for item in results
    ]
    component_checks = [
        *_validate_profile_review_status(component, profile, reason),
        *validate_voltage_relations(component, profile, design),
        *scope_topology_identities(
            _validate_component_topology(component, profile, design), design
        ),
    ]
    results = [scope_result(item, reason) for item in results]
    component_checks = [scope_result(item, reason) for item in component_checks]
    return ValidationReport(
        refdes=component.refdes,
        component_value=component.value,
        part_number=component.part_number,
        profile_part_number=profile.part_number,
        profile_lifecycle=lifecycle,
        legacy_profile_status=profile.review_status,
        reviewed_profile_tokens=sorted(approved_tokens(profile)) if reason is None else [],
        pin_results=results,
        component_checks=component_checks,
    )


def _validate_profile_review_status(
    component: Component,
    profile: DatasheetProfile,
    reason: str | None,
) -> list[ComponentValidation]:
    if reason is None:
        return []
    return [
        ComponentValidation(
            check="profile_review_status",
            result="UNKNOWN",
            rule_version="2",
            severity="WARNING",
            evidence_kind="HYPOTHESIS",
            refdes=component.refdes,
            summary=reason,
            evidence=[],
        )
    ]


def _validate_component_topology(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    family = str(profile.recommended.get("topology_family", "")).lower()
    if family == "buck":
        from hardwise.validation.dcdc import validate_buck_topology

        return validate_buck_topology(component, profile, design)
    if family == "half_bridge_gate_driver":
        from hardwise.validation.gate_driver import validate_half_bridge_gate_driver

        return validate_half_bridge_gate_driver(component, profile, design)
    if family == "mcu_basic":
        from hardwise.validation.mcu import validate_mcu_basic

        return validate_mcu_basic(component, profile, design)
    if family == "i2c_mux":
        from hardwise.validation.i2c_mux import validate_i2c_mux

        return validate_i2c_mux(component, profile, design)
    if family == "diode":
        from hardwise.validation.diode import validate_diode

        return validate_diode(component, profile, design)
    if family == "connector":
        from hardwise.validation.connector import validate_connector

        return validate_connector(component, profile, design)
    if family == "mosfet":
        from hardwise.validation.mosfet import validate_mosfet

        return validate_mosfet(component, profile, design)
    if family == "bjt":
        from hardwise.validation.bjt import validate_bjt

        return validate_bjt(component, profile, design)
    if family == "shift_register_piso":
        from hardwise.validation.shift_register import validate_shift_register_piso

        return validate_shift_register_piso(component, profile, design)
    if family == "i2c_level_shift_repeater":
        from hardwise.validation.i2c_repeater import validate_i2c_level_shift_repeater

        return validate_i2c_level_shift_repeater(component, profile, design)
    return []
