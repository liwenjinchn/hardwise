"""Tests for Pin / Component / Net / Design IR types."""

from __future__ import annotations

from hardwise.ir.types import Component, Pin


def test_pin_minimal_construction() -> None:
    """Pin built with required fields only — optional fields default sensibly."""
    pin = Pin(
        number="1",
        name="Vin",
        electrical_type="power_in",
        is_nc=False,
    )
    assert pin.number == "1"
    assert pin.name == "Vin"
    assert pin.electrical_type == "power_in"
    assert pin.is_nc is False
    assert pin.net is None
    assert pin.datasheet_function is None
    assert pin.findings == []


def test_pin_with_all_optional_fields() -> None:
    """Pin built with every field set."""
    pin = Pin(
        number="A2",
        name="GPIO_A2",
        electrical_type="bidirectional",
        is_nc=False,
        net="LED_DRIVE",
        datasheet_function="GPIO with internal pull-up",
    )
    assert pin.net == "LED_DRIVE"
    assert pin.datasheet_function == "GPIO with internal pull-up"


def test_pin_nc_flag_true() -> None:
    """Pin marked as no-connect — schematic NC marker present."""
    pin = Pin(
        number="3",
        name="NC",
        electrical_type="no_connect",
        is_nc=True,
    )
    assert pin.is_nc is True


def test_pin_findings_default_is_independent_list() -> None:
    """Each Pin gets its own findings list (no shared-default-list bug)."""
    p1 = Pin(number="1", name="A", electrical_type="input", is_nc=False)
    p2 = Pin(number="2", name="B", electrical_type="input", is_nc=False)
    p1.findings.append("sentinel")  # type: ignore[arg-type]
    assert p2.findings == []


def test_component_minimal_construction() -> None:
    """Component with only the required ``refdes`` and ``value``."""
    c = Component(refdes="U1", value="L7805")
    assert c.refdes == "U1"
    assert c.value == "L7805"
    assert c.package is None
    assert c.part_number is None
    assert c.manufacturer is None
    assert c.datasheet_path is None
    assert c.datasheet_profile is None
    assert c.pins == []
    assert c.properties == {}
    assert c.findings == []
    assert c.decision is None


def test_component_pin_by_number_returns_pin() -> None:
    """``pin_by_number()`` returns the Pin whose number matches."""
    c = Component(
        refdes="U1",
        value="L7805",
        pins=[
            Pin(number="1", name="Vin", electrical_type="power_in", is_nc=False),
            Pin(number="2", name="GND", electrical_type="power_in", is_nc=False),
            Pin(number="3", name="Vout", electrical_type="power_out", is_nc=False),
        ],
    )
    pin = c.pin_by_number("2")
    assert pin is not None
    assert pin.name == "GND"


def test_component_pin_by_number_returns_none_when_missing() -> None:
    """``pin_by_number()`` returns None when no pin matches."""
    c = Component(refdes="U1", value="L7805")
    assert c.pin_by_number("99") is None


def test_component_pin_by_name_returns_pin() -> None:
    """``pin_by_name()`` returns the Pin whose name matches (exact match)."""
    c = Component(
        refdes="U1",
        value="L7805",
        pins=[
            Pin(number="1", name="Vin", electrical_type="power_in", is_nc=False),
        ],
    )
    pin = c.pin_by_name("Vin")
    assert pin is not None
    assert pin.number == "1"


def test_component_pin_by_name_returns_none_when_missing() -> None:
    """``pin_by_name()`` returns None when no pin matches."""
    c = Component(refdes="U1", value="L7805")
    assert c.pin_by_name("VBUS") is None


def test_component_decision_literal_accepts_pass_warn_fail() -> None:
    """``decision`` field accepts only the three V2 verdicts."""
    Component(refdes="U1", value="L7805", decision="pass")
    Component(refdes="U1", value="L7805", decision="warn")
    Component(refdes="U1", value="L7805", decision="fail")
