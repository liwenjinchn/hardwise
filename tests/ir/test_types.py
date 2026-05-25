"""Tests for Pin / Component / Net / Design IR types."""

from __future__ import annotations

from hardwise.ir.types import Pin


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
