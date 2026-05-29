"""Tests for the run_component_validation bridge tool (agent <-> validators).

Two layers:
  - the pure tool function against a real IR Design + profile (no API)
  - the runner dispatch path, proving the agent loop reaches the family
    validator and gets structured PASS/WARN/ERROR back (FakeAnthropic, no API)

The bridge is the Phase 1 fix from DR-011: before it, agent/ and validation/
were parallel pipelines that never connected.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.agent.tools import (
    RunComponentValidationInput,
    run_component_validation,
)
from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.build import build_design_from_netlist
from hardwise.ir.profile import DatasheetProfile


def _mosfet_design():
    netlist = parse_allegro_netlist(Path("tests/fixtures/allegro/irf540n_mosfet.net"))
    bom = parse_bom(Path("tests/fixtures/allegro/irf540n_mosfet_bom.csv"))
    design = build_design_from_netlist(netlist)
    return apply_bom_to_design(design, match_bom_to_design(bom, design))


def _mosfet_profile() -> DatasheetProfile:
    return DatasheetProfile.load(Path("data/datasheet_profiles/irf540n.json"))


# ─────────────────────────── pure tool function ────────────────────────────


def test_validated_returns_structured_pass() -> None:
    design = _mosfet_design()
    targets = {"Q1": _mosfet_profile()}
    out = run_component_validation(design, targets, RunComponentValidationInput(refdes="Q1"))

    assert out.status == "validated"
    assert out.refdes == "Q1"
    assert out.profile_part_number == "IRF540N"
    assert out.overall == "PASS"
    assert out.counts["ERROR"] == 0
    # the corrected Vgs check rides through the bridge with its evidence token
    vgs = next(c for c in out.checks if c.check == "mosfet_vgs_rating")
    assert vgs.status == "PASS"
    assert "gate 10 V - source 0 V" in vgs.summary
    assert vgs.evidence == ["datasheet:irf540n.pdf#p1"]


def test_no_profile_for_unassigned_refdes() -> None:
    design = _mosfet_design()
    out = run_component_validation(design, {}, RunComponentValidationInput(refdes="Q1"))

    assert out.status == "no_profile"
    assert out.refdes == "Q1"


def test_not_found_returns_closest_matches() -> None:
    design = _mosfet_design()
    targets = {"Q1": _mosfet_profile()}
    # "Q11" scores ~0.8 against "Q1" — above difflib's 0.6 cutoff (same cutoff
    # get_component uses), so the suggestion path fires.
    out = run_component_validation(design, targets, RunComponentValidationInput(refdes="Q11"))

    assert out.status == "not_found"
    assert out.refdes == "Q11"
    assert "Q1" in out.closest_matches


def test_no_refdes_fabrication_on_empty_design() -> None:
    """An unknown refdes must never come back as validated."""
    design = _mosfet_design()
    out = run_component_validation(design, {}, RunComponentValidationInput(refdes="ZZ99"))
    assert out.status == "not_found"
    assert out.closest_matches == []


# ─────────────────────────── runner dispatch path ──────────────────────────


def _build_validation_runner(script: list[Any]):
    """Reuse the FakeAnthropic harness from test_runner, add design + targets."""
    from hardwise.adapters.base import BoardRegistry
    from hardwise.agent.router import ModelRouter
    from hardwise.agent.runner import Runner
    from hardwise.store.relational import create_store
    from tests.agent.test_runner import FakeAnthropic

    client = FakeAnthropic(script)
    session = create_store(":memory:")
    registry = BoardRegistry(project_dir=Path("/tmp/mock"), components=[], nc_pins=[])
    design = _mosfet_design()
    runner = Runner(
        client=client,  # type: ignore[arg-type]
        router=ModelRouter(env={"HARDWISE_MODEL_NORMAL": "test-model"}),
        session=session,
        registry=registry,
        design=design,
        validation_targets={"Q1": _mosfet_profile()},
    )
    return runner, client


def test_runner_dispatches_validation_and_returns_structured_payload() -> None:
    """The agent loop calls run_component_validation and gets PASS/WARN/ERROR back."""
    from tests.agent.test_runner import FakeResponse, FakeTextBlock, FakeToolUseBlock

    runner, client = _build_validation_runner(
        [
            FakeResponse(
                content=[
                    FakeToolUseBlock(
                        id="t1", name="run_component_validation", input={"refdes": "Q1"}
                    )
                ]
            ),
            FakeResponse(content=[FakeTextBlock(text="Q1 验证通过")]),
        ]
    )
    result = runner.run("Q1 接线对吗?")

    assert result.tool_calls[0].name == "run_component_validation"
    assert result.tool_calls[0].output_summary == "status=validated"
    tool_result_msg = client.messages.calls[1]["messages"][-1]
    payload = json.loads(tool_result_msg["content"][0]["content"])
    assert payload["status"] == "validated"
    assert payload["overall"] == "PASS"
    assert payload["profile_part_number"] == "IRF540N"


def test_runner_validation_without_design_returns_not_configured() -> None:
    """No design loaded -> structured not_configured, never a fabricated verdict."""
    from hardwise.adapters.base import BoardRegistry
    from hardwise.agent.router import ModelRouter
    from hardwise.agent.runner import Runner
    from hardwise.store.relational import create_store
    from tests.agent.test_runner import (
        FakeAnthropic,
        FakeResponse,
        FakeTextBlock,
        FakeToolUseBlock,
    )

    client = FakeAnthropic(
        [
            FakeResponse(
                content=[
                    FakeToolUseBlock(
                        id="t1", name="run_component_validation", input={"refdes": "Q1"}
                    )
                ]
            ),
            FakeResponse(content=[FakeTextBlock(text="无法验证")]),
        ]
    )
    runner = Runner(
        client=client,  # type: ignore[arg-type]
        router=ModelRouter(env={"HARDWISE_MODEL_NORMAL": "test-model"}),
        session=create_store(":memory:"),
        registry=BoardRegistry(project_dir=Path("/tmp/mock"), components=[], nc_pins=[]),
    )
    result = runner.run("Q1 接线对吗?")
    assert "skipped" in result.tool_calls[0].output_summary
    tool_result_msg = client.messages.calls[1]["messages"][-1]
    payload = json.loads(tool_result_msg["content"][0]["content"])
    assert payload["status"] == "not_configured"
