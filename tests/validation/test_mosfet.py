"""Tests for IRF540N N-channel MOSFET validation.

The load-bearing cases are the high-side ones: they prove Vgs is measured
gate-to-source, not gate-to-ground. The old validator measured the gate
against ground and would false-ERROR a healthy bootstrapped high-side gate.
"""

from pathlib import Path

import pytest

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.build import build_design_from_netlist
from hardwise.ir.profile import DatasheetProfile
from hardwise.validation.component import validate_component_against_profile


@pytest.fixture
def mosfet_profile() -> DatasheetProfile:
    """Load IRF540N profile."""
    return DatasheetProfile.load(Path("data/datasheet_profiles/irf540n.json"))


def _design(net_name: str, bom_name: str):
    netlist = parse_allegro_netlist(Path(f"tests/fixtures/allegro/{net_name}"))
    bom = parse_bom(Path(f"tests/fixtures/allegro/{bom_name}"))
    design = build_design_from_netlist(netlist)
    return apply_bom_to_design(design, match_bom_to_design(bom, design))


@pytest.fixture
def lowside_design():
    """Low-side FET: gate +10V, drain +48V, source GND."""
    return _design("irf540n_mosfet.net", "irf540n_mosfet_bom.csv")


@pytest.fixture
def highside_design():
    """High-side FET: source on the SW switch node, drain on +48V rail."""
    return _design("irf540n_highside.net", "irf540n_highside_bom.csv")


def test_lowside_nominal_all_pass(mosfet_profile, lowside_design):
    """Low-side FET: Vgs = 10V - 0V = 10V, Vds = 48V - 0V = 48V. All pass."""
    component = lowside_design.components["Q1"]
    results = validate_component_against_profile(component, mosfet_profile, lowside_design)

    assert results.status == "PASS"
    check_names = {c.check for c in results.component_checks}
    assert check_names == {
        "mosfet_gate_connectivity",
        "mosfet_drain_connectivity",
        "mosfet_source_connectivity",
        "mosfet_vgs_rating",
        "mosfet_vds_rating",
    }
    vgs = next(c for c in results.component_checks if c.check == "mosfet_vgs_rating")
    assert vgs.status == "PASS"
    assert "gate 10 V - source 0 V" in vgs.summary
    assert vgs.evidence == ["datasheet:irf540n.pdf#p1"]


def test_highside_vgs_uses_source_reference(mosfet_profile, highside_design):
    """The fix: source floats at 48V, gate at 58V -> Vgs = 10V (PASS).

    The old gate-to-ground logic would read the gate as 58V and false-ERROR
    against the +-20V abs max. Measuring against the source proves Vgs = 10V.
    """
    highside_design.nets["SW"].voltage_hint = 48.0
    highside_design.nets["BST_GATE"].voltage_hint = 58.0
    component = highside_design.components["Q1"]
    results = validate_component_against_profile(component, mosfet_profile, highside_design)

    vgs = next(c for c in results.component_checks if c.check == "mosfet_vgs_rating")
    assert vgs.status == "PASS"
    assert "gate 58 V - source 48 V" in vgs.summary
    # Vds = 48 (drain rail) - 48 (source switch node) = 0, well within 100V.
    vds = next(c for c in results.component_checks if c.check == "mosfet_vds_rating")
    assert vds.status == "PASS"


def test_highside_floating_source_warns_not_errors(mosfet_profile, highside_design):
    """No voltage hints: SW/BST_GATE net names don't parse to a voltage.

    The validator must WARN (Vgs unknowable), never assume the source is at
    ground and emit a false reading.
    """
    component = highside_design.components["Q1"]
    results = validate_component_against_profile(component, mosfet_profile, highside_design)

    vgs = next(c for c in results.component_checks if c.check == "mosfet_vgs_rating")
    assert vgs.status == "WARN"
    assert "ground" in vgs.summary.lower()


def test_vgs_overvoltage_errors(mosfet_profile, highside_design):
    """Real Vgs violation: gate 30V over a grounded source -> 30V > 20V abs max."""
    highside_design.nets["SW"].voltage_hint = 0.0
    highside_design.nets["BST_GATE"].voltage_hint = 30.0
    component = highside_design.components["Q1"]
    results = validate_component_against_profile(component, mosfet_profile, highside_design)

    assert results.status == "ERROR"
    vgs = next(c for c in results.component_checks if c.check == "mosfet_vgs_rating")
    assert vgs.status == "ERROR"
    assert "Vgs is 30 V" in vgs.summary


def test_negative_vds_magnitude_over_abs_max_errors(mosfet_profile, highside_design):
    """A reverse static drain-source stress must still compare by magnitude."""
    highside_design.nets["+48V"].voltage_hint = 0.0
    highside_design.nets["SW"].voltage_hint = 150.0
    highside_design.nets["BST_GATE"].voltage_hint = 160.0
    component = highside_design.components["Q1"]
    results = validate_component_against_profile(component, mosfet_profile, highside_design)

    vgs = next(c for c in results.component_checks if c.check == "mosfet_vgs_rating")
    vds = next(c for c in results.component_checks if c.check == "mosfet_vds_rating")
    assert results.status == "ERROR"
    assert vgs.status == "PASS"
    assert vds.status == "ERROR"
    assert "Vds is -150 V" in vds.summary
    assert "magnitude above abs max" in vds.summary


def test_routes_by_family_without_mpn_fallback(mosfet_profile, lowside_design):
    """Family dispatch must not depend on the profile part number."""
    component = lowside_design.components["Q1"]
    profile = mosfet_profile.model_copy(update={"part_number": "GENERIC_NFET"})
    results = validate_component_against_profile(component, profile, lowside_design)

    check_names = {c.check for c in results.component_checks}
    assert "mosfet_vgs_rating" in check_names


def test_gate_floating_errors(mosfet_profile, tmp_path):
    """ERROR: gate pin not connected."""
    netlist_content = """$PACKAGES
  ! 'TO220' ! IRF540N ; Q1
  ! 'R0805' ! 100R ; R_LOAD
$NETS
  '+48V' ; Q1.2, R_LOAD.1
  'GND' ; Q1.3, R_LOAD.2
$END
"""
    (tmp_path / "t.net").write_text(netlist_content)
    bom_content = """Reference,Value,Footprint,Description
Q1,IRF540N,TO220,N-channel MOSFET
R_LOAD,100R,0805,Load resistor
"""
    (tmp_path / "t_bom.csv").write_text(bom_content)

    netlist = parse_allegro_netlist(tmp_path / "t.net")
    bom = parse_bom(tmp_path / "t_bom.csv")
    design = build_design_from_netlist(netlist)
    design = apply_bom_to_design(design, match_bom_to_design(bom, design))

    component = design.components["Q1"]
    results = validate_component_against_profile(component, mosfet_profile, design)

    assert results.status == "ERROR"
    gate = next(c for c in results.component_checks if c.check == "mosfet_gate_connectivity")
    assert gate.status == "ERROR"
    assert "not connected" in gate.summary


def test_ln2312lt1g_profile_matches_public_sot23_pinout() -> None:
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/ln2312lt1g.json"))

    assert profile.recommended["topology_family"] == "mosfet"
    assert profile.abs_max["vds"] == 20.0
    assert profile.abs_max["vgs"] == 8.0
    assert profile.pin_function == {"1": "Gate", "2": "Source", "3": "Drain"}
    assert profile.pin_by_number("1").schematic_pin_aliases == ["G"]
    assert profile.pin_by_number("2").schematic_pin_aliases == ["S"]
    assert profile.pin_by_number("3").schematic_pin_aliases == ["D"]


def test_ln2312lt1g_lowside_validation_uses_existing_mosfet_rules(tmp_path) -> None:
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/ln2312lt1g.json"))
    netlist_content = """$PACKAGES
  ! 'SOT23' ! LN2312LT1G ; Q1
$NETS
  'P3V3' ; Q1.1
  'GND' ; Q1.2
  'P12V' ; Q1.3
$END
"""
    (tmp_path / "ln.net").write_text(netlist_content)
    bom_content = """Reference,Quantity,Value,Manufacturer,MPN
Q1,1,LN2312LT1G,LRC,LN2312LT1G
"""
    (tmp_path / "ln_bom.csv").write_text(bom_content)

    netlist = parse_allegro_netlist(tmp_path / "ln.net")
    bom = parse_bom(tmp_path / "ln_bom.csv")
    design = build_design_from_netlist(netlist)
    design = apply_bom_to_design(design, match_bom_to_design(bom, design))

    results = validate_component_against_profile(design.components["Q1"], profile, design)

    assert results.status == "PASS"
    assert {check.check for check in results.component_checks} == {
        "mosfet_gate_connectivity",
        "mosfet_drain_connectivity",
        "mosfet_source_connectivity",
        "mosfet_vgs_rating",
        "mosfet_vds_rating",
    }


def test_ln2312lt1g_validation_resolves_schematic_pin_aliases() -> None:
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/ln2312lt1g.json"))
    design = _design(
        "ln2312lt1g_symbol_alias.net",
        "ln2312lt1g_symbol_alias_bom.csv",
    )

    results = validate_component_against_profile(design.components["Q9"], profile, design)

    assert results.status == "PASS"
    assert [(pin.pin_number, pin.pin_name, pin.net, pin.status) for pin in results.pin_results] == [
        ("1", "Gate", "P3V3_GATE", "PASS"),
        ("2", "Source", "GND", "PASS"),
        ("3", "Drain", "P12V", "PASS"),
    ]
    vgs = next(check for check in results.component_checks if check.check == "mosfet_vgs_rating")
    assert vgs.status == "PASS"
    assert "gate 3.3 V - source 0 V" in vgs.summary
    assert vgs.evidence == ["datasheet:s-ln2312lt1g.pdf#p1"]


def test_l2n7002klt1g_profile_matches_public_sot23_pinout() -> None:
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/l2n7002klt1g.json"))

    assert profile.review_status == "ready"
    assert profile.part_number == "L2N7002KLT1G"
    assert profile.part_number_aliases == ["L2N7002KLT3G"]
    assert profile.recommended["topology_family"] == "mosfet"
    assert profile.recommended["polarity"] == "n_channel"
    assert profile.abs_max["vds"] == 60.0
    assert profile.abs_max["vgs"] == 20.0
    assert profile.abs_max["id"] == 0.32
    assert profile.pin_function == {"1": "Gate", "2": "Source", "3": "Drain"}
    assert profile.evidence["pin_function.1"] == "datasheet:l2n7002klt1g.pdf#p1"
    assert profile.evidence["abs_max.vds"] == "datasheet:l2n7002klt1g.pdf#p1"
    assert profile.evidence["abs_max.vgs"] == "datasheet:l2n7002klt1g.pdf#p1"


def test_l2n7002klt1g_lowside_validation_uses_existing_mosfet_rules(tmp_path) -> None:
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/l2n7002klt1g.json"))
    netlist_content = """$PACKAGES
  ! 'SOT23' ! L2N7002KLT1G ; Q1
$NETS
  'P3V3' ; Q1.1
  'GND' ; Q1.2
  'P12V' ; Q1.3
$END
"""
    (tmp_path / "l2.net").write_text(netlist_content)
    bom_content = """Reference,Quantity,Value,Manufacturer,MPN
Q1,1,L2N7002KLT1G,LRC,L2N7002KLT1G
"""
    (tmp_path / "l2_bom.csv").write_text(bom_content)

    netlist = parse_allegro_netlist(tmp_path / "l2.net")
    bom = parse_bom(tmp_path / "l2_bom.csv")
    design = build_design_from_netlist(netlist)
    design = apply_bom_to_design(design, match_bom_to_design(bom, design))

    results = validate_component_against_profile(design.components["Q1"], profile, design)

    assert results.status == "PASS"
    assert {check.check for check in results.component_checks} == {
        "mosfet_gate_connectivity",
        "mosfet_drain_connectivity",
        "mosfet_source_connectivity",
        "mosfet_vgs_rating",
        "mosfet_vds_rating",
    }
    vgs = next(check for check in results.component_checks if check.check == "mosfet_vgs_rating")
    assert vgs.status == "PASS"
    assert "gate 3.3 V - source 0 V" in vgs.summary
    assert vgs.evidence == ["datasheet:l2n7002klt1g.pdf#p1"]


def test_pe537ba_profile_matches_public_pdfn_pinout() -> None:
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/pe537ba.json"))

    assert profile.review_status == "ready"
    assert profile.part_number == "PE537BA"
    assert profile.recommended["topology_family"] == "mosfet"
    assert profile.recommended["polarity"] == "p_channel"
    assert profile.abs_max["vds"] == 30.0
    assert profile.abs_max["vgs"] == 25.0
    assert profile.abs_max["id"] == 33.0
    assert profile.abs_max["idm_pulsed"] == 100.0
    assert profile.abs_max["power_dissipation"] == 16.7
    assert profile.pin_function == {
        "1": "Source",
        "2": "Source",
        "3": "Source",
        "4": "Gate",
        "5": "Drain",
        "6": "Drain",
        "7": "Drain",
        "8": "Drain",
    }
    assert profile.pin_by_number("4").name == "Gate"
    assert profile.pin_by_number("1").name == "Source"
    assert profile.pin_by_number("5").name == "Drain"
    assert profile.evidence["pin_function.4"] == "datasheet:pe537ba.pdf#p1"
    assert profile.evidence["abs_max.vds"] == "datasheet:pe537ba.pdf#p1"
    assert profile.evidence["abs_max.vgs"] == "datasheet:pe537ba.pdf#p1"


def test_pe537ba_p_channel_highside_warns_when_drain_voltage_unknown(tmp_path) -> None:
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/pe537ba.json"))
    netlist_content = """$PACKAGES
  ! 'PDFN33' ! PE537BA ; Q13
$NETS
  'P12V' ; Q13.1, Q13.2, Q13.3
  'P3V3' ; Q13.4
  'LOAD' ; Q13.5, Q13.6, Q13.7, Q13.8
$END
"""
    (tmp_path / "pe.net").write_text(netlist_content)
    bom_content = """Reference,Quantity,Value,Manufacturer,MPN
Q13,1,PE537BA,NIKO-SEM,PE537BA
"""
    (tmp_path / "pe_bom.csv").write_text(bom_content)

    netlist = parse_allegro_netlist(tmp_path / "pe.net")
    bom = parse_bom(tmp_path / "pe_bom.csv")
    design = build_design_from_netlist(netlist)
    design = apply_bom_to_design(design, match_bom_to_design(bom, design))

    results = validate_component_against_profile(design.components["Q13"], profile, design)

    assert results.status == "WARN"
    assert [(pin.pin_number, pin.pin_name, pin.net, pin.status) for pin in results.pin_results] == [
        ("4", "Gate", "P3V3", "PASS"),
        ("1", "Source", "P12V", "PASS"),
        ("5", "Drain", "LOAD", "PASS"),
    ]
    vgs = next(check for check in results.component_checks if check.check == "mosfet_vgs_rating")
    vds = next(check for check in results.component_checks if check.check == "mosfet_vds_rating")
    assert vgs.status == "PASS"
    assert "gate 3.3 V - source 12 V" in vgs.summary
    assert vgs.evidence == ["datasheet:pe537ba.pdf#p1"]
    assert vds.status == "WARN"
    assert "Not assuming ground" in vds.summary
