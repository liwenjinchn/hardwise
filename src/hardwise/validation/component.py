"""Deterministic single-component validation against a pin profile."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.pins import validate_pin
from hardwise.validation.pin_voltage import profile_reference_pin
from hardwise.validation.profile_conditions import validate_voltage_relations
from hardwise.validation.types import ComponentValidation, ValidationReport


def validate_component_against_profile(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ValidationReport:
    """Validate one component's schematic pins against a structured pin profile."""

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
        *_validate_profile_review_status(component, profile),
        *validate_voltage_relations(component, profile, design),
        *_validate_component_topology(component, profile, design),
    ]
    if profile.review_status != "ready":
        # Unreviewed profile premises cannot certify electrical PASS/FAIL.
        results = [
            item.model_copy(
                update={"result": "UNKNOWN", "evidence_kind": "HYPOTHESIS", "needs_review": True}
            )
            for item in results
        ]
        component_checks = [
            item.model_copy(
                update={"result": "UNKNOWN", "evidence_kind": "HYPOTHESIS", "needs_review": True}
            )
            for item in component_checks
        ]
    return ValidationReport(
        refdes=component.refdes,
        component_value=component.value,
        part_number=component.part_number,
        profile_part_number=profile.part_number,
        pin_results=results,
        component_checks=component_checks,
    )


def _validate_profile_review_status(
    component: Component,
    profile: DatasheetProfile,
) -> list[ComponentValidation]:
    if profile.review_status == "ready":
        return []
    return [
        ComponentValidation(
            check="profile_review_status",
            result="UNKNOWN",
            severity="WARNING",
            evidence_kind="HYPOTHESIS",
            refdes=component.refdes,
            summary=(
                f"Datasheet profile {profile.part_number} is marked {profile.review_status}; "
                "treat deterministic checks as reviewer-confirmed only after profile review."
            ),
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
