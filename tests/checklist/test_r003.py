"""Tests for R003 — NC pin handling (EDA-only stage)."""

from pathlib import Path

from hardwise.adapters.base import NcPinRecord
from hardwise.checklist.checks.r003_nc_pin_handling import check


def _nc_pin(
    refdes: str = "U1",
    pin_number: str = "3",
    pin_name: str = "NC",
    pin_electrical_type: str = "passive",
) -> NcPinRecord:
    return NcPinRecord(
        refdes=refdes,
        pin_number=pin_number,
        pin_name=pin_name,
        pin_electrical_type=pin_electrical_type,
        source_file=Path("/tmp/mock.kicad_sch"),
    )


def test_check_produces_medium_finding_per_nc_pin() -> None:
    pins = [_nc_pin("U1", "3"), _nc_pin("U2", "5"), _nc_pin("J1", "4")]
    findings = check(pins)
    assert len(findings) == 3
    for f in findings:
        assert f.rule_id == "R003"
        assert f.severity == "medium"


def test_check_empty_input_returns_empty() -> None:
    assert check([]) == []


def test_finding_evidence_tokens_present() -> None:
    findings = check([_nc_pin("U1", "3")])
    assert len(findings) == 1
    assert findings[0].evidence_tokens
    assert "sch:" in findings[0].evidence_tokens[0]


def test_finding_message_contains_pin_info() -> None:
    findings = check([_nc_pin("U1", "3", "NC", "input")])
    f = findings[0]
    assert "U1" in f.message
    assert "pin 3" in f.message
    assert "NC" in f.message
    assert "input" in f.message


def test_finding_refdes_is_set() -> None:
    findings = check([_nc_pin("J1", "9")])
    assert findings[0].refdes == "J1"


def test_check_on_pic_programmer_nc_pins() -> None:
    from hardwise.adapters.kicad import parse_project

    registry = parse_project(Path("data/projects/pic_programmer"))
    findings = check(registry.nc_pins)
    assert len(findings) == 77
    refdes_set = {f.refdes for f in findings}
    assert "J1" in refdes_set
    assert "U4" in refdes_set
