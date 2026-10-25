"""Explicit units of implemented profile facts, not inferred units for legacy data."""

VOLTAGES = {
    "vin",
    "vcc",
    "vdd",
    "vcca",
    "vccb",
    "vds",
    "vgs",
    "vceo",
    "vcbo",
    "vebo",
    "vb_vs",
    "input_output_voltage",
    "input_voltage",
    "voltage",
    "reverse_voltage",
    "working_peak_reverse_voltage",
    "working_standoff_voltage",
    "repetitive_peak_reverse_voltage",
    "dc_blocking_voltage",
    "rms_reverse_voltage",
    "breakdown_voltage_min",
    "breakdown_voltage_max",
    "clamping_voltage_max",
    "logic_input",
    "abs_max_voltage",
    "recommended_voltage_min",
    "recommended_voltage_max",
    "nominal_voltage",
    "vb_vs_abs_max",
    "minimum_voltage",
    "logic_high_min",
    "vcc_min",
    "vcc_max",
    "vdd_min",
    "vdd_max",
    "vdd_nominal",
    "vcca_min",
    "vcca_max",
    "vccb_min",
    "vccb_max",
    "vin_min",
    "vin_max",
    "vs_min",
    "vs_max",
    "fixed_output_voltage",
    "forward_voltage_max_1a",
    "forward_voltage_max_2a",
    "forward_voltage_max_3a",
    "forward_voltage_typical",
    "vgs_threshold_min",
    "vgs_threshold_max",
    "vgs_threshold_typ",
    "vgs_typical",
}
CURRENTS = {
    "iout",
    "iout_max",
    "id",
    "ic",
    "id_t_lt_5s",
    "id_tc_100c",
    "idm_pulsed",
    "average_forward_current",
    "forward_continuous_current",
    "forward_current",
    "body_diode_source_current",
    "current_per_pin",
    "output_current",
    "output_current_max_a",
    "non_repetitive_peak_forward_current",
    "non_repetitive_peak_surge_current",
    "peak_forward_surge_current",
    "recommended_current_max",
    "reverse_current_typical",
}


def expected_unit(pointer):
    key = pointer.rsplit("/", 1)[-1]
    if key in VOLTAGES:
        return "V"
    if key in CURRENTS:
        return "A"
    if key in {"power_dissipation", "peak_pulse_power_w"}:
        return "W"
    if key in {"tj", "junction_temperature_max"}:
        return "degC"
    if key.startswith("rds_on"):
        return "ohm"
    if key == "single_pulsed_avalanche_energy":
        return "J"
    if key == "reverse_recovery_time_ns":
        return "ns"
    if key == "page":
        return "page"
    if key == "channel_count":
        return "count"
    return None


def declaration_problem(field):
    if not field.subject.strip() or not field.unit.strip():
        return "字段主体和单位不能为空白。"
    expected = expected_unit(field.pointer)
    value = field.value
    if expected:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if field.unit != expected:
                return f"要求明确单位 {expected}，不能将其他单位数值直接送入规则。"
        elif isinstance(value, str) and field.unit == "text":
            # E.g. "internally limited" is preserved text, never a numeric limit.
            try:
                float(value)
            except ValueError:
                pass
            else:
                return "数值字符串必须规范成带单位的显式数值，不能由规则隐式转换。"
        else:
            return "数值前提必须为显式数值；布尔或数值字符串不能作物理量。"
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        return "数值字段尚无实施规则的单位合同，不能认证。"
    elif field.unit != ("boolean" if isinstance(value, bool) else "text"):
        return "文本/枚举/标识和布尔值必须使用相应非物理量类型。"
    if field.nature != "intrinsic":
        return "应用推荐和板级策略不能作为器件无条件硬限值。"
    for condition in field.conditions:
        if condition.kind == "unsupported" or (
            condition.kind == "dc_relation" and not field.pointer.startswith("/voltage_relations/")
        ):
            return "当前规则不支持此字段的适用条件。"
    key = field.pointer.rsplit("/", 1)[-1]
    if expected and isinstance(value, (int, float)) and not isinstance(value, bool):
        role = (
            "maximum"
            if field.pointer.startswith("/abs_max/") or key in {"abs_max_voltage", "vb_vs_abs_max"}
            else None
        )
        role = "minimum" if key.endswith("_min") or key == "minimum_voltage" else role
        role = "maximum" if key.endswith("_max") or "_max_" in key else role
        role = "typical" if any(word in key for word in ("typical", "_typ", "nominal")) else role
        if role and field.role != role:
            return f"此字段要求 {role} 角色，典型值不能冒充边界。"
    return None
