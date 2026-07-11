"""Tests for generic passive validation."""

from __future__ import annotations

from pathlib import Path

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.build import build_design_from_netlist
from hardwise.validation import generic_passive, value_parsing
from hardwise.validation.generic_passive import validate_generic_passive
from hardwise.validation.value_parsing import (
    parse_capacitance_f,
    parse_current_rating_amps,
    parse_ferrite_impedance_ohms,
    parse_power_watts,
    parse_rated_voltage,
    parse_resistance_ohms,
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
    assert parse_current_rating_amps("10uH 2A").amps == 2.0
    assert parse_current_rating_amps("120R 500mA").amps == 0.5
    assert parse_ferrite_impedance_ohms("120R@100MHz 500mA").ohms == 120.0
    assert parse_ferrite_impedance_ohms("BLM18PG121SN1") is None


def test_generic_passive_preserves_legacy_value_parser_exports() -> None:
    assert generic_passive.ParsedResistance is value_parsing.ParsedResistance
    assert generic_passive.ParsedCurrentRating is value_parsing.ParsedCurrentRating
    assert generic_passive.ParsedImpedance is value_parsing.ParsedImpedance
    assert generic_passive.parse_capacitance_f is value_parsing.parse_capacitance_f
    assert generic_passive.parse_rated_voltage is value_parsing.parse_rated_voltage
    assert generic_passive.parse_resistance_ohms is value_parsing.parse_resistance_ohms
    assert generic_passive.parse_power_watts is value_parsing.parse_power_watts
    assert generic_passive.parse_current_rating_amps is value_parsing.parse_current_rating_amps
    assert (
        generic_passive.parse_ferrite_impedance_ohms is value_parsing.parse_ferrite_impedance_ohms
    )


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

    margin = next(
        check for check in validation.component_checks if check.check == "capacitor_voltage_margin"
    )
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

    power = next(
        check for check in validation.component_checks if check.check == "resistor_power_estimate"
    )
    assert validation.status == "WARN"
    assert power.status == "WARN"
    assert "Zero-ohm link bridges distinct inferred rails" in power.summary


def test_generic_inductor_validates_value_without_topology_claims(tmp_path: Path) -> None:
    design, _bom, report = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'IND' ! 6.8uH 2A ; L1
$NETS
  'SW_NODE' ; L1.1
  'VOUT' ; L1.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
L1,1,6.8uH 2A,Fixture,IND-6R8
""",
    )

    validation = validate_generic_passive(
        design.components["L1"], report.rows_by_refdes["L1"], design, "inductor"
    )

    assert validation.status == "PASS"
    assert validation.profile_part_number == "GENERIC_INDUCTOR"
    checks = {check.check: check for check in validation.component_checks}
    assert checks["inductor_value_parse"].status == "PASS"
    assert checks["inductor_package_presence"].status == "PASS"
    assert checks["inductor_current_rating_token"].status == "PASS"
    assert "buck_inductor" not in checks
    assert (
        "saturation suitability were not checked" in checks["inductor_current_rating_token"].summary
    )


def test_generic_ferrite_warns_when_impedance_is_not_explicit(tmp_path: Path) -> None:
    design, _bom, report = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'FB0603' ! BLM18PG121SN1 ; FB1
$NETS
  'VDD' ; FB1.1
  'VDD_FILT' ; FB1.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
FB1,1,BLM18PG121SN1,Murata,BLM18PG121SN1
""",
    )

    validation = validate_generic_passive(
        design.components["FB1"], report.rows_by_refdes["FB1"], design, "ferrite"
    )

    assert validation.status == "WARN"
    assert validation.profile_part_number == "GENERIC_FERRITE"
    checks = {check.check: check for check in validation.component_checks}
    assert checks["ferrite_impedance_parse"].status == "WARN"
    assert checks["ferrite_package_presence"].status == "PASS"
    assert checks["ferrite_current_rating_token"].status == "PASS"
    assert "could not be parsed deterministically" in checks["ferrite_impedance_parse"].summary


def test_project_index_treats_passives_as_generic_validated(tmp_path: Path) -> None:
    design, bom, report = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'C0402' ! 0.1uF 25V ; C1
  ! 'R0402' ! 10K 1/16W ; R1
  ! 'IND' ! 6.8uH ; L1
  ! 'FB0603' ! BLM18PG121SN1 ; FB1
  ! 'SOP8' ! UNKNOWN_IC ; U1
$NETS
  'P3V3' ; C1.1, R1.1, L1.1, FB1.1, U1.1
  'GND' ; C1.2, R1.2, L1.2, FB1.2, U1.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
C1,1,0.1uF 25V,Fixture,GW_CAPACITOR
R1,1,10K 1/16W,Fixture,GW_RESISTOR
L1,1,6.8uH,Fixture,IND-6R8
FB1,1,BLM18PG121SN1,Murata,BLM18PG121SN1
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
    assert rows["L1"].match_status == "generic_passive"
    assert rows["FB1"].match_status == "generic_passive"
    assert rows["U1"].validation is None
    assert len(index.validated_rows) == 4
    assert {group.identity for group in profile_gap_groups(index)} == {"UNKNOWN_IC"}
