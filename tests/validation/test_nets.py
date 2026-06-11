"""Tests for design-scoped net connectivity checks."""

from pathlib import Path

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.adapters.allegro_pst import parse_allegro_pst
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.build import build_design_from_netlist, build_design_from_pst
from hardwise.ir.types import Design, Net
from hardwise.report.project_validation_markdown import render
from hardwise.validation.nets import (
    CHECK_SINGLE_ENDPOINT,
    validate_design_nets,
)
from hardwise.validation.profile_candidates import suggest_profile_candidates
from hardwise.validation.project_index import build_project_validation_index


def _design_with_nets(nets: dict[str, list[tuple[str, str]]]) -> Design:
    """Build a minimal in-memory Design with the requested net nodes."""

    return Design(
        components={},
        nets={name: Net(name=name, nodes=nodes) for name, nodes in nets.items()},
        project_path=Path("synthetic_board"),
        source_eda="allegro_netlist",
    )


def test_single_endpoint_net_warns_with_evidence_token():
    """A one-node net yields exactly one WARN carrying a netlist token."""

    design = _design_with_nets(
        {
            "VCC_3V3": [("U1", "1"), ("C1", "1")],
            "DANGLE": [("U1", "7")],
        }
    )
    results = validate_design_nets(design)

    assert len(results) == 1
    result = results[0]
    assert result.net_name == "DANGLE"
    assert result.check == CHECK_SINGLE_ENDPOINT
    assert result.status == "WARN"
    assert result.nodes == ["U1.7"]
    assert result.evidence == ["netlist:synthetic_board#net=DANGLE"]
    assert "U1.7" in result.summary
    assert "Reviewer to confirm" in result.summary


def test_multi_endpoint_nets_produce_no_results():
    """Two-or-more-node nets are connectivity-clean for this check."""

    design = _design_with_nets(
        {
            "GND": [("U1", "2"), ("C1", "2"), ("R1", "2")],
            "SIG": [("U1", "3"), ("R1", "1")],
        }
    )
    assert validate_design_nets(design) == []


def test_source_label_overrides_project_path_in_evidence():
    """Callers that know the netlist file name control the token label."""

    design = _design_with_nets({"DANGLE": [("U1", "7")]})
    results = validate_design_nets(design, source_label="board.net")

    assert results[0].evidence == ["netlist:board.net#net=DANGLE"]


def test_results_are_sorted_by_net_name():
    """Output order is deterministic regardless of dict insertion order."""

    design = _design_with_nets(
        {
            "Z_LATE": [("U1", "9")],
            "A_EARLY": [("U1", "8")],
        }
    )
    results = validate_design_nets(design)

    assert [r.net_name for r in results] == ["A_EARLY", "Z_LATE"]


def test_mixed_controller_power_stage_fixture_ground_truth():
    """Public Allegro fixture: exactly ADC_POT and PWM1L are single-endpoint."""

    registry = parse_allegro_netlist(
        Path("tests/fixtures/allegro/mixed_controller_power_stage.net")
    )
    design = build_design_from_netlist(registry)
    results = validate_design_nets(
        design, source_label="mixed_controller_power_stage.net"
    )

    assert [(r.net_name, r.nodes) for r in results] == [
        ("ADC_POT", ["U8.11"]),
        ("PWM1L", ["U3.3"]),
    ]
    assert all(r.status == "WARN" for r in results)
    assert results[0].evidence == [
        "netlist:mixed_controller_power_stage.net#net=ADC_POT"
    ]


def test_pst_fixture_has_no_single_endpoint_nets():
    """PST fixture: every net has two or more endpoints — no findings."""

    registry = parse_allegro_pst(Path("tests/fixtures/allegro/pst"))
    design = build_design_from_pst(registry)

    assert validate_design_nets(design) == []


def _index_from_text(tmp_path: Path, netlist: str, bom_text: str):
    """Build a project validation index from synthetic netlist/BOM text."""

    netlist_path = tmp_path / "fixture.net"
    bom_path = tmp_path / "fixture_bom.csv"
    netlist_path.write_text(netlist, encoding="utf-8")
    bom_path.write_text(bom_text, encoding="utf-8")
    registry = parse_allegro_netlist(netlist_path)
    bom = parse_bom(bom_path)
    design = build_design_from_netlist(registry)
    report = match_bom_to_design(bom, design)
    design = apply_bom_to_design(design, report)
    candidates = suggest_profile_candidates(bom, Path("data/datasheet_profiles"))
    return build_project_validation_index(
        design=design,
        bom=bom,
        bom_report=report,
        candidate_report=candidates,
        project_name="net-checks",
        generated_at="2026-06-11T00:00:00+00:00",
        netlist_source=str(netlist_path),
        netlist_type="fixture",
    )


_DANGLING_NETLIST = """$PACKAGES
  ! 'SOP8' ! FIXTURE_IC ; U1
  ! 'C0805' ! 100nF ; C1
$NETS
  'VCC' ; U1.1, C1.1
  'GND' ; U1.2, C1.2
  'DANGLE' ; U1.7
$END
"""

_DANGLING_BOM = """Reference,Quantity,Value,Manufacturer,MPN
U1,1,FIXTURE_IC,Fixture,FIXTURE_IC
C1,1,100nF,Fixture,GRM21BR71E104KA01
"""


def test_project_index_populates_net_checks(tmp_path):
    """build_project_validation_index runs net checks with a basename token."""

    index = _index_from_text(tmp_path, _DANGLING_NETLIST, _DANGLING_BOM)

    assert [(c.net_name, c.status) for c in index.net_checks] == [("DANGLE", "WARN")]
    assert index.net_checks[0].check == CHECK_SINGLE_ENDPOINT
    # Token uses the netlist basename, never the absolute local path.
    assert index.net_checks[0].evidence == ["netlist:fixture.net#net=DANGLE"]


def test_markdown_report_renders_net_checks_section(tmp_path):
    """The project markdown report carries a Net Checks section."""

    index = _index_from_text(tmp_path, _DANGLING_NETLIST, _DANGLING_BOM)
    report = render(index)

    assert "## Net Checks" in report
    assert "| DANGLE | net_single_endpoint | WARN | U1.7 |" in report
    assert "`netlist:fixture.net#net=DANGLE`" in report
    # The net-check evidence token never carries the absolute local path.
    # (The header Netlist/BOM source fields show what display_path returns
    # for out-of-repo inputs — pre-existing behavior outside this check.)
    assert f"netlist:{tmp_path}" not in report


def test_markdown_report_states_no_net_findings(tmp_path):
    """With no single-endpoint nets the section says so explicitly."""

    clean_netlist = """$PACKAGES
  ! 'SOP8' ! FIXTURE_IC ; U1
  ! 'C0805' ! 100nF ; C1
$NETS
  'VCC' ; U1.1, C1.1
  'GND' ; U1.2, C1.2
$END
"""
    index = _index_from_text(tmp_path, clean_netlist, _DANGLING_BOM)
    report = render(index)

    assert "## Net Checks" in report
    assert "No net-level findings." in report
