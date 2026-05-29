"""MOSFET validation rules (IRF540N N-channel)."""

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.pins import voltage_for_net
from hardwise.validation.types import ComponentValidation


class MosfetValidator:
    """Validates N-channel MOSFET circuits."""

    def __init__(self, component: Component, design: Design):
        self.component = component
        self.design = design

    def validate(self) -> list[ComponentValidation]:
        """Run all MOSFET validation checks."""
        results = []
        results.append(self._check_vgs_range())
        results.append(self._check_gate_connectivity())
        results.append(self._check_drain_connectivity())
        results.append(self._check_source_connectivity())
        return results

    def _check_vgs_range(self) -> ComponentValidation:
        """Check Vgs is within absolute maximum (±20V)."""
        gate_pin = self.component.pin_by_number("1")
        if not gate_pin or not gate_pin.net:
            return ComponentValidation(
                check="mosfet_vgs_range",
                status="ERROR",
                summary="Gate pin (pin 1) not connected",
            )

        voltage = voltage_for_net(gate_pin.net, self.design)
        if voltage is None:
            return ComponentValidation(
                check="mosfet_vgs_range",
                status="WARN",
                summary=f"Cannot infer Vgs voltage from net '{gate_pin.net}'",
            )

        # Absolute maximum is ±20V
        if voltage < -20.0:
            return ComponentValidation(
                check="mosfet_vgs_range",
                status="ERROR",
                summary=f"Vgs voltage {voltage:g}V is below minimum -20V",
            )
        if voltage > 20.0:
            return ComponentValidation(
                check="mosfet_vgs_range",
                status="ERROR",
                summary=f"Vgs voltage {voltage:g}V exceeds maximum 20V",
            )

        return ComponentValidation(
            check="mosfet_vgs_range",
            status="PASS",
            summary=f"Vgs voltage {voltage:g}V within range ±20V",
        )

    def _check_gate_connectivity(self) -> ComponentValidation:
        """Check gate pin is connected."""
        gate_pin = self.component.pin_by_number("1")
        if not gate_pin or not gate_pin.net:
            return ComponentValidation(
                check="mosfet_gate_connectivity",
                status="ERROR",
                summary="Gate pin (pin 1) not connected",
            )

        return ComponentValidation(
            check="mosfet_gate_connectivity",
            status="PASS",
            summary=f"Gate connected to '{gate_pin.net}'",
        )

    def _check_drain_connectivity(self) -> ComponentValidation:
        """Check drain pin is connected."""
        drain_pin = self.component.pin_by_number("2")
        if not drain_pin or not drain_pin.net:
            return ComponentValidation(
                check="mosfet_drain_connectivity",
                status="ERROR",
                summary="Drain pin (pin 2) not connected",
            )

        return ComponentValidation(
            check="mosfet_drain_connectivity",
            status="PASS",
            summary=f"Drain connected to '{drain_pin.net}'",
        )

    def _check_source_connectivity(self) -> ComponentValidation:
        """Check source pin is connected."""
        source_pin = self.component.pin_by_number("3")
        if not source_pin or not source_pin.net:
            return ComponentValidation(
                check="mosfet_source_connectivity",
                status="ERROR",
                summary="Source pin (pin 3) not connected",
            )

        return ComponentValidation(
            check="mosfet_source_connectivity",
            status="PASS",
            summary=f"Source connected to '{source_pin.net}'",
        )


def validate_mosfet(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    """Entry point for MOSFET validation."""
    validator = MosfetValidator(component, design)
    return validator.validate()
