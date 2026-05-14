"""Sanitizer Layer 2 egress invariants — the two sides of the guard.

The refdes guard must wrap unverified refdes-shaped tokens in everything the
*user* sees (final assistant text, ToolCallTrace.input, ToolCallTrace.output_summary).
It must NOT touch what the *model* sees (the tool_result blocks appended to the
conversation `messages` history). The second half is the harder invariant: if
the guard wraps tool-result payloads going back to the model, the model loses
the ability to distinguish "this refdes really exists in the board" from "the
guard says it doesn't" — the tool-fact channel must remain pristine.

These tests pin both sides in one place so the next refactor doesn't drift.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hardwise.adapters.base import BoardRegistry, ComponentRecord
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
            }
        )
        if not self._script:
            raise RuntimeError("FakeMessages script exhausted")
        return self._script.pop(0)


class FakeAnthropic:
    def __init__(self, script: list[FakeResponse]) -> None:
        self.messages = FakeMessages(script)


def _registry() -> BoardRegistry:
    """U3 is verified; U999 is NOT in the registry."""
    return BoardRegistry(
        project_dir=Path("/tmp/mock"),
        components=[
            ComponentRecord(
                refdes="U3",
                value="LM7805",
                footprint="TO-220",
                datasheet="",
                source_file=Path("mock.kicad_sch"),
                source_kind="schematic",
            ),
        ],
    )


def _build_runner(script: list[FakeResponse]) -> tuple[Runner, FakeAnthropic]:
    client = FakeAnthropic(script)
    session = create_store(":memory:")
    registry = _registry()
    populate_from_registry(session, registry)
    runner = Runner(
        client=client,  # type: ignore[arg-type]
        router=ModelRouter(env={"HARDWISE_MODEL_NORMAL": "test-model"}),
        session=session,
        registry=registry,
    )
    return runner, client


def test_final_assistant_text_wraps_unverified_refdes() -> None:
    """RunResult.text — user-visible — must have unverified refdes wrapped."""
    runner, _ = _build_runner(
        [FakeResponse(content=[FakeTextBlock(text="U3 是真的，但 U999 是模型瞎编的")])]
    )
    result = runner.run("U999 是什么?")

    assert "⟨?U999⟩" in result.text
    assert "U3" in result.text  # verified, kept as-is
    assert "⟨?U3⟩" not in result.text
    assert result.text_wrapped == 1


def test_tool_call_trace_input_wraps_unverified_refdes() -> None:
    """ToolCallTrace.input — user-visible — must wrap unverified refdes in args."""
    runner, _ = _build_runner(
        [
            FakeResponse(
                content=[FakeToolUseBlock(id="t1", name="get_component", input={"refdes": "U999"})]
            ),
            FakeResponse(content=[FakeTextBlock(text="未找到")]),
        ]
    )
    result = runner.run("U999 是什么?")

    assert len(result.tool_calls) == 1
    trace = result.tool_calls[0]
    assert trace.input == {"refdes": "⟨?U999⟩"}
    assert trace.wrapped >= 1


def test_tool_call_trace_output_summary_wraps_unverified_refdes() -> None:
    """ToolCallTrace.output_summary — user-visible — must wrap unverified refdes.

    Exercises `_build_trace` directly with a summary string that contains an
    unverified refdes-shaped token (the realistic source is the tool-error path
    where an exception message may carry a refdes).
    """
    runner, _ = _build_runner([])

    trace = runner._build_trace(
        name="get_component",
        args={"refdes": "U3"},
        summary="tool error: ValueError: refdes U999 not in registry",
    )
    assert "⟨?U999⟩" in trace.output_summary
    assert "U3" not in trace.output_summary or "⟨?U3⟩" not in trace.output_summary  # U3 verified
    assert trace.wrapped >= 1


def test_message_history_tool_result_block_is_not_sanitized() -> None:
    """The tool_result block sent back to the model must contain the raw payload.

    This is the tool-fact channel invariant. The model needs to read the exact
    tool output to know that, e.g., `status=not_found` for `U999` came from
    the registry — not from the guard. Wrapping the payload would conflate the
    two sources of "U999 doesn't exist" and break the agent's trust in tool
    results.
    """
    runner, client = _build_runner(
        [
            FakeResponse(
                content=[FakeToolUseBlock(id="t1", name="get_component", input={"refdes": "U999"})]
            ),
            FakeResponse(content=[FakeTextBlock(text="未找到 U999")]),
        ]
    )
    runner.run("U999 是什么?")

    # The second messages.create call includes the tool_result block in history.
    second_messages = client.messages.calls[1]["messages"]
    tool_result_block = second_messages[-1]["content"][0]
    assert tool_result_block["type"] == "tool_result"

    raw_payload = json.loads(tool_result_block["content"])
    assert raw_payload["status"] == "not_found"
    # CRITICAL: the model-facing payload must carry the raw refdes string,
    # NOT the wrapped guard form. If this ever becomes "⟨?U999⟩" the fact
    # channel has been corrupted.
    assert raw_payload["refdes"] == "U999"
    assert "⟨" not in tool_result_block["content"]
    assert "⟩" not in tool_result_block["content"]


def test_verified_refdes_passes_through_untouched_everywhere() -> None:
    """All-verified runs should produce wrapped=0 on text and all traces.

    Uses prose that avoids refdes-shaped tokens entirely — part numbers like
    `LM7805` would false-positive the regex (documented trade-off elsewhere).
    """
    runner, client = _build_runner(
        [
            FakeResponse(
                content=[FakeToolUseBlock(id="t1", name="get_component", input={"refdes": "U3"})]
            ),
            FakeResponse(content=[FakeTextBlock(text="U3 是稳压器，工作正常")]),
        ]
    )
    result = runner.run("U3?")

    assert result.text_wrapped == 0
    assert sum(tc.wrapped for tc in result.tool_calls) == 0
    assert "⟨" not in result.text
    # And the tool-fact channel still raw.
    second_messages = client.messages.calls[1]["messages"]
    raw = json.loads(second_messages[-1]["content"][0]["content"])
    assert raw["component"]["refdes"] == "U3"
