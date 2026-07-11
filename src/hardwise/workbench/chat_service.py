"""Runner-backed workbench chat orchestration and response normalization."""

from __future__ import annotations

import os
from threading import RLock
from typing import Any

from hardwise.agent.prompts import WORKBENCH_SYSTEM_PROMPT
from hardwise.agent.router import ModelRouter, Tier
from hardwise.agent.runner import RunResult, Runner, ToolCallTrace
from hardwise.guards.evidence import unsupported_evidence_tokens
from hardwise.guards.evidence_class import classify_evidence_tokens
from hardwise.guards.refdes import sanitize_text
from hardwise.trust import trust_label_text
from hardwise.validation.project_index import ProjectValidationRow
from hardwise.workbench.chat_contracts import (
    ChatMode,
    ChatRequest,
    ChatResponse,
    EvidenceTrace,
)
from hardwise.workbench.chat_fake_model import (
    C5_L2_SNAPSHOT_QUESTION,
    FakeWorkbenchAnthropic,
    _AuditedL78SnapshotCollection,
    _row_evidence,
    _runner_prompt,
    _sanitize_chat_copy,
    _trace_refdes,
)
from hardwise.workbench.context import WorkbenchContext


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
        # Shallow request snapshots intentionally share this lock with the
        # underlying client, including across an imported context swap.
        self._turn_lock = RLock()
        self.router = (
            ModelRouter(env={"HARDWISE_MODEL_NORMAL": "fake-workbench-model"})
            if mode in {"fake", "snapshot"}
            else ModelRouter()
        )

    @property
    def datasheet_search_enabled(self) -> bool:
        return self.collection is not None

    def ask(self, request: ChatRequest) -> ChatResponse:
        # One context owns one SQLAlchemy Session. Serialize the complete agent
        # turn so concurrent requests cannot share that Session or the stateful
        # deterministic fake client at the same time.
        with self._turn_lock, self.context.agent_lock:
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
                project_index=self.context.index,
                document_report=self.context.document_report,
            )
            result = runner.run(_runner_prompt(request.question, selected, request.history))
            return self._response_from_result(result, selected)

    def fallback_response(self, question: str, selected_refdes: str | None = None) -> ChatResponse:
        selected = self._selected_refdes(selected_refdes)
        answer = "这个离线演示只包含已审计的验证快照。请选择建议问题，或在本地服务模式下连接模型。"
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
        verified_tokens = {token for trace in traces for token in trace.evidence}
        return ChatResponse(
            answer=result.text,
            mode=self.mode,
            selected_refdes=selected,
            trace=traces,
            wrapped_count=wrapped_count,
            suggestions=self._suggestions(selected),
            datasheet_search_enabled=self.datasheet_search_enabled,
            unsupported_evidence_tokens=unsupported_evidence_tokens(result.text, verified_tokens),
        )

    def _trace_from_runner_trace(self, trace: ToolCallTrace) -> EvidenceTrace:
        refdes = _trace_refdes(trace)
        row = self._row_for_refdes(refdes)
        evidence = trace.evidence or _row_evidence(row)
        status = row.status if row is not None else None
        trust_tier = trace.trust_tier
        live_tokens = evidence if trace.name == "search_datasheet" else []
        return EvidenceTrace(
            tool=trace.name,
            input=trace.input,
            summary=trace.output_summary,
            status=status,
            evidence=evidence,
            evidence_classification=classify_evidence_tokens(
                evidence,
                live_retrieved_tokens=live_tokens,
            ),
            wrapped=trace.wrapped,
            trust_tier=trust_tier,
            trust_label=trust_label_text(trust_tier) if trust_tier else None,
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
            f"查看 {refdes} 的证据链",
            f"数据手册里 {refdes} 的关键限制是什么?",
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
    l2_service = WorkbenchChatService(
        context,
        mode="snapshot",
        collection=_AuditedL78SnapshotCollection(),
    )
    selected = default_refdes(context)
    questions = [
        f"这个 {selected or '器件'} 为什么是 ERROR/WARN?",
        f"查看 {selected or '这个器件'} 的证据链",
        f"数据手册里 {selected or '这个器件'} 的关键限制是什么?",
        "板上有没有 U999?",
    ]
    responses: dict[str, ChatResponse] = {}
    for question in questions:
        responses[question] = service.ask(ChatRequest(question=question, selected_refdes=selected))
    responses[C5_L2_SNAPSHOT_QUESTION] = l2_service.ask(
        ChatRequest(question=C5_L2_SNAPSHOT_QUESTION, selected_refdes=selected)
    )
    fallback = service.fallback_response("", selected)
    fallback.suggestions.append(C5_L2_SNAPSHOT_QUESTION)
    responses["__fallback__"] = fallback
    return responses
