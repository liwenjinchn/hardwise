"""Connector validation rules (2x5 pin header)."""

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.pins import voltage_for_net
from hardwise.validation.types import ComponentValidation


class ConnectorValidator:
    """Validates 2x5 pin header connector circuits."""

    def __init__(self, component: Component, design: Design):
        self.component = component
        self.design = design

    def validate(self) -> list[ComponentValidation]:
        """Run all connector validation checks."""
        results = []
        results.append(self._check_power_voltage())
        results.append(self._check_ground_connectivity())
        results.extend(self._check_signal_connectivity())
        return results

    def _check_power_voltage(self) -> ComponentValidation:
        """Check VCC pin voltage is within recommended range (3.0V to 5.5V)."""
        vcc_pin = self.component.pin_by_number("1")
        if not vcc_pin or not vcc_pin.net:
            return ComponentValidation(
                check="connector_power_voltage",
                status="ERROR",
                summary="VCC pin (pin 1) not connected",
            )

        voltage = voltage_for_net(vcc_pin.net, self.design)
        if voltage is None:
            return ComponentValidation(
                check="connector_power_voltage",
                status="WARN",
                summary=f"Cannot infer VCC voltage from net '{vcc_pin.net}'",
            )

        if voltage < 3.0:
            return ComponentValidation(
                check="connector_power_voltage",
                status="ERROR",
                summary=f"VCC voltage {voltage:g}V is below minimum 3.0V",
            )
        if voltage > 5.5:
            return ComponentValidation(
                check="connector_power_voltage",
                status="ERROR",
                summary=f"VCC voltage {voltage:g}V exceeds maximum 5.5V",
            )

        return ComponentValidation(
            check="connector_power_voltage",
            status="PASS",
            summary=f"VCC voltage {voltage:g}V within range 3.0V-5.5V",
        )

    def _check_ground_connectivity(self) -> ComponentValidation:
        """Check GND pin is connected to a ground net."""
        gnd_pin = self.component.pin_by_number("5")
        if not gnd_pin or not gnd_pin.net:
            return ComponentValidation(
                check="connector_ground_connectivity",
                status="ERROR",
                summary="GND pin (pin 5) not connected",
            )

        # Check if connected to a recognized ground net
        net_name_upper = gnd_pin.net.upper()
        ground_nets = {"GND", "AGND", "DGND", "PGND", "HV_GND", "SGND"}
        if net_name_upper not in ground_nets:
            return ComponentValidation(
                check="connector_ground_connectivity",
                status="ERROR",
                summary=f"GND pin connected to '{gnd_pin.net}' (not a recognized ground net)",
            )

        return ComponentValidation(
            check="connector_ground_connectivity",
            status="PASS",
            summary=f"GND connected to '{gnd_pin.net}'",
        )

    def _check_signal_connectivity(self) -> list[ComponentValidation]:
        """Check all signal pins (2-4, 6-10) are connected."""
        results = []
        signal_pins = ["2", "3", "4", "6", "7", "8", "9", "10"]

        for pin_num in signal_pins:
            pin = self.component.pin_by_number(pin_num)
            if not pin or not pin.net:
                results.append(
                    ComponentValidation(
                        check=f"connector_signal_{pin_num}_connectivity",
                        status="ERROR",
                        summary=f"Signal pin {pin_num} not connected",
                    )
                )
            else:
                results.append(
                    ComponentValidation(
                        check=f"connector_signal_{pin_num}_connectivity",
                        status="PASS",
                        summary=f"Signal pin {pin_num} connected to '{pin.net}'",
                    )
                )

        return results


def validate_connector(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    """Entry point for connector validation."""
    validator = ConnectorValidator(component, design)
    return validator.validate()
