"""Workbench chat service backed by Runner and deterministic fake model mode."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

from hardwise.agent.prompts import WORKBENCH_SYSTEM_PROMPT
from hardwise.agent.router import ModelRouter, Tier
from hardwise.agent.runner import RunResult, Runner, ToolCallTrace
from hardwise.guards.refdes import sanitize_text
from hardwise.validation.project_index import ProjectValidationRow
from hardwise.workbench.context import WorkbenchContext


ChatMode = Literal["fake", "real", "snapshot"]


class ChatMessage(BaseModel):
    """One browser-held chat message sent back for short context."""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """User question sent from the Copilot panel."""

    question: str
    selected_refdes: str | None = None
    history: list[ChatMessage] = Field(default_factory=list)


class EvidenceTrace(BaseModel):
    """UI-friendly trace row derived from one Runner tool call."""

    tool: str
    input: dict[str, Any] = Field(default_factory=dict)
    summary: str
    status: str | None = None
    evidence: list[str] = Field(default_factory=list)
    wrapped: int = 0


class ChatResponse(BaseModel):
    """Answer returned to the Copilot panel."""

    answer: str
    mode: ChatMode
    selected_refdes: str | None = None
    trace: list[EvidenceTrace] = Field(default_factory=list)
    wrapped_count: int = 0
    suggestions: list[str] = Field(default_factory=list)
    datasheet_search_enabled: bool = False


@dataclass
class _FakeUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class _FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class _FakeToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]
    type: str = "tool_use"


@dataclass
class _FakeResponse:
    content: list[Any]
    usage: _FakeUsage = field(default_factory=_FakeUsage)


class _FakeWorkbenchMessages:
    """Anthropic-compatible fake messages API that round-trips Runner blocks."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self._turn = 0
        self._last_question = ""
        self._last_selected = ""

    def create(self, **kwargs: Any) -> _FakeResponse:
        self.calls.append(kwargs)
        messages = list(kwargs.get("messages", []))
        last = messages[-1] if messages else {}
        content = last.get("content")
        if isinstance(content, list):
            return _FakeResponse([_FakeTextBlock(self._answer_from_tool_result(content))])

        self._turn += 1
        self._last_question, self._last_selected = _parse_runner_prompt(str(content or ""))
        refdes = _choose_refdes(self._last_question, self._last_selected)
        if _needs_datasheet_search(self._last_question):
            return _FakeResponse(
                [
                    _FakeToolUseBlock(
                        id=f"hw_fake_{self._turn}_datasheet",
                        name="search_datasheet",
                        input={"query": self._last_question, "top_k": 3},
                    ),
                    _FakeToolUseBlock(
                        id=f"hw_fake_{self._turn}_validation",
                        name="run_component_validation",
                        input={"refdes": refdes},
                    ),
                ]
            )
        return _FakeResponse(
            [
                _FakeToolUseBlock(
                    id=f"hw_fake_{self._turn}",
                    name="run_component_validation",
                    input={"refdes": refdes},
                )
            ]
        )

    def _answer_from_tool_result(self, blocks: list[dict[str, Any]]) -> str:
        payloads = _tool_payloads(blocks)
        if not payloads:
            return _localized(
                self._last_question,
                "I could not read the tool result.",
                "我没有读到工具返回结果。",
            )
        search_payload = _search_payload(payloads)
        validation_payload = _validation_payload(payloads)
        if search_payload is not None:
            return self._answer_from_datasheet_result(search_payload, validation_payload)
        if validation_payload is None:
            return _localized(
                self._last_question,
                "The tool returned a result, but this fake workbench mode cannot summarize it yet.",
                "工具已经返回结果，但 fake workbench 模式暂时不能总结这个结果。",
            )
        return self._answer_from_validation_result(validation_payload)

    def _answer_from_datasheet_result(
        self,
        search_payload: dict[str, Any],
        validation_payload: dict[str, Any] | None,
    ) -> str:
        hits = search_payload.get("hits") if isinstance(search_payload.get("hits"), list) else []
        if not search_payload.get("found") and search_payload.get("error"):
            if _wants_english(self._last_question):
                prefix = (
                    "Vector datasheet search is not configured for this workbench run. "
                    "I checked the structured profile/validation evidence instead: "
                )
            else:
                prefix = (
                    "这次 workbench 没有配置向量 datasheet search。"
                    "先回退到结构化 profile/validation 证据: "
                )
            if validation_payload is not None:
                return prefix + self._answer_from_validation_result(validation_payload)
            return prefix + _localized(
                self._last_question,
                "no validation evidence was available for the selected component.",
                "当前选中器件没有可用的 validation 证据。",
            )

        if hits:
            hit = hits[0]
            source = hit.get("source_pdf") or "datasheet"
            page = hit.get("page") or "?"
            text = str(hit.get("text") or "").strip()
            snippet = text[:220]
            if _wants_english(self._last_question):
                return f"Datasheet search found {source} p{page}: {snippet}"
            return f"datasheet search 找到 {source} 第 {page} 页: {snippet}"

        return _localized(
            self._last_question,
            "Datasheet search returned no matching chunks for this question.",
            "datasheet search 没有找到匹配片段。",
        )

    def _answer_from_validation_result(self, payload: dict[str, Any]) -> str:
        status = payload.get("status")
        refdes = str(payload.get("refdes") or self._last_selected or "")
        if status == "validated":
            overall = str(payload.get("overall") or "UNKNOWN")
            counts = payload.get("counts") if isinstance(payload.get("counts"), dict) else {}
            checks = payload.get("checks") if isinstance(payload.get("checks"), list) else []
            important = _important_checks(checks)
            evidence = _evidence_from_checks(checks)
            if _wants_english(self._last_question):
                lines = [
                    f"{refdes} is {overall} in the deterministic family validator.",
                    (
                        "Counts: "
                        f"PASS={counts.get('PASS', 0)}, WARN={counts.get('WARN', 0)}, "
                        f"ERROR={counts.get('ERROR', 0)}."
                    ),
                ]
                if important:
                    lines.append("Key issue: " + important[0])
                if evidence:
                    lines.append("Evidence: " + ", ".join(evidence[:3]) + ".")
                return " ".join(lines)

            lines = [
                f"{refdes} 的确定性 family validator 结果是 {overall}。",
                (
                    "计数: "
                    f"PASS={counts.get('PASS', 0)}, WARN={counts.get('WARN', 0)}, "
                    f"ERROR={counts.get('ERROR', 0)}。"
                ),
            ]
            if important:
                lines.append("关键问题: " + important[0])
            if evidence:
                lines.append("证据: " + "、".join(evidence[:3]) + "。")
            return "".join(lines)

        if status == "not_found":
            matches = payload.get("closest_matches")
            suggestions = ", ".join(matches[:3]) if isinstance(matches, list) else ""
            if _wants_english(self._last_question):
                suffix = f" Closest matches: {suggestions}." if suggestions else ""
                return f"I could not find {refdes} in the EDA registry.{suffix}"
            suffix = f" 最接近的是: {suggestions}。" if suggestions else ""
            return f"我没有在当前 EDA registry 中找到 {refdes}。{suffix}"

        if status == "no_profile":
            if _wants_english(self._last_question):
                return f"{refdes} exists, but it has no assigned validation profile yet."
            return f"{refdes} 在板上，但还没有分配结构化 validation profile。"

        if _wants_english(self._last_question):
            return "The tool returned a result, but this fake workbench mode cannot summarize it yet."
        return "工具已经返回结果，但 fake workbench 模式暂时不能总结这个结果。"


class FakeWorkbenchAnthropic:
    """Tiny Anthropic-compatible fake client for tests and demo smoke."""

    def __init__(self) -> None:
        self.messages = _FakeWorkbenchMessages()


class WorkbenchChatService:
    """Run workbench questions through Runner and normalize the response."""

    def __init__(
        self,
        context: WorkbenchContext,
        *,
        mode: ChatMode,
        tier: Tier = "normal",
        collection: Any | None = None,
        client: Any | None = None,
    ) -> None:
        self.context = context
        self.mode = mode
        self.tier = tier
        self.collection = collection
        self.client = client or self._default_client(mode)
        self.router = (
            ModelRouter(env={"HARDWISE_MODEL_NORMAL": "fake-workbench-model"})
            if mode in {"fake", "snapshot"}
            else ModelRouter()
        )

    @property
    def datasheet_search_enabled(self) -> bool:
        return self.collection is not None

    def ask(self, request: ChatRequest) -> ChatResponse:
        selected = self._selected_refdes(request.selected_refdes)
        runner = Runner(
            client=self.client,
            router=self.router,
            session=self.context.session,
            registry=self.context.registry,
            collection=self.collection,
            tier=self.tier,
            max_iterations=4,
            system_prompt=WORKBENCH_SYSTEM_PROMPT,
            design=self.context.design,
            validation_targets=self.context.validation_targets,
        )
        result = runner.run(_runner_prompt(request.question, selected))
        return self._response_from_result(result, selected)

    def fallback_response(self, question: str, selected_refdes: str | None = None) -> ChatResponse:
        selected = self._selected_refdes(selected_refdes)
        answer = (
            "这个离线演示只包含已审计的 validation 快照。"
            "请选择建议问题，或在 serve-workbench 模式下连接本地模型。"
        )
        clean_answer, wrapped = sanitize_text(answer, self.context.registry)
        return ChatResponse(
            answer=clean_answer,
            mode=self.mode,
            selected_refdes=selected,
            wrapped_count=wrapped,
            suggestions=self._suggestions(selected),
            datasheet_search_enabled=self.datasheet_search_enabled,
        )

    def _response_from_result(self, result: RunResult, selected: str | None) -> ChatResponse:
        traces = [self._trace_from_runner_trace(trace) for trace in result.tool_calls]
        wrapped_count = result.text_wrapped + sum(trace.wrapped for trace in result.tool_calls)
        return ChatResponse(
            answer=result.text,
            mode=self.mode,
            selected_refdes=selected,
            trace=traces,
            wrapped_count=wrapped_count,
            suggestions=self._suggestions(selected),
            datasheet_search_enabled=self.datasheet_search_enabled,
        )

    def _trace_from_runner_trace(self, trace: ToolCallTrace) -> EvidenceTrace:
        refdes = _trace_refdes(trace)
        row = self._row_for_refdes(refdes)
        evidence = _row_evidence(row)
        status = row.status if row is not None else None
        return EvidenceTrace(
            tool=trace.name,
            input=trace.input,
            summary=trace.output_summary,
            status=status,
            evidence=evidence,
            wrapped=trace.wrapped,
        )

    def _row_for_refdes(self, refdes: str | None) -> ProjectValidationRow | None:
        if not refdes:
            return None
        for row in self.context.index.rows:
            if row.refdes == refdes:
                return row
        return None

    def _selected_refdes(self, selected_refdes: str | None) -> str | None:
        if selected_refdes and self.context.registry.has_refdes(selected_refdes):
            return selected_refdes
        return default_refdes(self.context)

    def _suggestions(self, selected_refdes: str | None) -> list[str]:
        refdes = selected_refdes or default_refdes(self.context) or "U1"
        raw = [
            f"这个 {refdes} 为什么是 ERROR/WARN?",
            f"Show evidence for {refdes}",
            f"datasheet 里 {refdes} 的关键限制是什么?",
            "板上有没有 U999?",
        ]
        return [_sanitize_chat_copy(item, self.context) for item in raw]

    @staticmethod
    def _default_client(mode: ChatMode) -> Any:
        if mode in {"fake", "snapshot"}:
            return FakeWorkbenchAnthropic()

        from anthropic import Anthropic
        from dotenv import load_dotenv

        load_dotenv(override=True)
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
        if not api_key or api_key == "replace_me":
            raise ValueError("ANTHROPIC_API_KEY missing or unset in .env")
        return Anthropic(api_key=api_key, base_url=base_url)


def default_refdes(context: WorkbenchContext) -> str | None:
    """Return the first high-signal validated refdes for chat defaults."""

    for wanted in ("ERROR", "WARN", "PASS"):
        for row in context.index.validated_rows:
            if row.validation is not None and row.validation.status == wanted:
                return row.refdes
    if context.index.rows:
        return context.index.rows[0].refdes
    return None


def build_snapshot_responses(context: WorkbenchContext) -> dict[str, ChatResponse]:
    """Precompute audited snapshot answers with the fake model and real Runner."""

    service = WorkbenchChatService(context, mode="snapshot")
    selected = default_refdes(context)
    questions = [
        f"这个 {selected or '器件'} 为什么是 ERROR/WARN?",
        f"Show evidence for {selected or 'this component'}",
        f"datasheet 里 {selected or '这个器件'} 的关键限制是什么?",
        "板上有没有 U999?",
    ]
    responses: dict[str, ChatResponse] = {}
    for question in questions:
        responses[question] = service.ask(ChatRequest(question=question, selected_refdes=selected))
    fallback = service.fallback_response("", selected)
    responses["__fallback__"] = fallback
    return responses


def _runner_prompt(question: str, selected_refdes: str | None) -> str:
    selected = selected_refdes or "(none)"
    return f"Selected refdes: {selected}\nQuestion: {question.strip()}"


def _parse_runner_prompt(content: str) -> tuple[str, str]:
    selected_match = re.search(r"Selected refdes:\s*(.+)", content)
    question_match = re.search(r"Question:\s*(.*)", content, re.DOTALL)
    selected = selected_match.group(1).strip() if selected_match else ""
    question = question_match.group(1).strip() if question_match else content.strip()
    return question, "" if selected == "(none)" else selected


def _choose_refdes(question: str, selected: str) -> str:
    tokens = re.findall(r"\b[A-Z]{1,3}\d{1,4}\b", question.upper())
    for token in tokens:
        if token != selected:
            return token
    if tokens:
        return tokens[0]
    return selected or "U1"


def _tool_payloads(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for block in blocks:
        if block.get("type") != "tool_result":
            continue
        content = block.get("content")
        if not isinstance(content, str):
            continue
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def _search_payload(payloads: list[dict[str, Any]]) -> dict[str, Any] | None:
    for payload in payloads:
        if "hits" in payload and "query" in payload:
            return payload
    return None


def _validation_payload(payloads: list[dict[str, Any]]) -> dict[str, Any] | None:
    validation_statuses = {"validated", "not_found", "no_profile", "not_configured"}
    for payload in payloads:
        status = payload.get("status")
        if isinstance(status, str) and status in validation_statuses:
            return payload
    return None


def _needs_datasheet_search(question: str) -> bool:
    text = question.lower()
    needles = (
        "datasheet",
        "data sheet",
        "absolute maximum",
        "abs max",
        "rating",
        "rated",
        "规格书",
        "数据手册",
        "手册",
        "绝对最大",
        "额定",
    )
    return any(needle in text for needle in needles)


def _important_checks(checks: list[Any]) -> list[str]:
    rendered: list[str] = []
    for status in ("ERROR", "WARN"):
        for check in checks:
            if not isinstance(check, dict) or check.get("status") != status:
                continue
            name = str(check.get("check") or "check")
            summary = str(check.get("summary") or "")
            rendered.append(f"{name}: {summary}")
    return rendered


def _evidence_from_checks(checks: list[Any]) -> list[str]:
    evidence: list[str] = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        raw = check.get("evidence")
        if isinstance(raw, list):
            for item in raw:
                token = str(item)
                if token and token not in evidence:
                    evidence.append(token)
    return evidence


def _row_evidence(row: ProjectValidationRow | None) -> list[str]:
    if row is None or row.validation is None:
        return []
    checks = [
        *[
            {"status": item.status, "evidence": item.evidence}
            for item in row.validation.pin_results
        ],
        *[
            {"status": item.status, "evidence": item.evidence}
            for item in row.validation.component_checks
        ],
    ]
    return _evidence_from_checks(checks)


def _trace_refdes(trace: ToolCallTrace) -> str | None:
    value = trace.input.get("refdes")
    return value if isinstance(value, str) and "?" not in value else None


def _sanitize_chat_copy(text: str, context: WorkbenchContext) -> str:
    clean, _wrapped = sanitize_text(text, context.registry)
    return clean


def _wants_english(text: str) -> bool:
    return not re.search(r"[\u4e00-\u9fff]", text)


def _localized(question: str, english: str, chinese: str) -> str:
    return english if _wants_english(question) else chinese
