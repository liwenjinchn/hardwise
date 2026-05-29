"""Deterministic single-component validation against a pin profile."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.pins import validate_pin
from hardwise.validation.types import ComponentValidation, ValidationReport


def validate_component_against_profile(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ValidationReport:
    """Validate one component's schematic pins against a structured pin profile."""

    results = [validate_pin(component, pin_profile, design) for pin_profile in profile.pins]
    component_checks = _validate_component_topology(component, profile, design)
    return ValidationReport(
        refdes=component.refdes,
        component_value=component.value,
        part_number=component.part_number,
        profile_part_number=profile.part_number,
        pin_results=results,
        component_checks=component_checks,
    )


def _validate_component_topology(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    family = str(profile.recommended.get("topology_family", "")).lower()
    if profile.part_number.upper() == "XL1509-12E1" or family == "buck":
        from hardwise.validation.dcdc import validate_buck_topology

        return validate_buck_topology(component, profile, design)
    if profile.part_number.upper() == "EG2132" or family == "half_bridge_gate_driver":
        from hardwise.validation.gate_driver import validate_half_bridge_gate_driver

        return validate_half_bridge_gate_driver(component, profile, design)
    if profile.part_number.upper() == "STM32G030C8T6" or family == "mcu_basic":
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
    return []
