"""Tests for the agent tool-use loop.

Uses a FakeAnthropicClient that returns scripted responses — keeps the loop
hermetic, no API key needed, fast subset eligible. Covers:

  - text-only response → runner returns text, no tool calls
  - single tool_use → dispatch + tool_result + final text
  - multiple tool_use blocks in one turn → all dispatched
  - search_datasheet with no collection → structured "not configured"
  - unknown tool name → is_error tool_result, run continues
  - iteration cap → runner stops, sets stopped_at_cap
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hardwise.adapters.base import BoardRegistry, ComponentRecord, NcPinRecord
from hardwise.agent.router import ModelRouter
from hardwise.agent.runner import Runner
from hardwise.store.relational import create_store, populate_from_registry


@dataclass
class FakeUsage:
    input_tokens: int = 100
    output_tokens: int = 50
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeToolUseBlock:
    id: str
    name: str
    input: dict
    type: str = "tool_use"


@dataclass
class FakeResponse:
    content: list[Any]
    usage: FakeUsage = field(default_factory=FakeUsage)


class FakeMessages:
    def __init__(self, script: list[FakeResponse]) -> None:
        self._script = script
        self.calls: list[dict] = []

    def create(self, **kwargs: Any) -> FakeResponse:
        self.calls.append(
            {
                "model": kwargs.get("model"),
                "messages": list(kwargs.get("messages", [])),
                "system": kwargs.get("system"),
                "tools": kwargs.get("tools"),
            }
        )
        if not self._script:
            raise RuntimeError("FakeMessages script exhausted")
        return self._script.pop(0)


class FakeAnthropic:
    def __init__(self, script: list[FakeResponse]) -> None:
        self.messages = FakeMessages(script)


def _mock_registry() -> BoardRegistry:
    return BoardRegistry(
        project_dir=Path("/tmp/mock"),
        components=[
            ComponentRecord(
                refdes="U3",
                value="LM7805",
                footprint="TO-220",
                datasheet="https://example.com/lm7805.pdf",
                source_file=Path("mock.kicad_sch"),
                source_kind="schematic",
            ),
            ComponentRecord(
                refdes="C1",
                value="100nF",
                footprint="",
                datasheet="",
                source_file=Path("mock.kicad_sch"),
                source_kind="schematic",
            ),
        ],
        nc_pins=[
            NcPinRecord(
                refdes="U3",
                pin_number="2",
                pin_name="GND",
                pin_electrical_type="passive",
                source_file=Path("mock.kicad_sch"),
            ),
        ],
    )


def _build_runner(
    script: list[FakeResponse], collection: Any | None = None
) -> tuple[Runner, FakeAnthropic]:
    client = FakeAnthropic(script)
    session = create_store(":memory:")
    registry = _mock_registry()
    populate_from_registry(session, registry)
    runner = Runner(
        client=client,  # type: ignore[arg-type]
        router=ModelRouter(env={"HARDWISE_MODEL_NORMAL": "test-model"}),
        session=session,
        registry=registry,
        collection=collection,
    )
    return runner, client


def test_runner_text_only_returns_text() -> None:
    runner, client = _build_runner(
        [FakeResponse(content=[FakeTextBlock(text="U3 是 LM7805 稳压器")])]
    )
    result = runner.run("U3 是什么?")
    assert result.text == "U3 是 LM7805 稳压器"
    assert result.tool_calls == []
    assert result.iterations == 1
    assert result.input_tokens == 100
    assert result.output_tokens == 50
    assert result.stopped_at_cap is False
    assert len(client.messages.calls) == 1


def test_runner_single_tool_use_dispatches_then_text() -> None:
    runner, client = _build_runner(
        [
            FakeResponse(
                content=[FakeToolUseBlock(id="t1", name="get_component", input={"refdes": "U3"})]
            ),
            FakeResponse(content=[FakeTextBlock(text="U3 是 LM7805，封装 TO-220")]),
        ]
    )
    result = runner.run("U3 是什么?")
    assert result.text == "U3 是 LM7805，封装 TO-220"
    assert result.iterations == 2
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "get_component"
    assert result.tool_calls[0].input == {"refdes": "U3"}
    assert "found" in result.tool_calls[0].output_summary
    assert len(client.messages.calls) == 2
    second_call_messages = client.messages.calls[1]["messages"]
    tool_result_msg = second_call_messages[-1]
    assert tool_result_msg["role"] == "user"
    assert tool_result_msg["content"][0]["type"] == "tool_result"
    payload = json.loads(tool_result_msg["content"][0]["content"])
    assert payload["status"] == "found"
    assert payload["component"]["refdes"] == "U3"


def test_runner_multiple_tool_uses_in_one_turn() -> None:
    runner, _ = _build_runner(
        [
            FakeResponse(
                content=[
                    FakeToolUseBlock(id="t1", name="get_component", input={"refdes": "U3"}),
                    FakeToolUseBlock(id="t2", name="get_component", input={"refdes": "C1"}),
                ]
            ),
            FakeResponse(content=[FakeTextBlock(text="U3 是 LM7805，C1 是 100nF")]),
        ]
    )
    result = runner.run("U3 和 C1 是什么?")
    assert result.iterations == 2
    assert len(result.tool_calls) == 2
    assert {t.input["refdes"] for t in result.tool_calls} == {"U3", "C1"}


def test_runner_unknown_refdes_returns_closest_matches_to_model() -> None:
    runner, client = _build_runner(
        [
            FakeResponse(
                content=[FakeToolUseBlock(id="t1", name="get_component", input={"refdes": "U33"})]
            ),
            FakeResponse(content=[FakeTextBlock(text="未找到 U33，最接近的是 U3")]),
        ]
    )
    result = runner.run("U33 是什么?")
    assert result.tool_calls[0].output_summary == "status=not_found"
    tool_result_msg = client.messages.calls[1]["messages"][-1]
    payload = json.loads(tool_result_msg["content"][0]["content"])
    assert payload["status"] == "not_found"
    assert payload["refdes"] == "U33"
    assert "U3" in payload["closest_matches"]


def test_runner_search_datasheet_without_collection_returns_not_configured() -> None:
    runner, client = _build_runner(
        [
            FakeResponse(
                content=[
                    FakeToolUseBlock(
                        id="t1",
                        name="search_datasheet",
                        input={"query": "absolute maximum input voltage"},
                    )
                ]
            ),
            FakeResponse(content=[FakeTextBlock(text="向量库未配置，无法回答")]),
        ],
        collection=None,
    )
    result = runner.run("找一下 U3 的最大输入电压?")
    assert "skipped" in result.tool_calls[0].output_summary
    payload = json.loads(client.messages.calls[1]["messages"][-1]["content"][0]["content"])
    assert payload["found"] is False
    assert "not configured" in payload["error"]


def test_runner_unknown_tool_returns_is_error() -> None:
    runner, client = _build_runner(
        [
            FakeResponse(
                content=[FakeToolUseBlock(id="t1", name="bogus_tool", input={"foo": "bar"})]
            ),
            FakeResponse(content=[FakeTextBlock(text="工具不存在")]),
        ]
    )
    result = runner.run("call bogus")
    assert result.tool_calls[0].name == "bogus_tool"
    assert "unknown tool" in result.tool_calls[0].output_summary
    second_call_messages = client.messages.calls[1]["messages"]
    tool_result_msg = second_call_messages[-1]
    block = tool_result_msg["content"][0]
    assert block["type"] == "tool_result"
    assert block.get("is_error") is True


def test_runner_iteration_cap_stops_loop() -> None:
    script = [
        FakeResponse(
            content=[FakeToolUseBlock(id=f"t{i}", name="get_component", input={"refdes": "U3"})]
        )
        for i in range(3)
    ]
    runner, client = _build_runner(script)
    runner.max_iterations = 3
    result = runner.run("loop forever")
    assert result.stopped_at_cap is True
    assert result.iterations == 3
    assert "cap reached" in result.text
    assert len(client.messages.calls) == 3


def test_runner_token_accounting_sums_across_iterations() -> None:
    runner, _ = _build_runner(
        [
            FakeResponse(
                content=[FakeToolUseBlock(id="t1", name="get_component", input={"refdes": "U3"})],
                usage=FakeUsage(input_tokens=200, output_tokens=80),
            ),
            FakeResponse(
                content=[FakeTextBlock(text="done")],
                usage=FakeUsage(input_tokens=300, output_tokens=20),
            ),
        ]
    )
    result = runner.run("U3?")
    assert result.input_tokens == 500
    assert result.output_tokens == 100
