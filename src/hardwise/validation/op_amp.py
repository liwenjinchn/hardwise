"""LM358 dual operational amplifier validation rules."""

from __future__ import annotations

from hardwise.ir.types import Component, Design
from hardwise.validation.pins import voltage_for_net
from hardwise.validation.types import ComponentValidation


LM358_PIN_MAP = {
    "1": "OUT_A",
    "2": "IN_A-",
    "3": "IN_A+",
    "4": "VEE_GND",
    "5": "IN_B+",
    "6": "IN_B-",
    "7": "OUT_B",
    "8": "VCC",
}


class OpAmpValidator:
    """Validates LM358 dual op-amp circuits."""

    def __init__(self, component: Component, design: Design):
        self.component = component
        self.design = design

    def validate(self) -> list[ComponentValidation]:
        """Run all op-amp validation checks."""
        results = []
        results.append(self._check_vcc_range())
        results.append(self._check_vee_connection())
        for channel in ["A", "B"]:
            results.extend(self._check_channel_connectivity(channel))
            results.append(self._check_channel_feedback(channel))
        return results

    def _check_vcc_range(self) -> ComponentValidation:
        """Check VCC is within recommended range (3V-32V)."""
        vcc_pin = self.component.pin_by_number("8")
        if not vcc_pin or not vcc_pin.net:
            return ComponentValidation(
                check="op_amp_vcc_range",
                status="ERROR",
                summary="VCC pin (pin 8) not connected",
            )

        voltage = voltage_for_net(vcc_pin.net, self.design)
        if voltage is None:
            return ComponentValidation(
                check="op_amp_vcc_range",
                status="WARN",
                summary=f"Cannot infer VCC voltage from net '{vcc_pin.net}'",
            )

        if voltage < 3.0:
            return ComponentValidation(
                check="op_amp_vcc_range",
                status="ERROR",
                summary=f"VCC voltage {voltage:g}V is below minimum 3V",
            )
        if voltage > 32.0:
            return ComponentValidation(
                check="op_amp_vcc_range",
                status="ERROR",
                summary=f"VCC voltage {voltage:g}V exceeds maximum 32V",
            )

        return ComponentValidation(
            check="op_amp_vcc_range",
            status="PASS",
            summary=f"VCC voltage {voltage:g}V within range 3V-32V",
        )

    def _check_vee_connection(self) -> ComponentValidation:
        """Check VEE/GND is connected to ground."""
        vee_pin = self.component.pin_by_number("4")
        if not vee_pin or not vee_pin.net:
            return ComponentValidation(
                check="op_amp_vee_connection",
                status="ERROR",
                summary="VEE/GND pin (pin 4) not connected",
            )

        net_upper = vee_pin.net.upper()
        ground_nets = {"GND", "AGND", "DGND", "PGND", "HV_GND", "SGND"}
        if net_upper in ground_nets:
            return ComponentValidation(
                check="op_amp_vee_connection",
                status="PASS",
                summary=f"VEE/GND connected to '{vee_pin.net}'",
            )

        return ComponentValidation(
            check="op_amp_vee_connection",
            status="WARN",
            summary=f"VEE/GND connected to '{vee_pin.net}' (not a recognized ground net)",
        )

    def _check_channel_connectivity(self, channel: str) -> list[ComponentValidation]:
        """Check IN+, IN-, OUT connectivity for a channel."""
        pin_nums = {
            "A": {"plus": "3", "minus": "2", "out": "1"},
            "B": {"plus": "5", "minus": "6", "out": "7"},
        }[channel]

        results = []
        for pin_type, pin_num in pin_nums.items():
            pin = self.component.pin_by_number(pin_num)
            check_name = (
                f"op_amp_in_{channel.lower()}_{pin_type}_connectivity"
                if pin_type in ("plus", "minus")
                else f"op_amp_out_{channel.lower()}_connectivity"
            )

            if not pin or not pin.net:
                results.append(
                    ComponentValidation(
                        check=check_name,
                        status="ERROR",
                        summary=f"Channel {channel} {pin_type} pin (pin {pin_num}) not connected",
                    )
                )
            else:
                results.append(
                    ComponentValidation(
                        check=check_name,
                        status="PASS",
                        summary=f"Channel {channel} {pin_type} pin connected to '{pin.net}'",
                    )
                )

        return results

    def _check_channel_feedback(self, channel: str) -> ComponentValidation:
        """Check if channel has feedback path (output connected to inverting input through passive network)."""
        pin_nums = {
            "A": {"out": "1", "in_minus": "2"},
            "B": {"out": "7", "in_minus": "6"},
        }[channel]

        out_pin = self.component.pin_by_number(pin_nums["out"])
        in_minus_pin = self.component.pin_by_number(pin_nums["in_minus"])

        if not out_pin or not out_pin.net:
            return ComponentValidation(
                check=f"op_amp_{channel.lower()}_feedback",
                status="ERROR",
                summary=f"Channel {channel} output pin not connected; cannot verify feedback",
            )

        if not in_minus_pin or not in_minus_pin.net:
            return ComponentValidation(
                check=f"op_amp_{channel.lower()}_feedback",
                status="ERROR",
                summary=f"Channel {channel} inverting input not connected; cannot verify feedback",
            )

        out_net_name = out_pin.net
        in_minus_net_name = in_minus_pin.net

        # Direct connection (voltage follower)
        if out_net_name == in_minus_net_name:
            return ComponentValidation(
                check=f"op_amp_{channel.lower()}_feedback",
                status="PASS",
                summary=f"Channel {channel} has direct feedback (voltage follower)",
            )

        # Trace through passive components (resistors)
        out_net = self.design.nets.get(out_net_name)
        in_minus_net = self.design.nets.get(in_minus_net_name)

        if not out_net or not in_minus_net:
            return ComponentValidation(
                check=f"op_amp_{channel.lower()}_feedback",
                status="ERROR",
                summary=f"Channel {channel} feedback path not found in netlist",
            )

        # Find components connected to output net (nodes are (refdes, pin_number) tuples)
        out_components = {node[0] for node in out_net.nodes}
        # Find components connected to inverting input net
        in_minus_components = {node[0] for node in in_minus_net.nodes}

        # Check for shared passive components (feedback resistor)
        shared = out_components & in_minus_components
        if shared:
            return ComponentValidation(
                check=f"op_amp_{channel.lower()}_feedback",
                status="PASS",
                summary=f"Channel {channel} has feedback through {', '.join(sorted(shared))}",
            )

        return ComponentValidation(
            check=f"op_amp_{channel.lower()}_feedback",
            status="ERROR",
            summary=f"Channel {channel} has no feedback path from output to inverting input",
        )


def validate_op_amp(
    component: Component,
    profile,
    design: Design,
) -> list[ComponentValidation]:
    """Entry point for LM358 validation."""
    validator = OpAmpValidator(component, design)
    return validator.validate()
