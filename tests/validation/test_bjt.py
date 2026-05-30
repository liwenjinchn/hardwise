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
