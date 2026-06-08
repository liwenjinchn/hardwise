"""Tests for 2N3904 NPN BJT validation.

The load-bearing case is reverse B-E breakdown: emitter above base by more
than VEBO must ERROR even though a base-to-ground check would see 0 V and miss it.
"""

from pathlib import Path

import pytest

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.build import build_design_from_netlist
from hardwise.ir.profile import DatasheetProfile
from hardwise.validation.component import validate_component_against_profile


@pytest.fixture
def bjt_profile() -> DatasheetProfile:
    return DatasheetProfile.load(Path("data/datasheet_profiles/2n3904.json"))


@pytest.fixture
def mmbt3904_profile() -> DatasheetProfile:
    return DatasheetProfile.load(Path("data/datasheet_profiles/mmbt3904.json"))


def _design(net_name: str, bom_name: str):
    netlist = parse_allegro_netlist(Path(f"tests/fixtures/allegro/{net_name}"))
    bom = parse_bom(Path(f"tests/fixtures/allegro/{bom_name}"))
    design = build_design_from_netlist(netlist)
    return apply_bom_to_design(design, match_bom_to_design(bom, design))


@pytest.fixture
def lowside_design():
    design = _design("2n3904_bjt.net", "2n3904_bjt_bom.csv")
    design.nets["BASE_DRIVE"].voltage_hint = 0.7
    design.nets["COLLECTOR_RAIL"].voltage_hint = 12.0
    return design


@pytest.fixture
def emitter_reference_design():
    return _design("2n3904_bjt_emitter_reference.net", "2n3904_bjt_emitter_reference_bom.csv")


def test_lowside_nominal_all_pass(bjt_profile, lowside_design):
    component = lowside_design.components["Q2"]
    results = validate_component_against_profile(component, bjt_profile, lowside_design)

    assert results.status == "PASS"
    check_names = {c.check for c in results.component_checks}
    assert check_names == {
        "bjt_base_connectivity",
        "bjt_collector_connectivity",
        "bjt_emitter_connectivity",
        "bjt_vebo_rating",
        "bjt_vceo_rating",
    }
    vebo = next(c for c in results.component_checks if c.check == "bjt_vebo_rating")
    assert vebo.status == "PASS"
    assert "base 0.7 V - emitter 0 V" in vebo.summary
    assert vebo.evidence == ["datasheet:2n3904-d.pdf#p1"]


def test_non_ground_emitter_uses_emitter_reference(bjt_profile, emitter_reference_design):
    emitter_reference_design.nets["BASE_NODE"].voltage_hint = 12.7
    emitter_reference_design.nets["EMITTER_NODE"].voltage_hint = 12.0
    emitter_reference_design.nets["COLLECTOR_NODE"].voltage_hint = 24.0
    component = emitter_reference_design.components["Q2"]

    results = validate_component_against_profile(component, bjt_profile, emitter_reference_design)

    assert results.status == "PASS"
    vebo = next(c for c in results.component_checks if c.check == "bjt_vebo_rating")
    assert vebo.status == "PASS"
    assert "base 12.7 V - emitter 12 V" in vebo.summary
    vceo = next(c for c in results.component_checks if c.check == "bjt_vceo_rating")
    assert vceo.status == "PASS"
    assert "collector 24 V - emitter 12 V" in vceo.summary


def test_reverse_be_breakdown_errors_against_emitter_reference(
    bjt_profile,
    emitter_reference_design,
):
    """Emitter at +12V and base at 0V exceeds VEBO=6V.

    A base-to-ground check would read 0V and miss this. Emitter-referenced
    Vbe catches the reverse B-E breakdown risk.
    """
    emitter_reference_design.nets["BASE_NODE"].voltage_hint = 0.0
    emitter_reference_design.nets["EMITTER_NODE"].voltage_hint = 12.0
    emitter_reference_design.nets["COLLECTOR_NODE"].voltage_hint = 24.0
    component = emitter_reference_design.components["Q2"]

    results = validate_component_against_profile(component, bjt_profile, emitter_reference_design)

    assert results.status == "ERROR"
    vebo = next(c for c in results.component_checks if c.check == "bjt_vebo_rating")
    assert vebo.status == "ERROR"
    assert "emitter 12 V - base 0 V" in vebo.summary
    assert "VEBO abs max 6 V" in vebo.summary


def test_floating_base_or_emitter_warns_not_errors(bjt_profile, emitter_reference_design):
    emitter_reference_design.nets["COLLECTOR_NODE"].voltage_hint = 24.0
    component = emitter_reference_design.components["Q2"]

    results = validate_component_against_profile(component, bjt_profile, emitter_reference_design)

    assert results.status == "WARN"
    vebo = next(c for c in results.component_checks if c.check == "bjt_vebo_rating")
    assert vebo.status == "WARN"
    assert "not assuming emitter is ground" in vebo.summary.lower()


def test_vceo_overvoltage_errors(bjt_profile, lowside_design):
    lowside_design.nets["COLLECTOR_RAIL"].voltage_hint = 50.0
    component = lowside_design.components["Q2"]

    results = validate_component_against_profile(component, bjt_profile, lowside_design)

    assert results.status == "ERROR"
    vceo = next(c for c in results.component_checks if c.check == "bjt_vceo_rating")
    assert vceo.status == "ERROR"
    assert "VCEO abs max 40 V" in vceo.summary


def test_routes_by_family_without_mpn_fallback(bjt_profile, lowside_design):
    component = lowside_design.components["Q2"]
    profile = bjt_profile.model_copy(update={"part_number": "GENERIC_NPN"})

    results = validate_component_against_profile(component, profile, lowside_design)

    check_names = {c.check for c in results.component_checks}
    assert "bjt_vebo_rating" in check_names


def test_mmbt3904_profile_matches_public_sot23_pinout(mmbt3904_profile):
    assert mmbt3904_profile.pin_function["1"] == "Base"
    assert mmbt3904_profile.pin_function["2"] == "Emitter"
    assert mmbt3904_profile.pin_function["3"] == "Collector"
    assert [(pin.number, pin.name) for pin in mmbt3904_profile.pins] == [
        ("1", "Base"),
        ("2", "Emitter"),
        ("3", "Collector"),
    ]


def test_mmbt3904_sot23_nominal_all_pass(mmbt3904_profile, tmp_path):
    design = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'SOT23' ! MMBT3904 ; Q10
  ! 'R0402' ! 1K ; R_BASE
  ! 'R0402' ! 1K ; R_LOAD
$NETS
  'BASE_DRIVE' ; Q10.1, R_BASE.2
  '+3V3' ; R_BASE.1
  'GND' ; Q10.2
  'COLLECTOR_RAIL' ; Q10.3, R_LOAD.2
  '+12V' ; R_LOAD.1
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
Q10,1,MMBT3904,onsemi,MMBT3904
R_BASE,1,1K,Fixture,RES-1K
R_LOAD,1,1K,Fixture,RES-1K
""",
    )
    design.nets["BASE_DRIVE"].voltage_hint = 0.7
    design.nets["COLLECTOR_RAIL"].voltage_hint = 12.0

    results = validate_component_against_profile(design.components["Q10"], mmbt3904_profile, design)

    assert results.status == "PASS"
    assert results.component_counts_by_status == {"PASS": 5, "WARN": 0, "ERROR": 0}
    checks = {c.check: c for c in results.component_checks}
    assert checks["bjt_vebo_rating"].evidence == ["datasheet:mmbt3904lt1-d.pdf#p1"]
    assert "base 0.7 V - emitter 0 V" in checks["bjt_vebo_rating"].summary


def test_ss8050_profile_matches_public_to92_pinout() -> None:
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/ss8050.json"))

    assert profile.review_status == "ready"
    assert profile.part_number == "SS8050"
    assert profile.recommended["topology_family"] == "bjt"
    assert profile.recommended["polarity"] == "npn"
    assert profile.abs_max["vceo"] == 25.0
    assert profile.abs_max["vcbo"] == 40.0
    assert profile.abs_max["vebo"] == 6.0
    assert profile.abs_max["ic"] == 1.5
    assert profile.pin_function == {"1": "Emitter", "2": "Base", "3": "Collector"}
    assert profile.evidence["pin_function.1"] == "datasheet:ss8050-d.pdf#p1"
    assert profile.evidence["abs_max.vceo"] == "datasheet:ss8050-d.pdf#p1"
    assert profile.evidence["abs_max.vebo"] == "datasheet:ss8050-d.pdf#p1"


def test_ss8050_controller_stage_moves_to_l1_and_flags_missing_emitter() -> None:
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/ss8050.json"))
    design = _design(
        "mixed_controller_power_stage.net",
        "mixed_controller_power_stage_bom.csv",
    )

    results = validate_component_against_profile(design.components["Q12"], profile, design)

    assert results.status == "ERROR"
    assert [(pin.pin_number, pin.pin_name, pin.net, pin.status) for pin in results.pin_results] == [
        ("1", "Emitter", None, "ERROR"),
        ("2", "Base", "+24V_EN", "PASS"),
        ("3", "Collector", "GND", "PASS"),
    ]
    emitter = next(check for check in results.component_checks if check.check == "bjt_emitter_connectivity")
    assert emitter.status == "ERROR"
    assert "emitter pin is not connected" in emitter.summary


def _design_from_text(tmp_path: Path, netlist_content: str, bom_content: str):
    netlist_path = tmp_path / "test.net"
    netlist_path.write_text(netlist_content)
    bom_path = tmp_path / "test_bom.csv"
    bom_path.write_text(bom_content)

    netlist = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(netlist)
    return apply_bom_to_design(design, match_bom_to_design(bom, design))
