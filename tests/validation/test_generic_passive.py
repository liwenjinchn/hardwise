"""Tests for generic passive validation."""

from __future__ import annotations

from pathlib import Path

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.build import build_design_from_netlist
from hardwise.validation.generic_passive import (
    parse_capacitance_f,
    parse_power_watts,
    parse_rated_voltage,
    parse_resistance_ohms,
    validate_generic_passive,
)
from hardwise.validation.profile_candidates import suggest_profile_candidates
from hardwise.validation.project_index import build_project_validation_index, profile_gap_groups


def _design_from_text(tmp_path: Path, netlist: str, bom_text: str):
    netlist_path = tmp_path / "fixture.net"
    bom_path = tmp_path / "fixture_bom.csv"
    netlist_path.write_text(netlist, encoding="utf-8")
    bom_path.write_text(bom_text, encoding="utf-8")
    registry = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(registry)
    report = match_bom_to_design(bom, design)
    return apply_bom_to_design(design, report), bom, report


def test_passive_value_parsers() -> None:
    assert parse_capacitance_f("0.1uF 25V") == 1e-7
    assert parse_rated_voltage("0.1uF 25V") == 25.0
    assert parse_resistance_ohms("4R7 1%").ohms == 4.7
    assert parse_resistance_ohms("10K 1/16W").ohms == 10_000.0
    assert parse_power_watts("10K 1/16W") == 0.0625
    assert parse_power_watts("10K 100mW") == 0.1


def test_generic_capacitor_voltage_margin_passes(tmp_path: Path) -> None:
    design, _bom, report = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'C0402' ! 0.1uF 25V ; C1
$NETS
  'P3V3' ; C1.1
  'GND' ; C1.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
C1,1,0.1uF 25V,Fixture,GW_CAPACITOR
""",
    )

    validation = validate_generic_passive(
        design.components["C1"], report.rows_by_refdes["C1"], design, "capacitor"
    )

    assert validation.status == "PASS"
    checks = {check.check: check for check in validation.component_checks}
    assert checks["capacitor_value_parse"].status == "PASS"
    assert checks["capacitor_rated_voltage_parse"].status == "PASS"
    assert checks["capacitor_voltage_margin"].status == "PASS"
    assert "25 V" in checks["capacitor_voltage_margin"].summary


def test_generic_capacitor_underrated_errors(tmp_path: Path) -> None:
    design, _bom, report = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'C0402' ! 0.1uF 6.3V ; C1
$NETS
  'P12V' ; C1.1
  'GND' ; C1.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
C1,1,0.1uF 6.3V,Fixture,GW_CAPACITOR
""",
    )

    validation = validate_generic_passive(
        design.components["C1"], report.rows_by_refdes["C1"], design, "capacitor"
    )

    margin = next(check for check in validation.component_checks if check.check == "capacitor_voltage_margin")
    assert validation.status == "ERROR"
    assert margin.status == "ERROR"
    assert "below inferred maximum terminal voltage 12 V" in margin.summary


def test_generic_resistor_zero_ohm_bridge_warns(tmp_path: Path) -> None:
    design, _bom, report = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'R0402' ! 0R 5% ; R1
$NETS
  'P3V3' ; R1.1
  'P1V8' ; R1.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
R1,1,0R 5%,Fixture,GW_RESISTOR
""",
    )

    validation = validate_generic_passive(
        design.components["R1"], report.rows_by_refdes["R1"], design, "resistor"
    )

    power = next(check for check in validation.component_checks if check.check == "resistor_power_estimate")
    assert validation.status == "WARN"
    assert power.status == "WARN"
    assert "Zero-ohm link bridges distinct inferred rails" in power.summary


def test_project_index_treats_passives_as_generic_validated(tmp_path: Path) -> None:
    design, bom, report = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'C0402' ! 0.1uF 25V ; C1
  ! 'R0402' ! 10K 1/16W ; R1
  ! 'SOP8' ! UNKNOWN_IC ; U1
$NETS
  'P3V3' ; C1.1, R1.1, U1.1
  'GND' ; C1.2, R1.2, U1.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
C1,1,0.1uF 25V,Fixture,GW_CAPACITOR
R1,1,10K 1/16W,Fixture,GW_RESISTOR
U1,1,UNKNOWN_IC,Fixture,UNKNOWN_IC
""",
    )
    candidates = suggest_profile_candidates(bom, Path("data/datasheet_profiles"))

    index = build_project_validation_index(
        design=design,
        bom=bom,
        bom_report=report,
        candidate_report=candidates,
        project_name="generic-passive",
        generated_at="2026-06-01T00:00:00+00:00",
        netlist_source="fixture.net",
        netlist_type="fixture",
    )

    rows = {row.refdes: row for row in index.rows}
    assert rows["C1"].match_status == "generic_passive"
    assert rows["R1"].match_status == "generic_passive"
    assert rows["U1"].validation is None
    assert len(index.validated_rows) == 2
    assert {group.identity for group in profile_gap_groups(index)} == {"UNKNOWN_IC"}
