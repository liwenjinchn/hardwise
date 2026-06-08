"""Tests for shared Allegro workbench context construction."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from hardwise.store.relational import query_components
from hardwise.workbench.server import create_workbench_app
from hardwise.workbench.context import (
    board_registry_from_design,
    build_workbench_context,
    load_allegro_design,
)


def test_board_registry_from_design_projects_components_into_runner_registry() -> None:
    design, _source, _input_type, _property_count = load_allegro_design(
        Path("tests/fixtures/allegro/l78_regulator.net")
    )

    registry = board_registry_from_design(design)

    assert registry.has_refdes("U1")
    assert registry.has_refdes("C1")
    assert len(registry.components) == len(design.components)
    assert registry.components[0].source_kind == "allegro_netlist"


def test_build_workbench_context_populates_relational_store_from_registry() -> None:
    context = build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        generated_at="2026-05-30T00:00:00+00:00",
    )

    try:
        rows = query_components(context.session)
        assert len(rows) == context.index.components_in_design
        profile_backed = {row.refdes for row in context.index.validated_rows if row.profile_path}
        assert profile_backed == {
            "D1",
            "D5",
            "Q1",
            "Q2",
            "Q12",
            "U1",
            "U12",
            "U3",
            "U8",
        }
        assert {"C1", "C2", "R1", "R2"} <= {
            row.refdes for row in context.index.validated_rows
        }
        assert set(context.validation_targets) == {
            "D1",
            "D5",
            "Q1",
            "Q2",
            "Q12",
            "U1",
            "U12",
            "U3",
            "U8",
        }
        assert context.risk_hints.source_path is None
        assert context.risk_hints.accepted_count == 0
        assert context.risk_hints.rejected_count == 0
    finally:
        context.session.close()


def test_build_workbench_context_loads_risk_hints_and_rejects_unknown_refdes(
    tmp_path: Path,
) -> None:
    risk_hints = tmp_path / "risk-hints.json"
    risk_hints.write_text(
        """
        {
          "hints": [
            {
              "refdes": "U1",
              "title": "Check regulator margin",
              "body": "U1 may need more input capacitance."
            },
            {
              "refdes": "U999",
              "title": "Unknown anchor",
              "body": "This hint should not be rendered."
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    context = build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        risk_hints_json=risk_hints,
        generated_at="2026-05-30T00:00:00+00:00",
    )

    try:
        assert context.risk_hints.source_path == str(risk_hints)
        assert context.risk_hints.accepted_count == 1
        assert context.risk_hints.rejected_count == 1
        assert context.risk_hints.accepted[0].refdes == "U1"
        assert context.risk_hints.rejected[0].reason == "unknown_refdes"
    finally:
        context.session.close()


def test_workbench_state_exposes_risk_hints_summary(tmp_path: Path) -> None:
    risk_hints = tmp_path / "risk-hints.json"
    risk_hints.write_text(
        """
        [
          {"refdes": "U1", "title": "Review input", "body": "Check U1 input margin."},
          {"refdes": "U999", "title": "Bad anchor", "body": "Rejected."}
        ]
        """,
        encoding="utf-8",
    )
    context = build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        risk_hints_json=risk_hints,
        generated_at="2026-05-30T00:00:00+00:00",
    )

    class DummyChatService:
        datasheet_search_enabled = False

        def fallback_response(self, _message: str, _selected: str | None) -> object:
            raise AssertionError("state endpoint should not render the workbench")

        def ask(self, _request: object) -> object:
            raise AssertionError("state endpoint should not call chat")

    try:
        client = TestClient(create_workbench_app(context, DummyChatService()))  # type: ignore[arg-type]
        response = client.get("/api/workbench/state")

        assert response.status_code == 200
        assert response.json()["risk_hints"] == {
            "external_status": "loaded",
            "count": 2,
            "accepted_external_count": 1,
            "rejected_external_count": 1,
        }
    finally:
        context.session.close()


def test_build_workbench_context_matches_public_mpn_from_value_with_internal_pn(
    tmp_path: Path,
) -> None:
    netlist_path = tmp_path / "internal_pn_public_value.net"
    bom_path = tmp_path / "internal_pn_public_value_bom.csv"
    netlist_path.write_text(
        """$PACKAGES
  ! 'QFN14' ! LOCAL_MPQ8626 ; U13
  ! 'TSSOP8' ! LOCAL_PCA9617 ; U30
  ! 'DO214AB' ! LOCAL_TVS ; D26
  ! 'SMAFL' ! LOCAL_SCHOTTKY ; D27
  ! 'SOD323' ! LOCAL_SMALL_SCHOTTKY ; D36
  ! 'IND' ! 1.5uH ; PL1
  ! 'R0402' ! 10K ; R_EN
$NETS
  'P12V' ; U13.3, D26.K, D27.1
  'GND' ; U13.1, U13.7, U13.14, U30.4, D26.A, D27.2, D36.1
  'SW' ; U13.2, U13.11, PL1.1
  'P1V8' ; U13.6, U30.1, PL1.2
  'CS_LOCAL' ; U13.4
  'EN_P1V8' ; U13.5
  'TRK_REF' ; U13.8
  'PGOOD' ; U13.9
  'BST' ; U13.10
  'MODE' ; U13.12
  'VCC_BIAS' ; U13.13
  'I2C_A_SCL' ; U30.2
  'I2C_A_SDA' ; U30.3
  'EN_LOCAL' ; U30.5, R_EN.2
  'I2C_B_SDA' ; U30.6
  'I2C_B_SCL' ; U30.7
  'P3V3' ; U30.8, R_EN.1, D36.2
$END
""",
        encoding="utf-8",
    )
    bom_path.write_text(
        "Reference,Quantity,Value,Manufacturer,MPN\n"
        "U13,1,IC MPQ8626GD-Z QFN-14 power converter MPS,MPS,1273963\n"
        "U30,1,IC PCA9617ADP TSSOP8 I2C repeater NXP,NXP,1300001\n"
        "D26,1,TVS 1.5SMC15A SMC Littelfuse,Littelfuse,1276307\n"
        "D27,1,Schottky SM340AF SMA-FL LRC,LRC,1260597\n"
        "D36,1,Schottky SD103AWS-7-F SOD323 Diodes,Diodes,1179226\n"
        "PL1,1,1.5uH,Fixture,INTERNAL-INDUCTOR\n"
        "R_EN,1,10K,Fixture,INTERNAL-RESISTOR\n",
        encoding="utf-8",
    )

    context = build_workbench_context(
        netlist_path=netlist_path,
        bom_path=bom_path,
        profiles=Path("data/datasheet_profiles"),
        generated_at="2026-06-03T00:00:00+00:00",
    )

    try:
        candidates = {candidate.refdes: candidate for candidate in context.candidate_report.candidates}
        profile_backed = {
            row.refdes: row.profile_path for row in context.index.validated_rows if row.profile_path
        }
        assert profile_backed == {
            "U13": "data/datasheet_profiles/mpq8626.json",
            "U30": "data/datasheet_profiles/pca9617a.json",
            "D26": "data/datasheet_profiles/1_5smc15a.json",
            "D27": "data/datasheet_profiles/sm340af.json",
            "D36": "data/datasheet_profiles/sd103aws_7_f.json",
        }
        assert candidates["U13"].identity_kind == "value_mpn"
        assert candidates["U30"].identity_kind == "value_mpn"
        rows = {row.refdes: row for row in context.index.rows}
        assert rows["U13"].validation is not None
        assert rows["U13"].validation.status == "PASS"
    finally:
        context.session.close()
