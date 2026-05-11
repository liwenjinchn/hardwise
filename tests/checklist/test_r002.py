from pathlib import Path

import pytest

from hardwise.adapters.base import ComponentRecord
from hardwise.adapters.kicad import parse_project
from hardwise.checklist.checks.r002_cap_voltage_derating import check, parse_rated_voltage


def _record(refdes: str, value: str = "") -> ComponentRecord:
    return ComponentRecord(
        refdes=refdes,
        value=value,
        footprint="",
        datasheet="",
        source_file=Path("/tmp/mock.kicad_sch"),
        source_kind="schematic",
    )


@pytest.mark.parametrize(
    "value, expected",
    [
        ("22uF/25V", 25.0),
        ("100µF/25V", 25.0),
        ("100uF / 25 V", 25.0),
        ("100uF/25v", 25.0),
        ("4.7uF/6.3V", 6.3),
        ("0.1uF/50V", 50.0),
        ("4.7nF", None),
        ("100nF", None),
        ("", None),
        ("0", None),
        ("100uF", None),
        # Bare "25V" with no slash separator should not match: the slash is the
        # convention that distinguishes a rated-voltage suffix from a unit.
        ("25V", None),
    ],
)
def test_parse_rated_voltage_branches(value: str, expected: float | None) -> None:
    assert parse_rated_voltage(value) == expected


def test_check_with_declared_voltage_returns_info_finding() -> None:
    findings = check([_record("C3", value="22uF/25V")])

    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "R002"
    assert f.severity == "info"
    assert f.refdes == "C3"
    assert "25" in f.message
    assert f.evidence_tokens, "info finding must still carry evidence"
    assert "20" in f.suggested_action  # 25 * 0.8


def test_check_without_voltage_returns_medium_finding() -> None:
    findings = check([_record("C1", value="100uF")])

    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "R002"
    assert f.severity == "medium"
    assert f.refdes == "C1"
    assert "100uF" in f.message
    assert "rated voltage" in f.message.lower()


def test_check_skips_zero_value_caps() -> None:
    """A `value="0"` cap is the KiCad DNF convention — should be skipped."""
    findings = check([_record("C4", value="0")])
    assert findings == []


def test_check_skips_empty_value_caps() -> None:
    findings = check([_record("C99", value="")])
    assert findings == []


def test_check_skips_non_capacitor_refdes() -> None:
    """R002 only applies to caps. Resistors/ICs must not generate findings here."""
    findings = check(
        [
            _record("R1", value="10k"),
            _record("U7", value="STM32F407"),
            _record("D2", value="1N4148"),
        ]
    )
    assert findings == []


def test_check_skips_virtual_kicad_markers() -> None:
    """`#PWR05` etc. start with `#` and are not real components."""
    findings = check([_record("#PWR05", value="GND")])
    assert findings == []


def test_check_on_pic_programmer_yields_six_medium_one_info() -> None:
    """Reality check against the public pic_programmer sample.

    Caps in pic_programmer: C1(100µF), C2(220uF), C3(22uF/25V), C4(0),
    C5(10nF), C6(100nF), C7(100nF), C9(220nF). C3 → info; C4 → skipped;
    others (6) → medium. Total = 7 findings."""
    registry = parse_project(Path("data/projects/pic_programmer"))
    findings = check(registry.schematic_records)

    by_severity: dict[str, set[str]] = {"info": set(), "medium": set()}
    for f in findings:
        assert f.rule_id == "R002"
        assert f.refdes is not None
        by_severity.setdefault(f.severity, set()).add(f.refdes)

    assert by_severity["info"] == {"C3"}
    assert by_severity["medium"] == {"C1", "C2", "C5", "C6", "C7", "C9"}
    assert len(findings) == 7
