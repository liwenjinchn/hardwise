"""Agent main loop — wire ModelRouter + TOOL_DEFINITIONS + Anthropic messages.create.

The loop sequence:

    user_message
      ↓
    messages.create(system=cache_control_blocks, tools=TOOL_DEFINITIONS, ...)
      ↓
    response.content has tool_use blocks? ─yes→ dispatch each tool, append
                                                tool_result blocks, repeat
                                          ─no →  extract final text, return

The agent code never names a specific model — `ModelRouter.select(tier)`
makes that call from `.env`. The `system_blocks` come from
`prompts.build_system_blocks()` with `cache_control=ephemeral` so the
upstream proxy can serve the long static prompt from cache across turns
(mechanism #5 wiring; whether the upstream actually caches depends on
provider support and the prompt-size threshold).

Hardware-engineer explanation: this is the part of the agent that actually
"thinks". The deterministic R001/R002/R003 checks in `checklist/checks/*`
are the rule-based pass; this loop is the question-answering pass that
lets a human ask "U3 是什么器件 / NC pin 怎么处理 / datasheet 第几页说了什么".
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from anthropic import Anthropic
from sqlalchemy.orm import Session

from hardwise.adapters.base import BoardRegistry
from hardwise.agent.prompts import build_system_blocks
from hardwise.agent.router import ModelRouter, Tier
from hardwise.agent.tools import (
    TOOL_DEFINITIONS,
    GetComponentInput,
    GetNcPinsInput,
    ListComponentsInput,
    SearchDatasheetInput,
    get_component,
    get_nc_pins,
    list_components,
    search_datasheet,
)

MAX_ITERATIONS = 10
MAX_TOKENS = 2048


@dataclass
class ToolCallTrace:
    """One executed tool call: name, input args, short summary of output."""

    name: str
    input: dict
    output_summary: str


@dataclass
class RunResult:
    """Outcome of one Runner.run() invocation."""

    text: str
    tool_calls: list[ToolCallTrace] = field(default_factory=list)
    iterations: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    stopped_at_cap: bool = False


class Runner:
    """Wire model + tools + messages.create into a finite tool-use loop.

    Construction is cheap. `run(user_message)` runs the loop and returns
    a `RunResult` carrying final text + tool call trace + token usage.
    Pass `collection=None` to disable `search_datasheet` (it returns a
    structured "not configured" message; the agent learns to back off).
    """

    def __init__(
        self,
        client: Anthropic,
        router: ModelRouter,
        session: Session,
        registry: BoardRegistry,
        collection: Any | None = None,
        tier: Tier = "normal",
        max_iterations: int = MAX_ITERATIONS,
        max_tokens: int = MAX_TOKENS,
    ) -> None:
        self.client = client
        self.router = router
        self.session = session
        self.registry = registry
        self.collection = collection
        self.tier = tier
        self.max_iterations = max_iterations
        self.max_tokens = max_tokens

    def run(self, user_message: str) -> RunResult:
        result = RunResult(text="")
        messages: list[dict] = [{"role": "user", "content": user_message}]
        model = self.router.select(self.tier)
        system_blocks = build_system_blocks()

        for iteration in range(1, self.max_iterations + 1):
            response = self.client.messages.create(
                model=model,
                max_tokens=self.max_tokens,
                system=system_blocks,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )
            self._accumulate_usage(result, response)
            tool_uses = [b for b in response.content if getattr(b, "type", None) == "tool_use"]

            if not tool_uses:
                result.text = self._extract_text(response.content)
                result.iterations = iteration
                return result

            messages.append({"role": "assistant", "content": response.content})
            tool_results: list[dict] = []
            for tool_use in tool_uses:
                tool_result_block, trace = self._dispatch(tool_use)
                tool_results.append(tool_result_block)
                result.tool_calls.append(trace)
            messages.append({"role": "user", "content": tool_results})

        result.text = "(stopped: iteration cap reached)"
        result.iterations = self.max_iterations
        result.stopped_at_cap = True
        return result

    def _dispatch(self, tool_use: Any) -> tuple[dict, ToolCallTrace]:
        """Run one tool call; return (tool_result block, trace entry)."""
        name = tool_use.name
        args = dict(tool_use.input) if tool_use.input else {}
        try:
            if name == "list_components":
                out = list_components(self.session, ListComponentsInput(**args))
                summary = f"total={out.total}"
                payload = out.model_dump_json()
            elif name == "get_component":
                out = get_component(self.session, self.registry, GetComponentInput(**args))
                summary = f"status={out.status}"
                payload = out.model_dump_json()
            elif name == "get_nc_pins":
                out = get_nc_pins(self.session, GetNcPinsInput(**args))
                summary = f"total={out.total}"
                payload = out.model_dump_json()
            elif name == "search_datasheet":
                if self.collection is None:
                    summary = "skipped: vector store not configured"
                    payload = json.dumps(
                        {
                            "found": False,
                            "hits": [],
                            "query": args.get("query", ""),
                            "error": "vector store not configured for this run",
                        }
                    )
                else:
                    out = search_datasheet(self.collection, SearchDatasheetInput(**args))
                    summary = f"hits={len(out.hits)}"
                    payload = out.model_dump_json()
            else:
                summary = f"unknown tool: {name}"
                return (
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps({"error": summary}),
                        "is_error": True,
                    },
                    ToolCallTrace(name=name, input=args, output_summary=summary),
                )
        except Exception as e:  # noqa: BLE001 — surface any tool error to the model
            summary = f"tool error: {type(e).__name__}: {e}"
            return (
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": json.dumps({"error": summary}),
                    "is_error": True,
                },
                ToolCallTrace(name=name, input=args, output_summary=summary),
            )

        return (
            {
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": payload,
            },
            ToolCallTrace(name=name, input=args, output_summary=summary),
        )

    @staticmethod
    def _extract_text(content: list[Any]) -> str:
        parts: list[str] = []
        for block in content:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                parts.append(text)
        return "".join(parts).strip()

    @staticmethod
    def _accumulate_usage(result: RunResult, response: Any) -> None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        result.input_tokens += int(getattr(usage, "input_tokens", 0) or 0)
        result.output_tokens += int(getattr(usage, "output_tokens", 0) or 0)
        result.cache_creation_tokens += int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
        result.cache_read_tokens += int(getattr(usage, "cache_read_input_tokens", 0) or 0)
