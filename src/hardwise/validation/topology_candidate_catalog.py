"""Explicit atomic/group rule inventory; never discover the denominator from output."""

from hardwise.validation.candidate_coverage import RuleCatalog, RuleDefinition

# Versions refer to the existing algorithm before isolation/approval wrappers.
FAMILIES = {
    "buck": {
        "buck_output_topology": ("1",),
        "buck_inductor": ("3",),
        "buck_freewheel_diode": ("1", "2"),
    },
    "half_bridge_gate_driver": {
        "gate_driver_vcc": ("2", "3"),
        "gate_driver_hin": ("1",),
        "gate_driver_lin": ("1",),
        "gate_driver_ho_gate_load": ("1",),
        "gate_driver_lo_gate_load": ("1",),
        "gate_driver_vs_switch_node": ("1",),
        "gate_driver_bootstrap": ("2",),
        "gate_driver_vb_vs_voltage": ("3",),
    },
    "mcu_basic": {
        "mcu_vdd_vdda_rail": ("2", "3"),
        "mcu_vbat_rail": ("2", "3"),
        "mcu_nrst": ("3",),
        "mcu_boot0": ("3",),
        "mcu_swdio": ("1",),
        "mcu_swclk": ("1",),
        "mcu_pa0": ("1",),
        "mcu_pa10": ("1",),
    },
    "i2c_mux": {
        "i2c_mux_vdd": ("2", "3"),
        "i2c_mux_upstream_bus": ("1",),
        "i2c_mux_control_pins": ("1",),
        "i2c_mux_channel_pairs": ("1",),
    },
    "diode": {
        "diode_cathode_connectivity": ("1",),
        "diode_anode_connectivity": ("1",),
        "diode_reverse_voltage": ("3",),
        "led_indicator_polarity": ("3",),
        "led_current_limit": ("2",),
        "tvs_terminal_1_connectivity": ("1",),
        "tvs_terminal_2_connectivity": ("1",),
        "tvs_terminal_separation": ("2",),
        "tvs_working_standoff": ("3",),
    },
    "mosfet": {
        "mosfet_gate_connectivity": ("1",),
        "mosfet_drain_connectivity": ("1",),
        "mosfet_source_connectivity": ("1",),
        "mosfet_vgs_rating": ("3",),
        "mosfet_vds_rating": ("3",),
    },
    "bjt": {
        "bjt_base_connectivity": ("1",),
        "bjt_collector_connectivity": ("1",),
        "bjt_emitter_connectivity": ("1",),
        "bjt_vebo_rating": ("3",),
        "bjt_vceo_rating": ("3",),
    },
    "shift_register_piso": {
        "shift_register_load_fanout": ("1",),
        "shift_register_clock_fanout": ("1",),
        "shift_register_clock_enable": ("3",),
        "shift_register_serial_chain": ("2",),
    },
    "i2c_level_shift_repeater": {
        "i2c_repeater_enable": ("3",),
        "i2c_repeater_port_a_pair": ("1",),
        "i2c_repeater_port_b_pair": ("1",),
    },
}
GROUP_SCOPES = {
    "i2c_mux_upstream_bus": "Aggregate connection check of SCL and SDA only",
    "i2c_mux_control_pins": "Aggregate connection check of RESET, A0, A1 and A2 only",
    "i2c_mux_channel_pairs": "Aggregate pair-completeness check across the eight declared channels",
    "buck_freewheel_diode": "External freewheel candidate or declared integrated synchronous path; not diode suitability",
    "buck_inductor": "Aggregate candidate value/path check, conditional selection may remain unknown",
    "gate_driver_bootstrap": "Aggregate bootstrap branch observation, not bootstrap function certification",
}
TOPOLOGY_CATALOG = RuleCatalog(
    version="hardwise.topology_candidates.v1",
    rules=tuple(
        RuleDefinition(
            rule_id="topology." + check,
            version="1",
            object_kind="component",
            scope=GROUP_SCOPES.get(
                check, "Existing bounded " + check + " assessment only; not full function"
            ),
        )
        for rules in FAMILIES.values()
        for check in rules
    ),
)


def selected_rules(profile):
    family = str(profile.recommended.get("topology_family", "")).lower()
    if family not in FAMILIES:
        raise ValueError("Family is not registered in this topology catalog")
    checks = FAMILIES[family]
    if family == "diode":
        role = str(profile.recommended.get("diode_role", "")).lower()
        if role == "bidirectional_tvs":
            checks = {k: v for k, v in checks.items() if k.startswith("tvs_")}
        else:
            checks = {
                k: v
                for k, v in checks.items()
                if k.startswith("diode_") or (role == "led_indicator" and k.startswith("led_"))
            }
    return family, checks
