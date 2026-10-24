"""Model prose cannot establish an assessment without a tool result."""

import pytest

from tests.agent.test_runner import (
    FakeResponse,
    FakeTextBlock,
    FakeToolUseBlock,
    _build_runner,
)


@pytest.mark.parametrize(
    "claim",
    [
        "整板检查通过，可以直接投板。",
        "U3 的额定输入为 900 V，PASS。",
        "All checks passed. Safe to fabricate.",
    ],
)
def test_zero_tool_claim_is_withheld(claim):
    runner, _ = _build_runner([FakeResponse(content=[FakeTextBlock(claim)])])
    result = runner.run("是否可以投板")
    assert claim not in result.text
    assert result.response_kind == "insufficient_evidence"
    assert "没有获得可用的工具结果" in result.text


@pytest.mark.parametrize(
    "tool,input_args",
    [
        ("imaginary_tool", {}),
        ("get_component", {}),
        ("search_datasheet", {"query": "U3 额定值"}),
        ("run_component_validation", {"refdes": "U3"}),
    ],
)
def test_failed_or_unconfigured_tool_does_not_unlock_model_claim(tool, input_args):
    runner, _ = _build_runner(
        [
            FakeResponse(content=[FakeToolUseBlock("x", tool, input_args)]),
            FakeResponse(content=[FakeTextBlock("整板检查通过，可以直接投板。")]),
        ]
    )
    result = runner.run("检查")
    assert "可以直接投板" not in result.text
    assert result.response_kind == "insufficient_evidence"
    assert not any(trace.has_result for trace in result.tool_calls)


def test_negative_lookup_is_a_real_tool_result_but_not_a_signoff():
    runner, _ = _build_runner(
        [
            FakeResponse(content=[FakeToolUseBlock("x", "get_component", {"refdes": "U999"})]),
            FakeResponse(content=[FakeTextBlock("没有找到U999。")]),
        ]
    )
    result = runner.run("有 U999 吗")
    assert result.response_kind == "model_explanation"
    assert result.tool_calls[0].has_result
    assert result.text == "没有找到⟨?U999⟩。"
