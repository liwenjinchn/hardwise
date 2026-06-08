"""Tests for SS34 Schottky diode validation."""

from pathlib import Path

import pytest

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.build import build_design_from_netlist
from hardwise.ir.profile import DatasheetProfile
from hardwise.validation.component import validate_component_against_profile


@pytest.fixture
def diode_profile() -> DatasheetProfile:
    """Load SS34 profile."""
    return DatasheetProfile.load(Path("data/datasheet_profiles/ss34.json"))


@pytest.fixture
def led_profile() -> DatasheetProfile:
    """Load LTST-C190KGKT LED indicator profile."""
    return DatasheetProfile.load(Path("data/datasheet_profiles/ltst-c190kgkt.json"))


@pytest.fixture
def tvs_profile() -> DatasheetProfile:
    """Load SMBJ24CA bidirectional TVS profile."""
    return DatasheetProfile.load(Path("data/datasheet_profiles/smbj24ca.json"))


@pytest.fixture
def bas316_profile() -> DatasheetProfile:
    """Load BAS316 small-signal diode profile."""
    return DatasheetProfile.load(Path("data/datasheet_profiles/bas316.json"))


@pytest.fixture
def smc15a_profile() -> DatasheetProfile:
    """Load 1.5SMC15A unidirectional TVS profile."""
    return DatasheetProfile.load(Path("data/datasheet_profiles/1_5smc15a.json"))


@pytest.fixture
def sm340af_profile() -> DatasheetProfile:
    """Load SM340AF Schottky rectifier profile."""
    return DatasheetProfile.load(Path("data/datasheet_profiles/sm340af.json"))


@pytest.fixture
def sd103aws_profile() -> DatasheetProfile:
    """Load SD103AWS-7-F Schottky diode profile."""
    return DatasheetProfile.load(Path("data/datasheet_profiles/sd103aws_7_f.json"))


@pytest.fixture
def n4007w_profile() -> DatasheetProfile:
    """Load 1N4007W general-purpose rectifier profile."""
    return DatasheetProfile.load(Path("data/datasheet_profiles/1n4007w.json"))


@pytest.fixture
def mbra210lt3g_profile() -> DatasheetProfile:
    """Load MBRA210LT3G Schottky rectifier profile."""
    return DatasheetProfile.load(Path("data/datasheet_profiles/mbra210lt3g.json"))


@pytest.fixture
def controller_power_stage_design():
    """Load mixed controller power-stage fixture."""
    netlist = parse_allegro_netlist(
        Path("tests/fixtures/allegro/mixed_controller_power_stage.net")
    )
    bom = parse_bom(Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"))
    design = build_design_from_netlist(netlist)
    return apply_bom_to_design(design, match_bom_to_design(bom, design))


@pytest.fixture
def diode_design():
    """Load diode fixture."""
    netlist = parse_allegro_netlist(Path("tests/fixtures/allegro/ss34_diode.net"))
    bom = parse_bom(Path("tests/fixtures/allegro/ss34_diode_bom.csv"))
    design = build_design_from_netlist(netlist)
    return apply_bom_to_design(design, match_bom_to_design(bom, design))


def test_ss34_nominal_all_pass(diode_profile, diode_design):
    """Nominal diode: cathode to +12V, anode to output."""
    component = diode_design.components["D1"]
    results = validate_component_against_profile(component, diode_profile, diode_design)

    assert results.status == "PASS"
    assert results.counts_by_status == {"PASS": 2, "WARN": 0, "ERROR": 0}
    assert results.component_counts_by_status == {"PASS": 3, "WARN": 0, "ERROR": 0}

    # Check specific validations
    check_names = {c.check for c in results.component_checks}
    assert "diode_cathode_connectivity" in check_names
    assert "diode_anode_connectivity" in check_names
    assert "diode_reverse_voltage" in check_names


def test_ss34_routes_by_family_without_mpn_fallback(diode_profile, diode_design):
    """Family dispatch should not depend on the profile part number."""
    component = diode_design.components["D1"]
    profile = diode_profile.model_copy(update={"part_number": "GENERIC_DIODE"})

    results = validate_component_against_profile(component, profile, diode_design)

    assert results.component_counts_by_status == {"PASS": 3, "WARN": 0, "ERROR": 0}


def test_ltst_c190kgkt_pinout_matches_public_pin_diagram(led_profile):
    assert led_profile.pin_function["1"] == "Cathode"
    assert led_profile.pin_function["2"] == "Anode"
    assert led_profile.pin_by_number("1").name == "Cathode"
    assert led_profile.pin_by_number("2").name == "Anode"


def test_smbj24ca_profile_matches_public_bidirectional_tvs(tvs_profile):
    assert tvs_profile.recommended["topology_family"] == "diode"
    assert tvs_profile.recommended["diode_role"] == "bidirectional_tvs"
    assert tvs_profile.recommended["working_standoff_voltage"] == 24.0
    assert tvs_profile.pin_function == {"1": "Terminal 1", "2": "Terminal 2"}
    assert [(pin.number, pin.name) for pin in tvs_profile.pins] == [
        ("1", "Terminal 1"),
        ("2", "Terminal 2"),
    ]


def test_bas316_profile_matches_public_sod323_pinout(bas316_profile):
    assert bas316_profile.recommended["topology_family"] == "diode"
    assert bas316_profile.recommended["diode_role"] == "small_signal_switching"
    assert bas316_profile.abs_max["reverse_voltage"] == 100.0
    assert bas316_profile.pin_function == {"1": "Cathode", "2": "Anode"}
    assert [(pin.number, pin.name) for pin in bas316_profile.pins] == [
        ("1", "Cathode"),
        ("2", "Anode"),
    ]


def test_bas316_nominal_reverse_voltage_passes(bas316_profile, tmp_path):
    design = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'SOD323' ! BAS316 ; D21
$NETS
  '+12V' ; D21.1
  'GND' ; D21.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
D21,1,BAS316,Nexperia,BAS316
""",
    )

    results = validate_component_against_profile(design.components["D21"], bas316_profile, design)

    assert results.status == "PASS"
    assert results.counts_by_status == {"PASS": 2, "WARN": 0, "ERROR": 0}
    assert results.component_counts_by_status == {"PASS": 3, "WARN": 0, "ERROR": 0}
    reverse = next(
        check for check in results.component_checks if check.check == "diode_reverse_voltage"
    )
    assert "within profile maximum 100 V" in reverse.summary


def test_bas316_reverse_voltage_overstress_errors(bas316_profile, tmp_path):
    design = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'SOD323' ! BAS316 ; D21
$NETS
  '+120V' ; D21.1
  'GND' ; D21.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
D21,1,BAS316,Nexperia,BAS316
""",
    )

    results = validate_component_against_profile(design.components["D21"], bas316_profile, design)

    reverse = next(
        check for check in results.component_checks if check.check == "diode_reverse_voltage"
    )
    assert results.status == "ERROR"
    assert reverse.status == "ERROR"
    assert "above profile maximum 100 V" in reverse.summary


def test_1_5smc15a_profile_matches_public_unidirectional_tvs(smc15a_profile):
    assert smc15a_profile.recommended["topology_family"] == "diode"
    assert smc15a_profile.recommended["diode_role"] == "unidirectional_tvs"
    assert smc15a_profile.recommended["working_standoff_voltage"] == 12.8
    assert smc15a_profile.abs_max["reverse_voltage"] == 12.8
    assert smc15a_profile.pin_function == {"K": "Cathode", "A": "Anode"}
    assert [(pin.number, pin.name) for pin in smc15a_profile.pins] == [
        ("K", "Cathode"),
        ("A", "Anode"),
    ]


def test_1_5smc15a_12v_rail_clamp_passes(smc15a_profile, tmp_path):
    design = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'DO214AB' ! 1.5SMC15A ; D26
$NETS
  '+12V' ; D26.K
  'GND' ; D26.A
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
D26,1,1.5SMC15A,Littelfuse,1.5SMC15A
""",
    )

    results = validate_component_against_profile(design.components["D26"], smc15a_profile, design)

    assert results.status == "PASS"
    reverse = next(
        check for check in results.component_checks if check.check == "diode_reverse_voltage"
    )
    assert reverse.status == "PASS"
    assert "within profile maximum 12.8 V" in reverse.summary


def test_sm340af_profile_matches_public_sma_fl_pinout(sm340af_profile):
    assert sm340af_profile.recommended["topology_family"] == "diode"
    assert sm340af_profile.recommended["diode_role"] == "schottky_rectifier"
    assert sm340af_profile.abs_max["reverse_voltage"] == 40.0
    assert sm340af_profile.pin_function == {"1": "Cathode", "2": "Anode"}
    assert [(pin.number, pin.name) for pin in sm340af_profile.pins] == [
        ("1", "Cathode"),
        ("2", "Anode"),
    ]


def test_sm340af_12v_reverse_voltage_passes(sm340af_profile, tmp_path):
    design = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'SMA-FL' ! SM340AF ; D27
$NETS
  '+12V' ; D27.1
  'GND' ; D27.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
D27,1,SM340AF SMA-FL,LRC,SM340AF SMA-FL
""",
    )

    results = validate_component_against_profile(design.components["D27"], sm340af_profile, design)

    assert results.status == "PASS"
    reverse = next(
        check for check in results.component_checks if check.check == "diode_reverse_voltage"
    )
    assert reverse.status == "PASS"
    assert "within profile maximum 40 V" in reverse.summary


def test_sd103aws_profile_matches_public_schottky_limits(sd103aws_profile):
    assert sd103aws_profile.recommended["topology_family"] == "diode"
    assert sd103aws_profile.recommended["diode_role"] == "schottky_barrier_switching"
    assert sd103aws_profile.abs_max["reverse_voltage"] == 40.0
    assert sd103aws_profile.pin_function == {"1": "Anode", "2": "Cathode"}
    assert [(pin.number, pin.name) for pin in sd103aws_profile.pins] == [
        ("1", "Anode"),
        ("2", "Cathode"),
    ]


def test_sd103aws_12v_reverse_voltage_passes(sd103aws_profile, tmp_path):
    design = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'SOD323' ! SD103AWS-7-F ; D36
$NETS
  'GND' ; D36.1
  '+12V' ; D36.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
D36,1,SD103AWS-7-F,Diodes Inc,SD103AWS-7-F
""",
    )

    results = validate_component_against_profile(design.components["D36"], sd103aws_profile, design)

    assert results.status == "PASS"
    reverse = next(
        check for check in results.component_checks if check.check == "diode_reverse_voltage"
    )
    assert reverse.status == "PASS"
    assert "within profile maximum 40 V" in reverse.summary


def test_1n4007w_profile_matches_public_rectron_limits(n4007w_profile):
    assert n4007w_profile.review_status == "ready"
    assert n4007w_profile.recommended["topology_family"] == "diode"
    assert n4007w_profile.recommended["diode_role"] == "general_purpose_rectifier"
    assert n4007w_profile.abs_max["reverse_voltage"] == 1000.0
    assert n4007w_profile.abs_max["average_forward_current"] == 1.0
    assert n4007w_profile.pin_function == {"1": "Cathode", "2": "Anode"}
    assert [(pin.number, pin.name) for pin in n4007w_profile.pins] == [
        ("1", "Cathode"),
        ("2", "Anode"),
    ]
    assert (
        n4007w_profile.evidence["abs_max.reverse_voltage"]
        == "datasheet:rectron_1n4001w-1n4007w.pdf#p1"
    )


def test_mbra210lt3g_profile_matches_public_onsemi_limits(mbra210lt3g_profile):
    assert mbra210lt3g_profile.review_status == "ready"
    assert mbra210lt3g_profile.recommended["topology_family"] == "diode"
    assert mbra210lt3g_profile.recommended["diode_role"] == "schottky_rectifier"
    assert mbra210lt3g_profile.abs_max["reverse_voltage"] == 10.0
    assert mbra210lt3g_profile.abs_max["average_forward_current"] == 2.0
    assert mbra210lt3g_profile.pin_function == {"1": "Cathode", "2": "Anode"}
    assert [(pin.number, pin.name) for pin in mbra210lt3g_profile.pins] == [
        ("1", "Cathode"),
        ("2", "Anode"),
    ]
    assert (
        mbra210lt3g_profile.evidence["pin_function.1"]
        == "datasheet:mbra210lt3-d.pdf#p5"
    )


def test_mixed_controller_diode_profiles_warn_without_topology_claim(
    n4007w_profile,
    mbra210lt3g_profile,
    controller_power_stage_design,
):
    profiles = {
        "D5": n4007w_profile,
        "D1": mbra210lt3g_profile,
    }

    for refdes, profile in profiles.items():
        results = validate_component_against_profile(
            controller_power_stage_design.components[refdes],
            profile,
            controller_power_stage_design,
        )
        checks = {check.check: check for check in results.component_checks}
        summaries = " ".join(check.summary for check in results.component_checks)

        assert results.status == "WARN"
        assert results.counts_by_status == {"PASS": 2, "WARN": 0, "ERROR": 0}
        assert results.component_counts_by_status == {"PASS": 2, "WARN": 1, "ERROR": 0}
        assert checks["diode_cathode_connectivity"].status == "PASS"
        assert checks["diode_anode_connectivity"].status == "PASS"
        assert checks["diode_reverse_voltage"].status == "WARN"
        assert "cannot be inferred from cathode/anode net names" in summaries
        assert "低于所需 24 V" not in summaries


def test_bidirectional_tvs_nominal_rail_clamp_passes(tvs_profile, tmp_path):
    design = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'DO214' ! SMBJ24CA ; D20
$NETS
  '+24V' ; D20.1
  'GND' ; D20.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
D20,1,SMBJ24CA,Littelfuse,SMBJ24CA
""",
    )

    results = validate_component_against_profile(design.components["D20"], tvs_profile, design)

    assert results.status == "PASS"
    assert results.counts_by_status == {"PASS": 2, "WARN": 0, "ERROR": 0}
    assert results.component_counts_by_status == {"PASS": 3, "WARN": 0, "ERROR": 0}
    standoff = next(
        check for check in results.component_checks if check.check == "tvs_working_standoff"
    )
    assert "clamps +24V to GND" in standoff.summary
    assert "within standoff 24 V" in standoff.summary


def test_bidirectional_tvs_rail_above_standoff_errors(tvs_profile, tmp_path):
    design = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'DO214' ! SMBJ24CA ; D20
$NETS
  '+36V' ; D20.1
  'GND' ; D20.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
D20,1,SMBJ24CA,Littelfuse,SMBJ24CA
""",
    )

    results = validate_component_against_profile(design.components["D20"], tvs_profile, design)

    standoff = next(
        check for check in results.component_checks if check.check == "tvs_working_standoff"
    )
    assert results.status == "ERROR"
    assert standoff.status == "ERROR"
    assert "above working standoff 24 V" in standoff.summary


def test_led_indicator_nominal_current_limited_path_passes(led_profile, tmp_path):
    design = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'LED0603' ! LTST-C190KGKT ; D10
  ! 'R0402' ! 330 ; RLED
$NETS
  '+3V3' ; D10.2
  'GND_LED' ; D10.1, RLED.1
  'GND' ; RLED.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
D10,1,LTST-C190KGKT,Lite-On,LTST-C190KGKT
RLED,1,330,Fixture,RES-330
""",
    )

    results = validate_component_against_profile(design.components["D10"], led_profile, design)

    assert results.status == "PASS"
    assert results.counts_by_status == {"PASS": 2, "WARN": 0, "ERROR": 0}
    assert results.component_counts_by_status == {"PASS": 5, "WARN": 0, "ERROR": 0}
    checks = {check.check: check for check in results.component_checks}
    assert checks["led_indicator_polarity"].status == "PASS"
    assert checks["led_current_limit"].status == "PASS"
    assert "series current-limit resistor RLED" in checks["led_current_limit"].summary
    assert "cathode branch GND_LED" in checks["led_current_limit"].summary


def test_led_indicator_missing_current_limit_errors(led_profile, tmp_path):
    design = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'LED0603' ! LTST-C190KGKT ; D10
$NETS
  '+3V3' ; D10.2
  'GND' ; D10.1
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
D10,1,LTST-C190KGKT,Lite-On,LTST-C190KGKT
""",
    )

    results = validate_component_against_profile(design.components["D10"], led_profile, design)

    assert results.status == "ERROR"
    check = next(check for check in results.component_checks if check.check == "led_current_limit")
    assert check.status == "ERROR"
    assert "no deterministic series current-limit resistor" in check.summary


def test_led_indicator_reversed_polarity_errors(led_profile, tmp_path):
    design = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'LED0603' ! LTST-C190KGKT ; D10
  ! 'R0402' ! 330 ; RLED
$NETS
  'GND' ; D10.2
  '+3V3_LED' ; D10.1, RLED.1
  '+3V3' ; RLED.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
D10,1,LTST-C190KGKT,Lite-On,LTST-C190KGKT
RLED,1,330,Fixture,RES-330
""",
    )

    results = validate_component_against_profile(design.components["D10"], led_profile, design)

    assert results.status == "ERROR"
    checks = {check.check: check for check in results.component_checks}
    assert checks["led_indicator_polarity"].status == "ERROR"
    assert "expected anode above cathode" in checks["led_indicator_polarity"].summary
    assert checks["led_current_limit"].status == "PASS"


def test_led_indicator_unrelated_rail_resistor_does_not_limit_current(led_profile, tmp_path):
    design = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'LED0603' ! LTST-C190KGKT ; D10
  ! 'R0402' ! 10K ; RPU
$NETS
  '+3V3' ; D10.2, RPU.1
  'GND' ; D10.1
  'STATUS_SENSE' ; RPU.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
D10,1,LTST-C190KGKT,Lite-On,LTST-C190KGKT
RPU,1,10K,Fixture,RES-10K
""",
    )

    results = validate_component_against_profile(design.components["D10"], led_profile, design)

    checks = {check.check: check for check in results.component_checks}
    assert checks["led_indicator_polarity"].status == "PASS"
    assert checks["led_current_limit"].status == "ERROR"
    assert "no deterministic series current-limit resistor" in checks["led_current_limit"].summary


def test_led_indicator_shared_resistor_summary_is_explicit(led_profile, tmp_path):
    design = _design_from_text(
        tmp_path,
        """$PACKAGES
  ! 'LED0603' ! LTST-C190KGKT ; D10, D11
  ! 'R0402' ! 330 ; RLED
$NETS
  '+3V3' ; D10.2, D11.2
  'GND_LED' ; D10.1, D11.1, RLED.1
  'GND' ; RLED.2
$END
""",
        """Reference,Quantity,Value,Manufacturer,MPN
"D10 D11",2,LTST-C190KGKT,Lite-On,LTST-C190KGKT
RLED,1,330,Fixture,RES-330
""",
    )

    results = validate_component_against_profile(design.components["D10"], led_profile, design)

    check = next(check for check in results.component_checks if check.check == "led_current_limit")
    assert check.status == "PASS"
    assert "shared current-limit resistor RLED" in check.summary


def test_ss34_cathode_floating(diode_profile, tmp_path):
    """ERROR: Cathode pin not connected."""
    netlist_content = """$PACKAGES
  ! 'SMA' ! SS34 ; D1
  ! 'R0805' ! 100R ; R_LOAD
$NETS
  'DIODE_OUT' ; D1.2, R_LOAD.1
  'GND' ; R_LOAD.2
$END
"""
    netlist_path = tmp_path / "test.net"
    netlist_path.write_text(netlist_content)

    bom_content = """Reference,Value,Footprint,Description
D1,SS34,SMA,Schottky diode
R_LOAD,100R,0805,Load resistor
"""
    bom_path = tmp_path / "test_bom.csv"
    bom_path.write_text(bom_content)

    netlist = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(netlist)
    design = apply_bom_to_design(design, match_bom_to_design(bom, design))

    component = design.components["D1"]
    results = validate_component_against_profile(component, diode_profile, design)

    assert results.status == "ERROR"
    cathode_checks = [
        c for c in results.component_checks if c.check == "diode_cathode_connectivity"
    ]
    assert len(cathode_checks) == 1
    assert cathode_checks[0].status == "ERROR"
    assert "not connected" in cathode_checks[0].summary


def test_ss34_anode_floating(diode_profile, tmp_path):
    """ERROR: Anode pin not connected."""
    netlist_content = """$PACKAGES
  ! 'SMA' ! SS34 ; D1
  ! 'R0805' ! 100R ; R_LOAD
$NETS
  '+12V' ; D1.1, R_LOAD.1
  'GND' ; R_LOAD.2
$END
"""
    netlist_path = tmp_path / "test.net"
    netlist_path.write_text(netlist_content)

    bom_content = """Reference,Value,Footprint,Description
D1,SS34,SMA,Schottky diode
R_LOAD,100R,0805,Load resistor
"""
    bom_path = tmp_path / "test_bom.csv"
    bom_path.write_text(bom_content)

    netlist = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(netlist)
    design = apply_bom_to_design(design, match_bom_to_design(bom, design))

    component = design.components["D1"]
    results = validate_component_against_profile(component, diode_profile, design)

    assert results.status == "ERROR"
    anode_checks = [c for c in results.component_checks if c.check == "diode_anode_connectivity"]
    assert len(anode_checks) == 1
    assert anode_checks[0].status == "ERROR"
    assert "not connected" in anode_checks[0].summary


def _design_from_text(tmp_path: Path, netlist_content: str, bom_content: str):
    netlist_path = tmp_path / "test.net"
    netlist_path.write_text(netlist_content)
    bom_path = tmp_path / "test_bom.csv"
    bom_path.write_text(bom_content)

    netlist = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(netlist)
    return apply_bom_to_design(design, match_bom_to_design(bom, design))
