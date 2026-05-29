"""Diode validation rules (SS34 Schottky)."""

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.pins import voltage_for_net
from hardwise.validation.types import ComponentValidation


class DiodeValidator:
    """Validates Schottky diode circuits."""

    def __init__(self, component: Component, design: Design):
        self.component = component
        self.design = design

    def validate(self) -> list[ComponentValidation]:
        """Run all diode validation checks."""
        results = []
        results.append(self._check_cathode_connectivity())
        results.append(self._check_anode_connectivity())
        results.append(self._check_reverse_voltage())
        return results

    def _check_cathode_connectivity(self) -> ComponentValidation:
        """Check cathode pin is connected."""
        cathode_pin = self.component.pin_by_number("1")
        if not cathode_pin or not cathode_pin.net:
            return ComponentValidation(
                check="diode_cathode_connectivity",
                status="ERROR",
                summary="Cathode pin (pin 1) not connected",
            )

        return ComponentValidation(
            check="diode_cathode_connectivity",
            status="PASS",
            summary=f"Cathode connected to '{cathode_pin.net}'",
        )

    def _check_anode_connectivity(self) -> ComponentValidation:
        """Check anode pin is connected."""
        anode_pin = self.component.pin_by_number("2")
        if not anode_pin or not anode_pin.net:
            return ComponentValidation(
                check="diode_anode_connectivity",
                status="ERROR",
                summary="Anode pin (pin 2) not connected",
            )

        return ComponentValidation(
            check="diode_anode_connectivity",
            status="PASS",
            summary=f"Anode connected to '{anode_pin.net}'",
        )

    def _check_reverse_voltage(self) -> ComponentValidation:
        """Check reverse voltage does not exceed 40V."""
        cathode_pin = self.component.pin_by_number("1")
        anode_pin = self.component.pin_by_number("2")

        if not cathode_pin or not cathode_pin.net:
            return ComponentValidation(
                check="diode_reverse_voltage",
                status="ERROR",
                summary="Cathode pin not connected; cannot check reverse voltage",
            )

        if not anode_pin or not anode_pin.net:
            return ComponentValidation(
                check="diode_reverse_voltage",
                status="ERROR",
                summary="Anode pin not connected; cannot check reverse voltage",
            )

        cathode_voltage = voltage_for_net(cathode_pin.net, self.design)
        anode_voltage = voltage_for_net(anode_pin.net, self.design)

        if cathode_voltage is None or anode_voltage is None:
            return ComponentValidation(
                check="diode_reverse_voltage",
                status="WARN",
                summary="Cannot infer voltages to check reverse voltage",
            )

        # Reverse voltage is cathode - anode when cathode > anode
        reverse_voltage = cathode_voltage - anode_voltage

        if reverse_voltage > 40.0:
            return ComponentValidation(
                check="diode_reverse_voltage",
                status="ERROR",
                summary=f"Reverse voltage {reverse_voltage:g}V exceeds maximum 40V",
            )

        return ComponentValidation(
            check="diode_reverse_voltage",
            status="PASS",
            summary=f"Reverse voltage {reverse_voltage:g}V within 40V limit",
        )


def validate_diode(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    """Entry point for diode validation."""
    validator = DiodeValidator(component, design)
    return validator.validate()
