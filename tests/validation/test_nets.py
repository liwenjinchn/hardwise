"""Tests for design-scoped net connectivity checks."""

from pathlib import Path

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.adapters.allegro_pst import parse_allegro_pst
from hardwise.ir.build import build_design_from_netlist, build_design_from_pst
from hardwise.ir.types import Design, Net
from hardwise.validation.nets import (
    CHECK_SINGLE_ENDPOINT,
    validate_design_nets,
)


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
