"""Fast tests for system prompt cache-control wiring."""

from __future__ import annotations

from hardwise.agent.prompts import SYSTEM_PROMPT, build_system_blocks


def test_build_system_blocks_wraps_prompt_with_ephemeral_cache_control() -> None:
    blocks = build_system_blocks()

    assert blocks == [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]


def test_build_system_blocks_preserves_custom_prompt_text() -> None:
    blocks = build_system_blocks("custom review prompt")

    assert blocks == [
        {
            "type": "text",
            "text": "custom review prompt",
            "cache_control": {"type": "ephemeral"},
        }
    ]
