"""Tests for the scoped reviewed-profile evidence locator."""

from __future__ import annotations

import json
from pathlib import Path

from hardwise.agent.evidence_locator import (
    LocateComponentEvidenceInput,
    locate_component_evidence,
)
from hardwise.agent.router import ModelRouter
from hardwise.agent.runner import Runner
from hardwise.workbench.context import build_workbench_context
from tests.agent.test_runner import FakeAnthropic, FakeResponse, FakeTextBlock, FakeToolUseBlock


def _write_docs(path: Path) -> Path:
    path.write_text(
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
    return path


def _context(document_index: Path | None = None):
    return build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        document_index=document_index,
        generated_at="2026-05-30T00:00:00+00:00",
    )


def test_locate_component_evidence_finds_boot_profile_pin_token() -> None:
    context = _context()
    try:
        result = locate_component_evidence(
            context.design,
            context.validation_targets,
            context.index,
            context.document_report,
            LocateComponentEvidenceInput(refdes="U8", topic="boot", limit=8),
        )

        assert result.status == "found"
        assert result.found is True
        assert result.profile_part_number == "STM32G030C8T6"
        boot = next(
            hit
            for hit in result.hits
            if hit.pin_number == "44" and hit.source_kind == "profile_pin"
        )
        assert boot.source_kind == "profile_pin"
        assert boot.pin_name == "BOOT0"
        assert boot.evidence == ["datasheet:stm32g030.pdf#p33"]
    finally:
        context.session.close()


def test_locate_component_evidence_finds_enable_pin_without_vector_search() -> None:
    context = _context()
    try:
        result = locate_component_evidence(
            context.design,
            context.validation_targets,
            context.index,
            context.document_report,
            LocateComponentEvidenceInput(refdes="U12", topic="enable", limit=8),
        )

        assert result.status == "found"
        assert any(hit.pin_number == "4" and hit.pin_name == "ON/OFF" for hit in result.hits)
        assert {token for hit in result.hits for token in hit.evidence} >= {
            "datasheet:xl1509.pdf#p2",
            "datasheet:xl1509.pdf#p5",
        }
    finally:
        context.session.close()


def test_locate_component_evidence_unknown_refdes_returns_closest_matches() -> None:
    context = _context()
    try:
        result = locate_component_evidence(
            context.design,
            context.validation_targets,
            context.index,
            context.document_report,
            LocateComponentEvidenceInput(refdes="U999", topic="boot"),
        )

        assert result.status == "not_found"
        assert result.found is False
        assert result.closest_matches
        assert all(match in context.design.refdes_set for match in result.closest_matches)
    finally:
        context.session.close()


def test_locator_no_profile_keeps_document_coverage_non_spec(tmp_path: Path) -> None:
    context = _context(_write_docs(tmp_path / "docs.csv"))
    try:
        result = locate_component_evidence(
            context.design,
            context.validation_targets,
            context.index,
            context.document_report,
            LocateComponentEvidenceInput(refdes="J2", topic="pin_function"),
        )

        assert result.status == "no_profile"
        assert result.found is False
        assert result.document_status == "matched"
        assert result.hits[0].source_kind == "document_coverage"
        assert result.hits[0].evidence == ["doc:docs.csv#line2"]
        assert "not proof" in result.hits[0].note
    finally:
        context.session.close()


def test_runner_dispatches_evidence_locator_and_preserves_l1_trace() -> None:
    context = _context()
    client = FakeAnthropic(
        [
            FakeResponse(
                content=[
                    FakeToolUseBlock(
                        id="t1",
                        name="locate_component_evidence",
                        input={"refdes": "U8", "topic": "boot", "limit": 3},
                    )
                ]
            ),
            FakeResponse(content=[FakeTextBlock(text="BOOT0 evidence found")]),
        ]
    )
    try:
        runner = Runner(
            client=client,  # type: ignore[arg-type]
            router=ModelRouter(env={"HARDWISE_MODEL_NORMAL": "test-model"}),
            session=context.session,
            registry=context.registry,
            design=context.design,
            validation_targets=context.validation_targets,
            project_index=context.index,
            document_report=context.document_report,
        )

        result = runner.run("U8 BOOT0 evidence?")

        assert result.tool_calls[0].name == "locate_component_evidence"
        assert result.tool_calls[0].output_summary == "status=found, hits=3"
        assert result.tool_calls[0].trust_tier == "l1"
        assert "datasheet:stm32g030.pdf#p33" in result.tool_calls[0].evidence
        payload = json.loads(client.messages.calls[1]["messages"][-1]["content"][0]["content"])
        assert payload["status"] == "found"
        assert payload["hits"][0]["source_kind"] in {
            "profile_fact",
            "profile_pin",
            "validation_check",
        }
    finally:
        context.session.close()
