"""Tests for deterministic voltage hints parsed from net names."""

from __future__ import annotations

import pytest

from hardwise.validation.net_voltage import parse_voltage_hint


@pytest.mark.parametrize(
    ("net_name", "expected_voltage"),
    [
        ("P3V3_STBY", 3.3),
        ("P1V8", 1.8),
        ("P12V", 12.0),
        ("VCC_3V3", 3.3),
        ("VDD_1V8", 1.8),
    ],
)
def test_parse_voltage_hint_parses_supported_rail_names(
    net_name: str,
    expected_voltage: float,
) -> None:
    hint = parse_voltage_hint(net_name)

    assert hint.found is True
    assert hint.voltage == expected_voltage
    assert hint.rule_token == f"rule:net_voltage_name#{net_name}"


def test_parse_voltage_hint_returns_structured_unknown_for_signal_net() -> None:
    hint = parse_voltage_hint("I2C_SCL")

    assert hint.found is False
    assert hint.voltage is None
    assert hint.rule_token is None
    assert hint.reason == "No voltage hint found in net name."
