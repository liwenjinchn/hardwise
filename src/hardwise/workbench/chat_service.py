"""Runner-backed workbench chat orchestration and response normalization."""

from __future__ import annotations

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
    _runner_prompt,
    _sanitize_chat_copy,
    _trace_refdes,
)
from hardwise.workbench.context import WorkbenchContext
from hardwise.workbench.chat_client import WorkbenchAIUnavailable
from hardwise.workbench.ai_config import create_provider_client
from hardwise.workbench.ai_disclosure import DisclosureSession, AIConfirmationRequired


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
        injected_destination: str | None = None,
    ) -> None:
        self.context = context
        self.mode = mode
        self.tier = tier
        self.collection = collection
        if mode == "real" and client is None:
            from dotenv import load_dotenv

            # Preserve model-slot configuration before the router snapshots
            # the environment, without requiring a key or constructing an SDK client.
            load_dotenv(override=True)
        self._disclosure_session = DisclosureSession(
            client=client,
            injected_destination=injected_destination,
            factory=lambda config: self._default_client("real", config),
        )
        self.client = (
            client
            if client is not None
            else (
                self._disclosure_session.snapshot().client
                if mode == "real"
                else self._default_client(mode)
            )
        )
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

    def disclosure(self):
        with self._turn_lock:
            return self._disclosure_session.describe(
                self.context, mode=self.mode, tier=self.tier, collection=self.collection is not None
            )

    def ask(self, request: ChatRequest) -> ChatResponse:
        # One context owns one SQLAlchemy Session. Serialize the complete agent
        # turn so concurrent requests cannot share that Session or the stateful
        # deterministic fake client at the same time.
        with self._turn_lock, self.context.agent_lock:
            client, router = self.client, self.router
            if self.mode == "real":
                snapshot = self._disclosure_session.snapshot()
                disclosure = self._disclosure_session.describe(
                    self.context,
                    mode=self.mode,
                    tier=self.tier,
                    collection=self.collection is not None,
                    snapshot=snapshot,
                )
                if not disclosure.available:
                    raise WorkbenchAIUnavailable(disclosure.notice)
                if request.disclosure_id != disclosure.disclosure_id:
                    raise AIConfirmationRequired(stale=bool(request.disclosure_id))
                client, router = snapshot.client, snapshot.config.router()
            selected = self._selected_refdes(request.selected_refdes)
            runner = Runner(
                client=client,
                router=router,
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
            from anthropic import APIError

            try:
                result = runner.run(_runner_prompt(request.question, selected, request.history))
            except APIError as exc:
                # Provider errors may contain request details. Keep them out of
                # the browser and do not synthesize an engineering answer.
                raise WorkbenchAIUnavailable(
                    "AI 服务暂不可用；导入、确定性检查、人工处理和导出仍可使用。"
                ) from exc
            return self._response_from_result(result, selected)

    def fallback_response(self, question: str, selected_refdes: str | None = None) -> ChatResponse:
        selected = self._selected_refdes(selected_refdes)
        answer = "这个离线演示只包含已审计的验证快照。请选择建议问题，或在本地服务模式下连接模型。"
        clean_answer, wrapped = sanitize_text(answer, self.context.registry)
        return ChatResponse(
            answer=clean_answer,
            response_kind="offline_notice",
            mode=self.mode,
            selected_refdes=selected,
            wrapped_count=wrapped,
            suggestions=self._suggestions(selected),
            datasheet_search_enabled=self.datasheet_search_enabled,
        )

    def _response_from_result(self, result: RunResult, selected: str | None) -> ChatResponse:
        from hardwise.agent.claim_turn import render_explanation
        from hardwise.agent.output_boundary import INSUFFICIENT_EVIDENCE

        traces = [self._trace_from_runner_trace(trace) for trace in result.tool_calls]
        wrapped_count = result.text_wrapped + sum(trace.wrapped for trace in result.tool_calls)
        verified_tokens = {token for trace in traces for token in trace.evidence}
        if result.explanation_review is None:
            answer, response_kind = INSUFFICIENT_EVIDENCE, "insufficient_evidence"
        else:
            answer, response_kind = render_explanation(result.explanation_review)
        answer, _ = sanitize_text(answer, self.context.registry)
        return ChatResponse(
            answer=answer,
            response_kind=response_kind,
            explanation_review=result.explanation_review,
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
        evidence = trace.evidence
        status = row.status if row is not None and trace.has_result else None
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
                reviewed_profile_tokens=row.validation.reviewed_profile_tokens
                if row is not None and row.validation is not None
                else [],
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
    def _default_client(mode: ChatMode, config=None) -> Any:
        if mode in {"fake", "snapshot"}:
            return FakeWorkbenchAnthropic()
        if config is None:
            raise WorkbenchAIUnavailable("AI 配置快照缺失；请刷新发送说明。")
        return create_provider_client(config)


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
