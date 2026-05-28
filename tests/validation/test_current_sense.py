"""Tests for INA180 current-sense amplifier validation."""

from __future__ import annotations

from pathlib import Path

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.build import build_design_from_netlist
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Net, Pin
from hardwise.validation import validate_component_against_profile


def _ina180_profile() -> DatasheetProfile:
    return DatasheetProfile.load(Path("data/datasheet_profiles/ina180.json"))


def _ina180_design() -> Design:
    design = build_design_from_netlist(
        parse_allegro_netlist(Path("tests/fixtures/allegro/ina180_current_sense.net"))
    )
    bom = parse_bom(Path("tests/fixtures/allegro/ina180_current_sense_bom.csv"))
    return apply_bom_to_design(design, match_bom_to_design(bom, design))


def test_ina180_nominal_all_pass():
    """Nominal fixture: all component checks should PASS."""
    profile = _ina180_profile()
    design = _ina180_design()
    component = design.components["U20"]
    report = validate_component_against_profile(component, profile, design)

    assert report.refdes == "U20"
    assert report.profile_part_number == "INA180"

    checks = {c.check: c for c in report.component_checks}
    assert checks["csa_input_pair"].status == "PASS"
    assert checks["csa_output_load"].status == "PASS"
    assert checks["csa_ref_connection"].status == "PASS"

    assert report.status == "PASS"


def _ina180_design_inline(
    *,
    in_plus_net: str = "ISENSE_HI",
    in_minus_net: str = "ISENSE_LO",
    out_net: str = "ADC_IN",
    ref_net: str = "GND",
    out_neighbors: list[str] | None = None,
) -> Design:
    """Build an inline Design for INA180 error-case testing."""
    if out_neighbors is None:
        out_neighbors = ["R2"]

    pins = [
        Pin(number="1", name="OUT", electrical_type="", is_nc=False, net=out_net),
        Pin(number="2", name="GND", electrical_type="", is_nc=False, net="GND"),
        Pin(number="3", name="VCC", electrical_type="", is_nc=False, net="+5V"),
        Pin(number="4", name="REF", electrical_type="", is_nc=False, net=ref_net),
        Pin(number="5", name="IN-", electrical_type="", is_nc=False, net=in_minus_net),
        Pin(number="6", name="IN+", electrical_type="", is_nc=False, net=in_plus_net),
    ]
    u20 = Component(refdes="U20", value="INA180", part_number="INA180", pins=pins)

    nets: dict[str, Net] = {}
    for pin in pins:
        if pin.net and pin.net not in nets:
            nets[pin.net] = Net(name=pin.net, nodes=[])
        if pin.net:
            nets[pin.net].nodes.append(("U20", pin.number))

    if out_neighbors:
        for nb in out_neighbors:
            nets.setdefault(out_net, Net(name=out_net, nodes=[]))
            nets[out_net].nodes.append((nb, "1"))

    components = {"U20": u20}
    for nb in (out_neighbors or []):
        components[nb] = Component(refdes=nb, value="10K", part_number="", pins=[])

    return Design(
        components=components,
        nets=nets,
        project_path=Path("tests/fixtures/allegro"),
        source_eda="allegro_netlist",
    )


def test_ina180_input_pair_shorted():
    """ERROR: IN+ and IN- shorted on same net."""
    profile = _ina180_profile()
    design = _ina180_design_inline(in_plus_net="ISENSE", in_minus_net="ISENSE")
    component = design.components["U20"]
    report = validate_component_against_profile(component, profile, design)

    checks = {c.check: c for c in report.component_checks}
    assert checks["csa_input_pair"].status == "ERROR"
    assert "shorted" in checks["csa_input_pair"].summary.lower()


def test_ina180_output_floating():
    """ERROR: OUT pin has no downstream components."""
    profile = _ina180_profile()
    design = _ina180_design_inline(out_neighbors=[])
    component = design.components["U20"]
    report = validate_component_against_profile(component, profile, design)

    checks = {c.check: c for c in report.component_checks}
    assert checks["csa_output_load"].status == "ERROR"
    assert "no downstream" in checks["csa_output_load"].summary.lower()


def test_ina180_ref_floating_warns():
    """WARN: REF pin has no connection."""
    profile = _ina180_profile()
    design = _ina180_design_inline(ref_net="")
    component = design.components["U20"]
    report = validate_component_against_profile(component, profile, design)

    checks = {c.check: c for c in report.component_checks}
    assert checks["csa_ref_connection"].status == "WARN"
