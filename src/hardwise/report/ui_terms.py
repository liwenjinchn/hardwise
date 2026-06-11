"""User-facing Chinese labels for validator UI terms."""

from __future__ import annotations

import re

STATUS_LABELS = {
    "matched": "已匹配",
    "no_result": "无本地档案",
    "manual_needed": "需人工确认",
    "ambiguous": "多候选",
    "not_requested": "未配置资料索引",
    "not_validated": "未验证",
    "generic_passive": "通用被动件检查",
}

IDENTITY_KIND_LABELS = {
    "mpn": "料号",
    "value": "型号值",
    "part_number": "料号",
    "part_like_value": "型号值",
    "passive_value": "参数值",
    "connector_or_mechanical": "连接/结构件",
    "missing": "缺失",
}

FAMILY_LABELS = {
    "capacitor": "电容",
    "connector": "连接器",
    "diode": "二极管",
    "ferrite": "磁珠",
    "ic": "IC",
    "inductor": "电感",
    "mechanical": "结构件",
    "resistor": "电阻",
    "test_point": "测试点",
    "transistor": "晶体管",
    "crystal": "晶振",
    "fuse": "保险丝",
    "switch": "开关",
    "relay": "继电器",
    "transformer": "变压器",
    "battery": "电池",
    "unknown": "未知",
}

GENERIC_PASSIVE_TERM_LABELS = {
    "capacitor": "电容",
    "resistor": "电阻",
    "inductor": "电感",
    "ferrite bead": "磁珠",
    "Capacitance": "电容值",
    "Resistance": "电阻值",
    "Inductance": "电感值",
    "Ferrite impedance": "磁珠阻抗",
}

PROFILE_PART_LABELS = {
    "GENERIC_CAPACITOR": "通用电容检查",
    "GENERIC_RESISTOR": "通用电阻检查",
    "GENERIC_INDUCTOR": "通用电感检查",
    "GENERIC_FERRITE": "通用磁珠检查",
}

PIN_CATEGORY_LABELS = {
    "analog_input": "模拟输入",
    "analog_output": "模拟输出",
    "bias_supply": "偏置电源",
    "boot_mode": "启动模式",
    "bootstrap_supply": "自举电源",
    "debug": "调试接口",
    "enable": "使能",
    "feedback": "反馈",
    "gate_output": "栅极输出",
    "generic_capacitor_terminal": "通用电容端子",
    "generic_ferrite_terminal": "通用磁珠端子",
    "generic_inductor_terminal": "通用电感端子",
    "generic_resistor_terminal": "通用电阻端子",
    "gpio": "GPIO",
    "ground": "地",
    "i2c_channel_clock": "I2C 通道时钟",
    "i2c_channel_data": "I2C 通道数据",
    "i2c_upstream_clock": "I2C 上游时钟",
    "i2c_upstream_data": "I2C 上游数据",
    "logic_input": "逻辑输入",
    "open_collector_output": "开漏输出",
    "power_good": "电源良好信号",
    "power_input": "电源输入",
    "power_output": "电源输出",
    "reset": "复位",
    "switch_node": "开关节点",
    "switch_output": "开关输出",
}

CHECK_LABELS = {
    "buck_output_topology": "Buck 输出拓扑",
    "buck_inductor": "Buck 电感",
    "buck_freewheel_diode": "Buck 续流二极管",
    "capacitor_package_presence": "电容封装字段",
    "capacitor_rated_voltage_parse": "电容额定电压解析",
    "capacitor_value_parse": "电容值解析",
    "capacitor_voltage_margin": "电容电压裕量",
    "connector_ground_connectivity": "连接器地脚连接",
    "connector_power_voltage": "连接器电源电压",
    "diode_reverse_voltage": "二极管反向耐压",
    "gate_driver_bootstrap": "栅极驱动自举路径",
    "gate_driver_hin": "栅极驱动 HIN 输入",
    "gate_driver_lin": "栅极驱动 LIN 输入",
    "gate_driver_ho_gate_load": "HO 栅极负载",
    "gate_driver_lo_gate_load": "LO 栅极负载",
    "gate_driver_vcc": "栅极驱动 VCC",
    "gate_driver_vs_switch_node": "栅极驱动 VS 开关节点",
    "i2c_mux_address": "I2C mux 地址脚",
    "i2c_mux_channel_pairs": "I2C mux 通道对",
    "i2c_mux_reset": "I2C mux 复位脚",
    "i2c_mux_upstream_bus": "I2C mux 上游总线",
    "i2c_mux_vdd": "I2C mux VDD",
    "ferrite_current_rating_token": "磁珠电流 token",
    "ferrite_impedance_parse": "磁珠阻抗解析",
    "ferrite_package_presence": "磁珠封装字段",
    "inductor_current_rating_token": "电感电流 token",
    "inductor_package_presence": "电感封装字段",
    "inductor_value_parse": "电感值解析",
    "led_current_limit": "LED 限流",
    "led_indicator_polarity": "LED 极性",
    "mcu_boot0": "MCU BOOT0 默认状态",
    "mcu_nrst": "MCU NRST 复位网络",
    "mcu_supply": "MCU 供电",
    "mcu_swdio": "MCU SWDIO 调试线",
    "mcu_swclk": "MCU SWCLK 调试线",
    "mosfet_vds_rating": "MOSFET VDS 耐压",
    "mosfet_vgs_rating": "MOSFET VGS 耐压",
    "profile_review_status": "器件档案审核状态",
    "resistor_package_presence": "电阻封装字段",
    "resistor_power_estimate": "电阻功耗估算",
    "resistor_value_parse": "电阻值解析",
    "tvs_working_standoff": "TVS 工作反向电压",
}

PROFILE_GROUP_LABELS = {
    "abs_max": "绝对最大额定",
    "recommended": "推荐/应用条件",
}

PROFILE_FACT_LABELS = {
    "abs_max.average_forward_current": "平均正向电流",
    "abs_max.breakdown_voltage_max": "击穿电压上限",
    "abs_max.breakdown_voltage_min": "击穿电压下限",
    "abs_max.body_diode_source_current": "体二极管源极电流",
    "abs_max.clamping_voltage_max": "钳位电压上限",
    "abs_max.current_per_pin": "单引脚电流",
    "abs_max.forward_continuous_current": "连续正向电流",
    "abs_max.forward_current": "正向电流",
    "abs_max.ic": "集电极电流",
    "abs_max.id": "漏极电流",
    "abs_max.id_t_lt_5s": "短时漏极电流",
    "abs_max.idm_pulsed": "脉冲漏极电流",
    "abs_max.input_output_voltage": "输入/输出电压",
    "abs_max.input_voltage": "输入电压",
    "abs_max.iout": "输出电流",
    "abs_max.junction_temperature_max": "结温上限",
    "abs_max.logic_input": "逻辑输入电压",
    "abs_max.non_repetitive_peak_forward_current": "非重复峰值正向电流",
    "abs_max.on_off": "ON/OFF 控制电压",
    "abs_max.output_current": "输出电流",
    "abs_max.peak_forward_surge_current": "峰值浪涌正向电流",
    "abs_max.peak_pulse_power_w": "峰值脉冲功率",
    "abs_max.power_dissipation": "功耗",
    "abs_max.repetitive_peak_reverse_voltage": "重复峰值反向电压",
    "abs_max.reverse_voltage": "反向电压",
    "abs_max.tj": "结温",
    "abs_max.vb_vs": "VB-VS 自举电压",
    "abs_max.vcbo": "VCBO 耐压",
    "abs_max.vcc": "VCC 电源电压",
    "abs_max.vcca": "VCCA 电源电压",
    "abs_max.vccb": "VCCB 电源电压",
    "abs_max.vceo": "VCEO 耐压",
    "abs_max.vdd": "VDD 电源电压",
    "abs_max.vds": "VDS 耐压",
    "abs_max.vebo": "VEBO 耐压",
    "abs_max.vgs": "VGS 耐压",
    "abs_max.vin": "输入电压",
    "abs_max.voltage": "电压",
    "abs_max.working_standoff_voltage": "工作反向电压",
    "recommended.boot0": "BOOT0 默认状态",
    "recommended.boot0_default": "BOOT0 默认电平",
    "recommended.bootstrap": "自举电路",
    "recommended.bootstrap_diode": "自举二极管",
    "recommended.bootstrap_required": "需要自举",
    "recommended.buck_topology": "Buck 拓扑",
    "recommended.channel_count": "通道数量",
    "recommended.channel_pairs": "通道对",
    "recommended.clock_enable_pin": "时钟使能脚",
    "recommended.clock_pin": "时钟脚",
    "recommended.control_pins": "控制引脚",
    "recommended.debug_interface": "调试接口",
    "recommended.device_role": "器件角色",
    "recommended.diode_role": "二极管角色",
    "recommended.enable_pin": "使能脚",
    "recommended.external_freewheel_diode_required": "需要外部续流二极管",
    "recommended.fixed_output_voltage": "固定输出电压",
    "recommended.forward_voltage_max_3a": "3A 最大正向压降",
    "recommended.forward_voltage_typical": "典型正向压降",
    "recommended.freewheel_diode": "续流二极管",
    "recommended.freewheel_diode_type": "续流二极管类型",
    "recommended.gpio": "GPIO 引脚",
    "recommended.inductor": "电感选型",
    "recommended.inductor_max_uh": "电感上限",
    "recommended.inductor_min_uh": "电感下限",
    "recommended.iout_max": "输出电流上限",
    "recommended.load_pin": "负载引脚",
    "recommended.logic_high_min": "逻辑高电平下限",
    "recommended.logic_inputs": "逻辑输入",
    "recommended.nrst": "复位网络",
    "recommended.output_current_max_a": "输出电流上限",
    "recommended.output_topology": "输出拓扑建议",
    "recommended.outputs": "输出端",
    "recommended.outputs_require_gate_load": "输出需要栅极负载",
    "recommended.polarity": "极性",
    "recommended.reference_net": "参考网络",
    "recommended.reset_network": "复位网络",
    "recommended.reverse_current_typical": "典型反向电流",
    "recommended.reverse_recovery_time_ns": "反向恢复时间",
    "recommended.serial_chain": "串行链路",
    "recommended.serial_input_pin": "串行输入脚",
    "recommended.serial_output_pin": "串行输出脚",
    "recommended.swd": "SWD 调试接口",
    "recommended.synchronous_rectification": "同步整流",
    "recommended.topology_family": "拓扑族",
    "recommended.upstream_bus": "上游总线",
    "recommended.validation_scope": "验证范围",
    "recommended.vbat": "VBAT 电源",
    "recommended.vcc": "VCC 电源",
    "recommended.vcc_max": "VCC 上限",
    "recommended.vcc_min": "VCC 下限",
    "recommended.vcca": "VCCA 电源",
    "recommended.vcca_max": "VCCA 上限",
    "recommended.vcca_min": "VCCA 下限",
    "recommended.vccb": "VCCB 电源",
    "recommended.vccb_max": "VCCB 上限",
    "recommended.vccb_min": "VCCB 下限",
    "recommended.vdd": "VDD 电源",
    "recommended.vdd_max": "VDD 上限",
    "recommended.vdd_min": "VDD 下限",
    "recommended.vdd_nominal": "VDD 标称电压",
    "recommended.vdd_vdda": "VDD/VDDA 电源",
    "recommended.vgs_threshold_max": "VGS 阈值上限",
    "recommended.vgs_threshold_min": "VGS 阈值下限",
    "recommended.vgs_typical": "典型 VGS",
    "recommended.vin_max": "输入电压上限",
    "recommended.vin_min": "输入电压下限",
    "recommended.voltage_range": "电压范围",
    "recommended.vs_max": "VS 上限",
    "recommended.vs_min": "VS 下限",
    "recommended.working_standoff_voltage": "工作反向电压",
}

LIMIT_LABELS = {
    "abs_max_voltage": "绝对最大电压",
    "expected_net": "期望网络",
    "logic_high_min": "逻辑高电平下限",
    "nominal_voltage": "标称电压",
    "recommended_current_max": "推荐电流上限",
    "recommended_voltage_max": "推荐电压上限",
    "recommended_voltage_min": "推荐电压下限",
    "vb_vs_abs_max": "VB-VS 绝对最大电压",
}

PROFILE_VALUE_LABELS = {
    "buck": "Buck 降压",
    "half_bridge_gate_driver": "半桥栅极驱动",
    "mcu_basic": "MCU 基础检查",
    "schottky": "肖特基",
    "low": "低电平",
    "pull-up or RC reset network": "上拉或 RC 复位网络",
    "internally limited": "内部限制",
}

REVIEW_STATUS_LABELS = {
    "ready": "已审定",
    "needs_review": "待复核",
    "draft": "草稿",
}

REASON_LABELS = {
    "No local profile part_number matched this BOM identity.": "本地还没有匹配这个 BOM 身份的器件档案。",
    "BOM item has no MPN or part-like value for profile matching.": "BOM 行缺少可用于匹配器件档案的 MPN/型号。",
    "No document index was provided.": "未提供本地资料索引。",
    "BOM item has no MPN or part-like value for document matching.": "BOM 行缺少可用于匹配资料的 MPN/型号。",
    "No local document-index row matched this BOM identity.": "本地资料索引里没有匹配这个 BOM 身份的条目。",
    "Multiple local document-index rows match this BOM identity.": "本地资料索引里有多个候选，需要人工确认。",
    "Exactly one local document-index row matched this BOM identity.": "本地资料索引已匹配到唯一条目。",
    "Generic passive validation ran from BOM value/package; no per-MPN datasheet profile is required.": (
        "已按 BOM 参数/封装执行通用被动件检查，不需要逐个阻容值建立器件档案。"
    ),
}

VALIDATION_SUMMARY_LABELS = {
    "Profiled pin is missing from the schematic/netlist component.": "器件档案中的引脚在原理图/netlist 器件里缺失。",
    "Profiled pin has no connected net in the schematic/netlist.": "器件档案中的引脚在原理图/netlist 里没有连接网络。",
    "Switch output pin is connected; peripheral topology checks run at component level.": "开关输出引脚已连接；外围拓扑在器件级检查。",
    "Pin is connected; family-specific topology checks run at component level.": "引脚已连接；器件族拓扑在器件级检查。",
    "Pin category has no deterministic V3.3 validation rule yet.": "这个引脚类别当前还没有确定性 V3.3 检查规则。",
    "Ground pin is connected to a recognized ground net.": "接地引脚已连接到识别出的地网。",
    "Ground pin is not connected to a recognized ground net.": "接地引脚没有连接到识别出的地网。",
    "Input voltage cannot be inferred from the net name or net metadata.": "无法从网络名或网络元数据确定输入电压。",
    "Input net voltage is within the structured profile limits.": "输入网络电压在结构化器件档案限制内。",
    "Output voltage cannot be compared deterministically yet.": "当前无法确定性比较输出电压。",
    "Output net voltage matches the structured profile nominal voltage.": "输出网络电压与结构化器件档案标称值一致。",
    "Feedback nominal voltage is not present in the structured profile.": "结构化器件档案没有给出反馈标称电压。",
    "Feedback net voltage cannot be inferred from the net name or net metadata.": "无法从网络名或网络元数据确定反馈网络电压。",
    "Feedback pin is connected to the fixed output rail.": "反馈引脚已连接到固定输出电源轨。",
    "Enable pin is connected, but its voltage cannot be inferred deterministically.": "使能引脚已连接，但无法确定性推断其电压。",
    "Enable pin is connected and its inferred voltage is within profile limits.": "使能引脚已连接，推断电压在器件档案限制内。",
    "Buck switch output pin is missing or has no connected net.": "Buck 开关输出引脚缺失或没有连接网络。",
    "Buck switch output net does not connect to an inductor.": "Buck 开关输出网络没有连接到电感。",
    "Buck switch output net does not connect to a freewheel diode.": "Buck 开关输出网络没有连接到续流二极管。",
    "Gate-driver VCC pin is missing or has no connected net.": "栅极驱动 VCC 引脚缺失或没有连接网络。",
    "Gate-driver VCC voltage cannot be inferred deterministically.": "无法确定性推断栅极驱动 VCC 电压。",
    "Gate-driver VS pin is missing or has no connected net.": "栅极驱动 VS 引脚缺失或没有连接网络。",
    "Gate-driver bootstrap pins VB/VS are missing or not connected.": "栅极驱动自举引脚 VB/VS 缺失或未连接。",
    "I2C mux reset and address pins are connected for deterministic review.": "I2C mux 的复位和地址引脚已连接，可进行确定性检查。",
    "Capacitor voltage margin cannot be checked because rated voltage is missing.": "电容额定电压缺失，无法检查电压裕量。",
    "Resistor power cannot be estimated because resistance is missing.": "电阻值缺失，无法估算功耗。",
    "No deterministic rail voltage was inferred for this capacitor; voltage-margin comparison was skipped without guessing.": (
        "没有推断出该电容的确定性电源轨电压；电压裕量比较已跳过，不做猜测。"
    ),
    "Resistor does not have two deterministic terminal voltages; power estimate was skipped without guessing current.": (
        "该电阻没有两个确定性的端子电压；功耗估算已跳过，不猜测电流。"
    ),
    "Generic capacitor terminal is not connected in the schematic/netlist.": "通用电容端子在原理图/netlist 中未连接。",
    "Generic resistor terminal is not connected in the schematic/netlist.": "通用电阻端子在原理图/netlist 中未连接。",
    "Generic inductor terminal is not connected in the schematic/netlist.": "通用电感端子在原理图/netlist 中未连接。",
    "Generic ferrite bead terminal is not connected in the schematic/netlist.": (
        "通用磁珠端子在原理图/netlist 中未连接。"
    ),
}

RECOMMENDED_TOPOLOGY_LABELS = {
    "Connect to the unregulated input rail.": "连接到未稳压输入电源轨。",
    "Place the input bypass capacitor close to VI and GND.": "输入旁路电容靠近 VI 和 GND 放置。",
    "Place input bypass capacitors close to VIN and GND.": "输入旁路电容靠近 VIN 和 GND 放置。",
    "Connect directly to the system ground return.": "直接连接到系统地回流。",
    "Connect directly to system ground.": "直接连接到系统地。",
    "Share the local return path with input and output bypass capacitors.": "与输入/输出旁路电容共用本地回流路径。",
    "Connect to the regulated 5 V rail.": "连接到稳压后的 5 V 电源轨。",
    "Place the output bypass capacitor close to VO and GND.": "输出旁路电容靠近 VO 和 GND 放置。",
    "Connect to the inductor and freewheel Schottky diode.": "连接到电感和续流肖特基二极管。",
    "Use an inductor in the profile recommended range.": "使用器件档案推荐范围内的电感。",
    "For the fixed 12 V version, connect feedback to the +12 V output rail.": "固定 12 V 版本的反馈脚连接到 +12V 输出轨。",
    "Drive low to enable; keep the control voltage within VIN limits.": "低电平使能；控制电压保持在 VIN 限制内。",
    "Connect to a local gate-drive supply rail.": "连接到本地栅极驱动电源轨。",
    "Decouple VCC to GND close to the driver.": "在驱动器附近将 VCC 对 GND 去耦。",
    "Drive from a controller PWM or logic output.": "由控制器 PWM 或逻辑输出驱动。",
    "Connect to the low-side MOSFET gate path.": "连接到低边 MOSFET 栅极路径。",
    "Connect to the bridge switch node and bootstrap capacitor return.": "连接到桥臂开关节点和自举电容回流端。",
    "Connect to the high-side MOSFET gate path.": "连接到高边 MOSFET 栅极路径。",
    "Connect to bootstrap diode supply path and bootstrap capacitor to VS.": "连接到自举二极管供电路径，并通过自举电容接到 VS。",
    "Connect to the system ground reference.": "连接到系统地参考。",
    "Connect to the 3.3 V rail with local decoupling.": "连接到 3.3 V 电源轨并做本地去耦。",
    "Connect only when the schematic intends to use this channel.": "仅在原理图需要使用该通道时连接。",
    "Connect to a named logic/PWM net when used.": "使用时连接到命名的逻辑/PWM 网络。",
    "Connect to the SWDIO signal on the debug connector.": "连接到调试连接器上的 SWDIO 信号。",
    "Connect to the SWCLK signal on the debug connector.": "连接到调试连接器上的 SWCLK 信号。",
    "Hold low for normal boot unless a programming mode is intentionally selected.": (
        "正常启动时保持低电平；只有有意进入编程模式时才改变。"
    ),
    "Tie to VDD when no separate backup battery is used.": "没有单独备份电池时接到 VDD。",
    "Provide a defined reset network such as pull-up and/or RC filtering.": (
        "提供明确的复位网络，例如上拉和/或 RC 滤波。"
    ),
}


def status_label(status: str) -> str:
    """Return a user-facing label for coverage/document status strings."""

    return STATUS_LABELS.get(status, status)


def identity_kind_label(kind: str) -> str:
    """Return a user-facing label for normalized BOM identity kinds."""

    return IDENTITY_KIND_LABELS.get(kind, kind)


def family_label(family: str) -> str:
    """Return a user-facing label for suggested component families."""

    return FAMILY_LABELS.get(family, family)


def profile_part_label(part_number: str) -> str:
    """Return a readable label for synthetic and real profile identities."""

    return PROFILE_PART_LABELS.get(part_number, part_number)


def pin_category_label(category: str) -> str:
    """Return a readable label for profile pin categories."""

    return PIN_CATEGORY_LABELS.get(category, category)


def check_label(check: str) -> str:
    """Return a readable label for deterministic component check names."""

    return CHECK_LABELS.get(check, check)


def profile_group_label(group: str) -> str:
    """Return a readable label for profile fact groups."""

    return PROFILE_GROUP_LABELS.get(group, group)


def profile_fact_label(group: str, key: str) -> str:
    """Return a readable label for structured profile fact keys."""

    claim_key = f"{group}.{key}" if group else key
    return PROFILE_FACT_LABELS.get(claim_key, key)


def profile_claim_label(claim_key: str) -> str:
    """Return a readable label for evidence-ledger claim keys."""

    if claim_key in PROFILE_FACT_LABELS:
        return PROFILE_FACT_LABELS[claim_key]
    if claim_key.startswith("pins."):
        return f"引脚 {claim_key.split('.', 1)[1]}"
    if claim_key.startswith("pin_function."):
        return f"引脚 {claim_key.split('.', 1)[1]} 功能"
    if "." in claim_key:
        group, _, key = claim_key.partition(".")
        fact = profile_fact_label(group, key)
        if fact != key:
            return fact
    return claim_key


def limit_label(key: str) -> str:
    """Return a readable label for per-pin limit keys."""

    return LIMIT_LABELS.get(key, key)


def profile_value_label(value: object) -> str:
    """Return a readable value label without changing the underlying fact."""

    if isinstance(value, bool):
        return "是" if value else "否"
    text = str(value)
    return PROFILE_VALUE_LABELS.get(text, text)


def review_status_label(status: str) -> str:
    """Return a readable label for profile review status strings."""

    return REVIEW_STATUS_LABELS.get(status, status)


def extraction_model_label(model: str) -> str:
    """Return a readable label for profile extraction metadata."""

    if model.startswith("deterministic-"):
        return "确定性结构化抽取"
    if model.startswith("manual-"):
        return "人工结构化档案"
    if model.startswith("claude-"):
        return "模型辅助结构化抽取"
    return model


def reason_label(reason: str) -> str:
    """Return a localized reason while preserving unknown diagnostic text."""

    return REASON_LABELS.get(reason, reason)


def validation_summary_label(summary: str) -> str:
    """Return Chinese display text for common deterministic validation summaries."""

    if summary in VALIDATION_SUMMARY_LABELS:
        return VALIDATION_SUMMARY_LABELS[summary]

    for pattern, replacement in _VALIDATION_PATTERNS:
        match = pattern.fullmatch(summary)
        if match:
            return replacement(match)

    translated = _replace_known_clauses(summary)
    if translated != summary:
        return translated
    return summary


def recommended_topology_label(text: str) -> str:
    """Return Chinese display text for common profile topology notes."""

    return RECOMMENDED_TOPOLOGY_LABELS.get(text, text)


def _replace_known_clauses(summary: str) -> str:
    translated = summary
    for source, target in _CLAUSE_LABELS.items():
        translated = translated.replace(source, target)
    if translated != summary and translated.endswith("."):
        translated = translated[:-1] + "。"
    return translated


_CLAUSE_LABELS = {
    "Buck inductor path runs from switch net ": "Buck 电感路径：从开关网络 ",
    " to fixed output rail ": " 到固定输出电源轨 ",
    "Freewheel diode path runs from switch net ": "续流二极管路径：从开关网络 ",
    " to ground return ": " 到地回流 ",
    "exact MOSFET gate pin role is not proven by this schematic-only check.": (
        "该原理图级检查不能证明精确的 MOSFET 栅极引脚角色。"
    ),
    "exact switch-node pin role is not proven by this schematic-only check.": (
        "该原理图级检查不能证明精确的开关节点引脚角色。"
    ),
    "is not obviously a logic/PWM signal.": "不明显是逻辑/PWM 信号。",
}


_VALIDATION_PATTERNS = [
    (
        re.compile(r"Input net voltage ([^ ]+) V exceeds abs max ([^ ]+) V\."),
        lambda match: f"输入网络电压 {match.group(1)} V 超过绝对最大值 {match.group(2)} V。",
    ),
    (
        re.compile(r"Input net voltage ([^ ]+) V is below recommended min ([^ ]+) V\."),
        lambda match: f"输入网络电压 {match.group(1)} V 低于推荐下限 {match.group(2)} V。",
    ),
    (
        re.compile(r"Input net voltage ([^ ]+) V is above recommended max ([^ ]+) V\."),
        lambda match: f"输入网络电压 {match.group(1)} V 高于推荐上限 {match.group(2)} V。",
    ),
    (
        re.compile(r"Output net voltage ([^ ]+) V differs from nominal ([^ ]+) V\."),
        lambda match: f"输出网络电压 {match.group(1)} V 与标称值 {match.group(2)} V 不一致。",
    ),
    (
        re.compile(r"Feedback net voltage ([^ ]+) V differs from fixed output ([^ ]+) V\."),
        lambda match: f"反馈网络电压 {match.group(1)} V 与固定输出 {match.group(2)} V 不一致。",
    ),
    (
        re.compile(r"Enable net voltage ([^ ]+) V exceeds abs max ([^ ]+) V\."),
        lambda match: f"使能网络电压 {match.group(1)} V 超过绝对最大值 {match.group(2)} V。",
    ),
    (
        re.compile(r"Inductor ([^ ]+) is ([^ ]+) uH, below the profile minimum ([^ ]+) uH\. (.*)"),
        lambda match: (
            f"电感 {match.group(1)} 为 {match.group(2)} uH，低于器件档案下限 "
            f"{match.group(3)} uH。{_replace_known_clauses(match.group(4))}"
        ),
    ),
    (
        re.compile(r"Inductor ([^ ]+) is ([^ ]+) uH, above the profile maximum ([^ ]+) uH\. (.*)"),
        lambda match: (
            f"电感 {match.group(1)} 为 {match.group(2)} uH，高于器件档案上限 "
            f"{match.group(3)} uH。{_replace_known_clauses(match.group(4))}"
        ),
    ),
    (
        re.compile(r"Inductor ([^ ]+) value ([^ ]+) uH is within profile range\. (.*)"),
        lambda match: (
            f"电感 {match.group(1)} 的值 {match.group(2)} uH 在器件档案范围内。"
            f"{_replace_known_clauses(match.group(3))}"
        ),
    ),
    (
        re.compile(r"Inductor ([^ ]+) value cannot be parsed deterministically\. (.*)"),
        lambda match: f"电感 {match.group(1)} 的值无法确定性解析。{_replace_known_clauses(match.group(2))}",
    ),
    (
        re.compile(r"Freewheel diode ([^ ]+) \(([^)]+)\) is not a Schottky-style diode family\. (.*)"),
        lambda match: (
            f"续流二极管 {match.group(1)}（{match.group(2)}）不是肖特基类型。"
            f"{_replace_known_clauses(match.group(3))}"
        ),
    ),
    (
        re.compile(r"Freewheel diode ([^ ]+) \(([^)]+)\) type cannot be classified deterministically\. (.*)"),
        lambda match: (
            f"续流二极管 {match.group(1)}（{match.group(2)}）类型无法确定性分类。"
            f"{_replace_known_clauses(match.group(3))}"
        ),
    ),
    (
        re.compile(r"Gate-driver VCC is ([^ ]+) V, below profile minimum ([^ ]+) V\."),
        lambda match: f"栅极驱动 VCC 为 {match.group(1)} V，低于器件档案下限 {match.group(2)} V。",
    ),
    (
        re.compile(r"Gate-driver VCC is ([^ ]+) V, above profile maximum ([^ ]+) V\."),
        lambda match: f"栅极驱动 VCC 为 {match.group(1)} V，高于器件档案上限 {match.group(2)} V。",
    ),
    (
        re.compile(r"Gate-driver VCC net ([^ ]+) is within the profile supply range\."),
        lambda match: f"栅极驱动 VCC 网络 {match.group(1)} 在器件档案供电范围内。",
    ),
    (
        re.compile(r"Gate-driver ([^ ]+) input pin is missing or has no connected net\."),
        lambda match: f"栅极驱动 {match.group(1)} 输入引脚缺失或没有连接网络。",
    ),
    (
        re.compile(r"Gate-driver ([^ ]+) input is connected to logic/PWM net ([^.]+)\."),
        lambda match: f"栅极驱动 {match.group(1)} 输入连接到逻辑/PWM 网络 {match.group(2)}。",
    ),
    (
        re.compile(r"Gate-driver ([^ ]+) input is connected, but net ([^ ]+) is not obviously a logic/PWM signal\."),
        lambda match: f"栅极驱动 {match.group(1)} 输入已连接，但网络 {match.group(2)} 不明显是逻辑/PWM 信号。",
    ),
    (
        re.compile(r"Gate-driver ([^ ]+) input net ([^ ]+) has no other connected component\."),
        lambda match: f"栅极驱动 {match.group(1)} 输入网络 {match.group(2)} 没有连接到其他器件。",
    ),
    (
        re.compile(r"Gate-driver ([^ ]+) output pin is missing or has no connected net\."),
        lambda match: f"栅极驱动 {match.group(1)} 输出引脚缺失或没有连接网络。",
    ),
    (
        re.compile(r"Gate-driver ([^ ]+) output reaches Q-prefixed drive target\(s\): ([^;]+); (.*)"),
        lambda match: (
            f"栅极驱动 {match.group(1)} 输出可到达 Q 前缀驱动目标：{match.group(2)}；"
            f"{_replace_known_clauses(match.group(3))}"
        ),
    ),
    (
        re.compile(r"Gate-driver ([^ ]+) output net ([^ ]+) does not reach a Q-prefixed drive target\."),
        lambda match: f"栅极驱动 {match.group(1)} 输出网络 {match.group(2)} 没有到达 Q 前缀驱动目标。",
    ),
    (
        re.compile(r"Gate-driver VS net ([^ ]+) reaches two Q-prefixed devices; (.*)"),
        lambda match: f"栅极驱动 VS 网络 {match.group(1)} 到达两个 Q 前缀器件；{_replace_known_clauses(match.group(2))}",
    ),
    (
        re.compile(r"Gate-driver VS net ([^ ]+) reaches one Q-prefixed device only; (.*)"),
        lambda match: f"栅极驱动 VS 网络 {match.group(1)} 只到达一个 Q 前缀器件；{_replace_known_clauses(match.group(2))}",
    ),
    (
        re.compile(r"Gate-driver VS net ([^ ]+) does not reach a Q-prefixed switch target\."),
        lambda match: f"栅极驱动 VS 网络 {match.group(1)} 没有到达 Q 前缀开关目标。",
    ),
    (
        re.compile(r"Gate-driver bootstrap path lacks a capacitor between ([^ ]+) and ([^.]+)\."),
        lambda match: f"栅极驱动自举路径缺少位于 {match.group(1)} 与 {match.group(2)} 之间的电容。",
    ),
    (
        re.compile(r"Gate-driver bootstrap path lacks a diode feeding ([^.]+)\."),
        lambda match: f"栅极驱动自举路径缺少给 {match.group(1)} 供电的二极管。",
    ),
    (
        re.compile(r"Bootstrap diode ([^ ]+) \(([^)]+)\) is rated about ([^ ]+) V, below required ([^ ]+) V\."),
        lambda match: (
            f"自举二极管 {match.group(1)}（{match.group(2)}）额定值约 {match.group(3)} V，"
            f"低于所需 {match.group(4)} V。"
        ),
    ),
    (
        re.compile(r"MCU ([^ ]+) supply pin is missing or has no connected net\."),
        lambda match: f"MCU {match.group(1)} 供电脚缺失或没有连接网络。",
    ),
    (
        re.compile(r"MCU ([^ ]+) rail voltage on net ([^ ]+) cannot be inferred\."),
        lambda match: f"MCU {match.group(1)} 网络 {match.group(2)} 的电压无法推断。",
    ),
    (
        re.compile(r"MCU ([^ ]+) net ([^ ]+) is ([^ ]+) V, expected ([^ ]+) V\."),
        lambda match: f"MCU {match.group(1)} 网络 {match.group(2)} 为 {match.group(3)} V，期望 {match.group(4)} V。",
    ),
    (
        re.compile(r"MCU ([^ ]+) net ([^ ]+) is a valid ([^ ]+) V rail\."),
        lambda match: f"MCU {match.group(1)} 网络 {match.group(2)} 是有效的 {match.group(3)} V 电源轨。",
    ),
    (
        re.compile(r"MCU ([^ ]+) is connected to ([^,]+), expected ([^.]+)\."),
        lambda match: f"MCU {match.group(1)} 连接到了 {match.group(2)}，期望连接到 {match.group(3)}。",
    ),
    (
        re.compile(r"MCU ([^ ]+) is connected to expected debug net ([^.]+)\."),
        lambda match: f"MCU {match.group(1)} 已连接到期望的调试网络 {match.group(2)}。",
    ),
    (
        re.compile(r"MCU ([^ ]+) is connected to schematic net ([^.]+)\."),
        lambda match: f"MCU {match.group(1)} 已连接到原理图网络 {match.group(2)}。",
    ),
    (
        re.compile(r"MCU NRST net ([^ ]+) has a recognizable reset pull/default network\."),
        lambda match: f"MCU NRST 网络 {match.group(1)} 有可识别的复位上拉/默认状态网络。",
    ),
    (
        re.compile(r"MCU BOOT0 net ([^ ]+) has a deterministic low default state\."),
        lambda match: f"MCU BOOT0 网络 {match.group(1)} 有确定性的默认低电平状态。",
    ),
    (
        re.compile(r"Generic (capacitor|resistor|inductor|ferrite bead) terminal is connected to ([^.]+)\."),
        lambda match: (
            f"通用{GENERIC_PASSIVE_TERM_LABELS[match.group(1)]}端子已连接到 "
            f"{match.group(2)}。"
        ),
    ),
    (
        re.compile(
            r"(Capacitance|Resistance|Inductance|Ferrite impedance) value was parsed "
            r"from BOM/component value '([^']+)'\."
        ),
        lambda match: (
            f"{GENERIC_PASSIVE_TERM_LABELS[match.group(1)]}已从 BOM/器件值 "
            f"'{match.group(2)}' 解析。"
        ),
    ),
    (
        re.compile(
            r"(Capacitance|Resistance|Inductance|Ferrite impedance) value could not "
            r"be parsed deterministically from '([^']+)'\."
        ),
        lambda match: (
            f"{GENERIC_PASSIVE_TERM_LABELS[match.group(1)]}无法从 "
            f"'{match.group(2)}' 确定性解析。"
        ),
    ),
    (
        re.compile(r"Capacitor rated voltage ([^ ]+) V was parsed from '([^']+)'\."),
        lambda match: f"已从 '{match.group(2)}' 解析出电容额定电压 {match.group(1)} V。",
    ),
    (
        re.compile(r"Capacitor rated voltage could not be parsed deterministically from '([^']+)'\."),
        lambda match: f"无法从 '{match.group(1)}' 确定性解析电容额定电压。",
    ),
    (
        re.compile(
            r"Generic (capacitor|resistor|inductor|ferrite bead) check has no "
            r"schematic package field to inspect\."
        ),
        lambda match: (
            f"通用{GENERIC_PASSIVE_TERM_LABELS[match.group(1)]}检查没有可读取的"
            "原理图封装字段。"
        ),
    ),
    (
        re.compile(
            r"Schematic package '([^']+)' is present for generic "
            r"(capacitor|resistor|inductor|ferrite bead) review\."
        ),
        lambda match: (
            f"原理图封装 '{match.group(1)}' 已用于通用"
            f"{GENERIC_PASSIVE_TERM_LABELS[match.group(2)]}检查。"
        ),
    ),
    (
        re.compile(
            r"Generic (inductor|ferrite bead) BOM/component value '([^']+)' has no "
            r"explicit current-rating token; current, ripple, and saturation "
            r"suitability were not checked\."
        ),
        lambda match: (
            f"通用{GENERIC_PASSIVE_TERM_LABELS[match.group(1)]} BOM/器件值 "
            f"'{match.group(2)}' 没有显式电流额定 token；未检查电流、纹波和饱和适用性。"
        ),
    ),
    (
        re.compile(
            r"Generic (inductor|ferrite bead) current-rating token ([^ ]+) "
            r"\(([^)]+) A\) was parsed from '([^']+)'; current, ripple, and "
            r"saturation suitability were not checked without topology/profile evidence\."
        ),
        lambda match: (
            f"已从 '{match.group(4)}' 解析出通用"
            f"{GENERIC_PASSIVE_TERM_LABELS[match.group(1)]}电流额定 token "
            f"{match.group(2)}（{match.group(3)} A）；没有拓扑/档案证据时不检查电流、纹波和饱和适用性。"
        ),
    ),
]
