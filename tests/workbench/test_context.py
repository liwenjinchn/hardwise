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


class DummyChatService:
    datasheet_search_enabled = False

    def fallback_response(self, _message: str, _selected: str | None) -> object:
        raise AssertionError("state/detail endpoints should not render chat")

    def ask(self, _request: object) -> object:
        raise AssertionError("state/detail endpoints should not call chat")


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
        assert {"C1", "C2", "R1", "R2"} <= {row.refdes for row in context.index.validated_rows}
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


def test_workbench_state_exposes_spa_queue_and_risk_hint_details(tmp_path: Path) -> None:
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

    try:
        client = TestClient(create_workbench_app(context, DummyChatService()))  # type: ignore[arg-type]
        payload = client.get("/api/workbench/state").json()

        assert payload["summary"] == {
            "components": 25,
            "bom_matched": 25,
            "validated": 22,
            "manual": 3,
            "pass_count": 5,
            "warn_count": 13,
            "error_count": 4,
        }
        assert payload["selected_refdes"] == "Q12"
        queue_by_refdes = {item["refdes"]: item for item in payload["queue"]}
        assert set(queue_by_refdes) >= {"U12", "U8", "Q12"}
        assert len(queue_by_refdes) == len(payload["queue"])
        q12 = queue_by_refdes["Q12"]
        assert q12["task_count"] >= 4
        assert q12["task_counts"]["error"] >= 4
        assert q12["task_ids"][0] == "F-001"
        assert q12["top_task_id"] == "F-001"
        assert q12["deterministic_status"] == "ERROR"
        assert q12["document_status"] == "not_configured"
        assert payload["risk_hints"] == {
            "external_status": "loaded",
            "count": 2,
            "accepted_external_count": 1,
            "rejected_external_count": 1,
        }
        assert payload["risk_hint_details"]["accepted"][0]["refdes"] == "U1"
        assert payload["risk_hint_details"]["rejected"] == [
            {"reason": "unknown_refdes", "count": 1}
        ]
    finally:
        context.session.close()


def test_workbench_state_exposes_finding_first_review_tasks() -> None:
    context = build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        generated_at="2026-05-30T00:00:00+00:00",
    )

    try:
        client = TestClient(create_workbench_app(context, DummyChatService()))  # type: ignore[arg-type]
        payload = client.get("/api/workbench/state").json()

        tasks = payload["review_tasks"]
        assert tasks[0]["id"] == "F-001"
        assert {task["refdes"] for task in tasks} >= {"U12", "U8", "Q12"}
        assert payload["task_counts"]["total"] == len(tasks)
        assert payload["task_counts"]["error"] >= 3
        first_task = tasks[0]
        assert first_task["kind"] == "component_check"
        assert first_task["stable_key"].startswith("component_check|Q12|")
        assert first_task["check"] == "bjt_emitter_connectivity"
        assert first_task["subject"] == "bjt_emitter_connectivity"
        assert first_task["evidence_chain"]
        assert {item["kind"] for item in first_task["evidence_chain"]} & {
            "netlist_trace",
            "design_rule",
            "datasheet_or_profile",
        }
    finally:
        context.session.close()


def test_workbench_component_detail_exposes_evidence_classification() -> None:
    context = build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        generated_at="2026-05-30T00:00:00+00:00",
    )

    try:
        client = TestClient(create_workbench_app(context, DummyChatService()))  # type: ignore[arg-type]
        detail = client.get("/api/workbench/components/U8").json()

        assert detail["refdes"] == "U8"
        assert detail["status"] == "ERROR"
        assert detail["trust_tier"] == "l1"
        assert detail["task_counts"]["total"] >= 2
        assert {task["kind"] for task in detail["tasks"]} >= {"component_check"}
        assert detail["bom"]["source"].endswith("#line5")
        assert detail["profile"]["path"] == "data/datasheet_profiles/stm32g030c8t6.json"
        assert detail["document"]["status"] == "not_configured"
        evidence = [token for item in detail["evidence_chain"] for token in item["evidence"]]
        assert any(item["source_class"] == "reviewed_profile" for item in evidence)
        assert any(item["token"] == "datasheet:stm32g030.pdf#p33" for item in evidence)

        miss = client.get("/api/workbench/components/U999")
        assert miss.status_code == 404
        assert miss.json()["reason"] == "unknown_refdes"
        assert miss.json()["closest_matches"]
    finally:
        context.session.close()


def test_workbench_component_evidence_endpoint_is_scoped_to_profile_facts() -> None:
    context = build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        generated_at="2026-05-30T00:00:00+00:00",
    )

    try:
        client = TestClient(create_workbench_app(context, DummyChatService()))  # type: ignore[arg-type]
        response = client.get("/api/workbench/components/U8/evidence?topic=boot")
        miss = client.get("/api/workbench/components/U999/evidence?topic=boot")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "found"
        assert payload["profile_part_number"] == "STM32G030C8T6"
        assert any(hit["pin_name"] == "BOOT0" for hit in payload["hits"])
        assert "datasheet:stm32g030.pdf#p33" in {
            token for hit in payload["hits"] for token in hit["evidence"]
        }
        assert miss.status_code == 404
        assert miss.json()["status"] == "not_found"
        assert miss.json()["closest_matches"]
    finally:
        context.session.close()


def test_workbench_component_prep_packet_json_and_markdown_are_safe(tmp_path: Path) -> None:
    risk_hints = tmp_path / "risk-hints.json"
    risk_hints.write_text(
        """
        [
          {"refdes": "U8", "title": "Review SWD header", "body": "Check debug wiring."},
          {"refdes": "U999", "title": "Rejected secret", "body": "Rejected body must not leak."}
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

    try:
        client = TestClient(create_workbench_app(context, DummyChatService()))  # type: ignore[arg-type]
        json_response = client.get("/api/workbench/components/U8/prep-packet?format=json")
        markdown_response = client.get("/api/workbench/components/U8/prep-packet?format=markdown")
        miss = client.get("/api/workbench/components/U999/prep-packet")

        assert json_response.status_code == 200
        packet = json_response.json()
        assert packet["schema_version"] == "hardwise.prep_packet.v1"
        assert packet["component"]["refdes"] == "U8"
        assert packet["component"]["tasks"][0]["stable_key"]
        assert {task["kind"] for task in packet["tasks"]} >= {"component_check"}
        assert packet["risk_hints"]["accepted"][0]["title"] == "Review SWD header"
        assert packet["risk_hints"]["rejected"] == [{"reason": "unknown_refdes", "count": 1}]
        assert "Rejected secret" not in json_response.text
        assert "Rejected body must not leak" not in json_response.text
        assert "ANTHROPIC_API_KEY" not in json_response.text
        assert "sk-" not in json_response.text

        assert markdown_response.status_code == 200
        assert "Hardwise 评审准备包 · U8" in markdown_response.text
        assert packet["tasks"][0]["stable_key"] in markdown_response.text
        assert "Rejected secret" not in markdown_response.text
        assert "Rejected body must not leak" not in markdown_response.text
        assert "ANTHROPIC_API_KEY" not in markdown_response.text
        assert "sk-" not in markdown_response.text

        assert miss.status_code == 404
        assert miss.json()["reason"] == "unknown_refdes"
    finally:
        context.session.close()


def test_workbench_project_prep_packet_json_and_markdown_are_safe(tmp_path: Path) -> None:
    risk_hints = tmp_path / "risk-hints.json"
    risk_hints.write_text(
        """
        [
          {"refdes": "U8", "title": "Review SWD header", "body": "Check debug wiring."},
          {"refdes": "U999", "title": "Rejected secret", "body": "Rejected body must not leak."}
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

    try:
        client = TestClient(create_workbench_app(context, DummyChatService()))  # type: ignore[arg-type]
        json_response = client.get("/api/workbench/prep-packet?format=json")
        markdown_response = client.get("/api/workbench/prep-packet?format=markdown")

        assert json_response.status_code == 200
        packet = json_response.json()
        assert packet["schema_version"] == "hardwise.project_prep_packet.v1"
        assert packet["summary"] == {
            "components": 25,
            "bom_matched": 25,
            "validated": 22,
            "manual": 3,
            "pass_count": 5,
            "warn_count": 13,
            "error_count": 4,
        }
        assert packet["queue"][0]["refdes"] == "Q12"
        assert packet["priority_tasks"][0]["id"] == "F-001"
        assert packet["priority_tasks"][0]["refdes"] == "Q12"
        assert packet["key_component_groups"]
        assert {area["area"] for area in packet["focus_areas"]} >= {"power"}
        assert packet["draft_summaries"]["scope"] == "schematic_netlist_review_prep_only"
        assert {item["nets"][0] for item in packet["draft_summaries"]["power"]} >= {
            "GND",
            "+3V3",
            "+12V",
        }
        assert packet["draft_summaries"]["modules"]
        assert "不是确认的供电层级" in packet["draft_summaries"]["power"][0]["uncertainty"]
        assert {item["status"] for item in packet["profile_promotion_candidates"]} == {
            "needs_public_document"
        }
        assert {item["title"] for item in packet["profile_promotion_candidates"]} >= {
            "RES-10K",
            "SWD-HEADER",
        }
        assert packet["open_questions"]
        assert packet["risk_hints"]["accepted"][0]["title"] == "Review SWD header"
        assert packet["risk_hints"]["rejected"] == [{"reason": "unknown_refdes", "count": 1}]
        assert "Rejected secret" not in json_response.text
        assert "Rejected body must not leak" not in json_response.text
        assert "ANTHROPIC_API_KEY" not in json_response.text
        assert "sk-" not in json_response.text

        assert markdown_response.status_code == 200
        assert "Hardwise 项目评审准备包" in markdown_response.text
        assert "PASS / WARN / ERROR" in markdown_response.text
        assert "Draft Module / Power Summaries" in markdown_response.text
        assert "Manual Gap Promotion Queue" in markdown_response.text
        assert packet["priority_tasks"][0]["stable_key"] in markdown_response.text
        assert "Rejected secret" not in markdown_response.text
        assert "Rejected body must not leak" not in markdown_response.text
        assert "ANTHROPIC_API_KEY" not in markdown_response.text
        assert "sk-" not in markdown_response.text
    finally:
        context.session.close()


def test_workbench_profile_promotion_packet_is_needs_review_only(tmp_path: Path) -> None:
    docs = tmp_path / "docs.csv"
    docs.write_text(
        "\n".join(
            [
                "MPN,Manufacturer,Title,URL,Description",
                (
                    "SWD-HEADER,Fixture,SWD header public drawing,"
                    "https://example.test/swd-header.pdf,fixture"
                ),
            ]
        ),
        encoding="utf-8",
    )
    context = build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        document_index=docs,
        generated_at="2026-05-30T00:00:00+00:00",
    )

    try:
        client = TestClient(create_workbench_app(context, DummyChatService()))  # type: ignore[arg-type]
        json_response = client.get("/api/workbench/profile-gaps/15/promotion-packet?format=json")
        markdown_response = client.get(
            "/api/workbench/profile-gaps/15/promotion-packet?format=markdown"
        )
        miss = client.get("/api/workbench/profile-gaps/999/promotion-packet")

        assert json_response.status_code == 200
        packet = json_response.json()
        candidate = packet["candidate"]
        assert packet["schema_version"] == "hardwise.profile_promotion_packet.v1"
        assert candidate["title"] == "SWD-HEADER"
        assert candidate["status"] == "ready_for_draft"
        assert candidate["draft_review_status"] == "needs_review"
        assert "draft-datasheet-profile" in candidate["draft_command"]
        assert "ready" not in candidate["draft_command"]
        assert any("不改变 PASS/WARN/ERROR" in item for item in packet["guardrails"])

        assert markdown_response.status_code == 200
        assert "needs_review" in markdown_response.text
        assert "ready" in markdown_response.text
        assert "review_status` 必须先保持 `needs_review`" in markdown_response.text

        assert miss.status_code == 404
        assert miss.json()["reason"] == "unknown_component_group"
    finally:
        context.session.close()


def test_workbench_import_rebuilds_context_from_uploaded_files() -> None:
    context = build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/l78_regulator.net"),
        bom_path=Path("tests/fixtures/allegro/l78_regulator_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        generated_at="2026-05-30T00:00:00+00:00",
    )
    app = create_workbench_app(context, DummyChatService())  # type: ignore[arg-type]
    client = TestClient(app)

    try:
        with (
            Path("tests/fixtures/allegro/mixed_controller_power_stage.net").open("rb") as netlist,
            Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv").open("rb") as bom,
        ):
            response = client.post(
                "/api/workbench/import",
                files={
                    "netlist": ("mixed_controller_power_stage.net", netlist, "text/plain"),
                    "bom": ("mixed_controller_power_stage_bom.csv", bom, "text/csv"),
                },
            )

        assert response.status_code == 200, response.text
        assert response.json()["summary"] == {
            "components": 25,
            "bom_matched": 25,
            "validated": 22,
            "manual": 3,
            "pass_count": 5,
            "warn_count": 13,
            "error_count": 4,
        }
        assert client.get("/api/workbench/state").json()["summary"]["components"] == 25
    finally:
        app.state.workbench_context["value"].session.close()


def test_workbench_import_failure_keeps_previous_state(tmp_path: Path) -> None:
    context = build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        generated_at="2026-05-30T00:00:00+00:00",
    )
    app = create_workbench_app(context, DummyChatService())  # type: ignore[arg-type]
    client = TestClient(app)
    bad_hints = tmp_path / "bad-risk-hints.json"
    bad_hints.write_text('{"hints": [', encoding="utf-8")

    try:
        before = client.get("/api/workbench/state").json()["summary"]
        with (
            Path("tests/fixtures/allegro/l78_regulator.net").open("rb") as netlist,
            bad_hints.open("rb") as risk_hints,
        ):
            response = client.post(
                "/api/workbench/import",
                files={
                    "netlist": ("l78_regulator.net", netlist, "text/plain"),
                    "risk_hints_json": ("bad-risk-hints.json", risk_hints, "application/json"),
                },
            )

        assert response.status_code == 400
        assert "import failed" in response.json()["detail"]
        assert client.get("/api/workbench/state").json()["summary"] == before
    finally:
        app.state.workbench_context["value"].session.close()


def test_workbench_export_endpoints_return_safe_downloads() -> None:
    context = build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        generated_at="2026-05-30T00:00:00+00:00",
    )
    app = create_workbench_app(context, DummyChatService())  # type: ignore[arg-type]
    client = TestClient(app)

    try:
        json_response = client.get("/api/workbench/export?format=json")
        csv_response = client.get("/api/workbench/export?format=csv")
        annotations_response = client.get("/api/workbench/export?format=annotations")

        assert json_response.status_code == 200
        assert json_response.json()["review_tasks"][0]["id"] == "F-001"
        assert "F-001" in csv_response.text
        assert "recommended_action" in csv_response.text
        assert "Hardwise EDA annotation export" in annotations_response.text
        combined = json_response.text + csv_response.text + annotations_response.text
        assert "ANTHROPIC_API_KEY" not in combined
        assert "sk-" not in combined
    finally:
        app.state.workbench_context["value"].session.close()


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
        candidates = {
            candidate.refdes: candidate for candidate in context.candidate_report.candidates
        }
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
