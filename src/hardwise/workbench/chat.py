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
from hardwise.guards.evidence_class import EvidenceClassification, classify_evidence_tokens
from hardwise.guards.refdes import sanitize_text
from hardwise.report.ui_terms import check_label, validation_summary_label
from hardwise.trust import TrustTier, trust_label_text
from hardwise.validation.project_index import ProjectValidationRow
from hardwise.workbench.context import WorkbenchContext


ChatMode = Literal["fake", "real", "snapshot"]
C5_L2_SNAPSHOT_QUESTION = "查看 L7805 输入耐压的数据手册证据链"


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
    evidence_classification: list[EvidenceClassification] = Field(default_factory=list)
    wrapped: int = 0
    trust_tier: TrustTier | None = None
    trust_label: str | None = None


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
        topology_tools = _topology_tool_uses(self._last_question, refdes, self._turn)
        if topology_tools:
            return _FakeResponse(topology_tools)
        if _needs_document_coverage(self._last_question):
            if _needs_document_summary(self._last_question):
                return _FakeResponse(
                    [
                        _FakeToolUseBlock(
                            id=f"hw_fake_{self._turn}_document_summary",
                            name="summarize_document_coverage",
                            input={"limit": 10, "candidate_limit": 3},
                        )
                    ]
                )
            return _FakeResponse(
                [
                    _FakeToolUseBlock(
                        id=f"hw_fake_{self._turn}_component_documents",
                        name="get_component_documents",
                        input={"refdes": refdes, "candidate_limit": 5},
                    )
                ]
            )
        if _needs_datasheet_search(self._last_question):
            tool_uses: list[Any] = [
                _FakeToolUseBlock(
                    id=f"hw_fake_{self._turn}_datasheet",
                    name="search_datasheet",
                    input={"query": self._last_question, "top_k": 3},
                )
            ]
            if not _is_evidence_chain_smoke(self._last_question):
                tool_uses.append(
                    _FakeToolUseBlock(
                        id=f"hw_fake_{self._turn}_validation",
                        name="run_component_validation",
                        input={"refdes": refdes},
                    )
                )
            return _FakeResponse(tool_uses)
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
        topology_payload = _topology_payload(payloads)
        search_payload = _search_payload(payloads)
        document_payload = _document_payload(payloads)
        validation_payload = _validation_payload(payloads)
        if topology_payload is not None:
            return self._answer_from_topology_result(topology_payload)
        if search_payload is not None:
            return self._answer_from_datasheet_result(search_payload, validation_payload)
        if document_payload is not None:
            return self._answer_from_document_result(document_payload)
        if validation_payload is None:
            return _localized(
                self._last_question,
                "The tool returned a result, but this fake workbench mode cannot summarize it yet.",
                "工具已经返回结果，但演示模式暂时不能总结这个结果。",
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
                    "这次原理图检验工具没有配置向量数据手册搜索。"
                    "先回退到结构化器件档案/验证证据："
                )
            if validation_payload is not None:
                return prefix + self._answer_from_validation_result(validation_payload)
            return prefix + _localized(
                self._last_question,
                "no validation evidence was available for the selected component.",
                "当前选中器件没有可用的验证证据。",
            )

        if hits:
            hit = hits[0]
            source = hit.get("source_pdf") or "datasheet"
            page = hit.get("page") or "?"
            text = str(hit.get("text") or "").strip()
            snippet = text[:220]
            if _wants_english(self._last_question):
                return f"Datasheet search found {source} p{page}: {snippet}"
            if "Absolute maximum ratings table: input voltage VI is 35 V" in text:
                return (
                    f"数据手册搜索命中 {source} 第 {page} 页："
                    "绝对最大额定值表显示，VI 输入耐压为 35 V。"
                )
            return f"数据手册搜索找到 {source} 第 {page} 页：{snippet}"

        return _localized(
            self._last_question,
            "Datasheet search returned no matching chunks for this question.",
            "数据手册搜索没有找到匹配片段。",
        )

    def _answer_from_validation_result(self, payload: dict[str, Any]) -> str:
        status = payload.get("status")
        refdes = str(payload.get("refdes") or self._last_selected or "")
        if status == "validated":
            overall = str(payload.get("overall") or "UNKNOWN")
            counts = payload.get("counts") if isinstance(payload.get("counts"), dict) else {}
            checks = payload.get("checks") if isinstance(payload.get("checks"), list) else []
            wants_english = _wants_english(self._last_question)
            important = _important_checks(checks, localized=not wants_english)
            evidence = _evidence_from_checks(checks)
            if wants_english:
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
                f"{refdes} 的确定性器件族检查结果是 {overall}。",
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
            return f"我没有在当前解析到的 EDA 器件清单中找到 {refdes}。{suffix}"

        if status == "no_profile":
            if _wants_english(self._last_question):
                return f"{refdes} exists, but it has no assigned validation profile yet."
            return f"{refdes} 在板上，但还没有分配结构化器件档案。"

        if _wants_english(self._last_question):
            return "The tool returned a result, but this fake workbench mode cannot summarize it yet."
        return "工具已经返回结果，但演示模式暂时不能总结这个结果。"

    def _answer_from_topology_result(self, payload: dict[str, Any]) -> str:
        status = str(payload.get("status") or "")
        if status == "not_configured":
            return _localized(
                self._last_question,
                "No Allegro/PST schematic topology is loaded for this run.",
                "这次运行没有加载 Allegro/PST 原理图拓扑，所以不能回答连接关系。",
            )
        if status == "summarized":
            return _summarize_topology_payload(self._last_question, payload)
        if "component" in payload:
            return _summarize_component_context_payload(self._last_question, payload)
        if "net_name" in payload:
            return _summarize_net_context_payload(self._last_question, payload)
        if "hits" in payload and "query" in payload:
            return _summarize_net_search_payload(self._last_question, payload)
        return _localized(
            self._last_question,
            "The topology tool returned a result, but this fake workbench mode cannot summarize it yet.",
            "拓扑工具已经返回结果，但演示模式暂时不能总结这个结果。",
        )

    def _answer_from_document_result(self, payload: dict[str, Any]) -> str:
        status = str(payload.get("status") or "")
        if status == "not_configured":
            return _localized(
                self._last_question,
                "No public document index is configured for this workbench run.",
                "这次工作台没有配置公开资料索引，所以不能给出资料覆盖状态。",
            )

        if status == "configured":
            counts = payload.get("counts_by_status") if isinstance(payload.get("counts_by_status"), dict) else {}
            groups = payload.get("groups") if isinstance(payload.get("groups"), list) else []
            missing = [
                group
                for group in groups
                if isinstance(group, dict)
                and group.get("document_status") in {"no_result", "ambiguous", "manual_needed"}
            ]
            first = missing[0] if missing else (groups[0] if groups and isinstance(groups[0], dict) else {})
            identity = str(first.get("identity") or "-")
            doc_status = str(first.get("document_status") or "-")
            if _wants_english(self._last_question):
                return (
                    "Document coverage is from the configured public index only. "
                    f"Counts: matched={counts.get('matched', 0)}, no_result={counts.get('no_result', 0)}, "
                    f"ambiguous={counts.get('ambiguous', 0)}, manual_needed={counts.get('manual_needed', 0)}. "
                    f"First gap/sample: {identity} ({doc_status})."
                )
            return (
                "资料覆盖来自已配置的公开资料索引，不代表电气规格结论。"
                f"计数: matched={counts.get('matched', 0)}，no_result={counts.get('no_result', 0)}，"
                f"ambiguous={counts.get('ambiguous', 0)}，manual_needed={counts.get('manual_needed', 0)}。"
                f"首个缺口/样例: {identity}（{doc_status}）。"
            )

        refdes = str(payload.get("refdes") or self._last_selected or "")
        identity = str(payload.get("identity") or "-")
        selected = payload.get("selected") if isinstance(payload.get("selected"), dict) else None
        candidates = payload.get("candidates") if isinstance(payload.get("candidates"), list) else []
        if status == "matched" and selected:
            title = str(selected.get("title") or "document")
            source = str(selected.get("source") or "")
            if _wants_english(self._last_question):
                return (
                    f"{refdes} maps to {identity}; the local public document index has "
                    f"a matched document: {title} ({source}). This is coverage evidence, "
                    "not an electrical spec claim."
                )
            return (
                f"{refdes} 对应 BOM 身份 {identity}；本地公开资料索引已匹配资料："
                f"{title}（{source}）。这只是资料覆盖证据，不是电气规格结论。"
            )
        if status == "ambiguous":
            count = len(candidates)
            if _wants_english(self._last_question):
                return f"{refdes} maps to {identity}, but the document index has {count} candidates; reviewer selection is needed."
            return f"{refdes} 对应 BOM 身份 {identity}，但公开资料索引有 {count} 个候选，需要人工选定。"
        if status in {"no_result", "manual_needed"}:
            reason = str(payload.get("reason") or "")
            if _wants_english(self._last_question):
                return f"{refdes} maps to {identity}, but document coverage is {status}. Reason: {reason}"
            return f"{refdes} 对应 BOM 身份 {identity}，资料覆盖状态是 {status}。原因: {reason}"
        if status == "not_found":
            matches = payload.get("closest_matches")
            suggestions = ", ".join(matches[:3]) if isinstance(matches, list) else ""
            if _wants_english(self._last_question):
                return f"I could not find {refdes} in document coverage groups. Closest matches: {suggestions}."
            return f"我没有在资料覆盖分组里找到 {refdes}。最接近的是: {suggestions}。"

        return _localized(
            self._last_question,
            "The document tool returned a result, but this fake workbench mode cannot summarize it yet.",
            "资料工具已经返回结果，但演示模式暂时不能总结这个结果。",
        )


class FakeWorkbenchAnthropic:
    """Tiny Anthropic-compatible fake client for tests and demo smoke."""

    def __init__(self) -> None:
        self.messages = _FakeWorkbenchMessages()


class _AuditedL78SnapshotCollection:
    """Hermetic search collection for the static L78 evidence-chain smoke."""

    def count(self) -> int:
        return 1

    def query(self, query_texts: list[str], n_results: int) -> dict[str, list[list[Any]]]:
        del query_texts, n_results
        return {
            "documents": [
                [
                    (
                        "Absolute maximum ratings table: input voltage VI is 35 V "
                        "for VO = 5 to 18 V."
                    )
                ]
            ],
            "metadatas": [
                [
                    {
                        "part_ref": "L7805",
                        "source_pdf": "l78.pdf",
                        "page": 4,
                        "chunk_index": 0,
                    }
                ]
            ],
            "distances": [[0.0]],
        }


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
            project_index=self.context.index,
            document_report=self.context.document_report,
        )
        result = runner.run(_runner_prompt(request.question, selected))
        return self._response_from_result(result, selected)

    def fallback_response(self, question: str, selected_refdes: str | None = None) -> ChatResponse:
        selected = self._selected_refdes(selected_refdes)
        answer = (
            "这个离线演示只包含已审计的验证快照。"
            "请选择建议问题，或在本地服务模式下连接模型。"
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


def _document_payload(payloads: list[dict[str, Any]]) -> dict[str, Any] | None:
    document_statuses = {
        "matched",
        "no_result",
        "ambiguous",
        "manual_needed",
        "not_found",
        "not_configured",
        "configured",
    }
    for payload in payloads:
        status = payload.get("status")
        if isinstance(status, str) and status in document_statuses:
            if "document_index_file" in payload or "identity" in payload or "groups" in payload:
                return payload
            reason = str(payload.get("reason") or "")
            if status == "not_configured" and "document index" in reason.lower():
                return payload
    return None


def _topology_payload(payloads: list[dict[str, Any]]) -> dict[str, Any] | None:
    topology_statuses = {"found", "not_found", "not_configured", "summarized"}
    for payload in payloads:
        status = payload.get("status")
        if isinstance(status, str) and status in topology_statuses:
            if "component" in payload or "net_name" in payload or "component_count" in payload:
                return payload
            reason = str(payload.get("reason") or "")
            if status == "not_configured" and "topology" in reason.lower():
                return payload
    for payload in payloads:
        if "hits" in payload and "query" in payload:
            if "closest_matches" in payload or "sample_members" in json.dumps(payload):
                return payload
    return None


def _topology_tool_uses(question: str, refdes: str, turn: int) -> list[Any]:
    if _needs_project_topology(question):
        return [
            _FakeToolUseBlock(
                id=f"hw_fake_{turn}_topology_summary",
                name="summarize_project_topology",
                input={"component_limit": 10, "net_limit": 10, "gap_limit": 8},
            )
        ]
    if _needs_component_topology(question):
        return [
            _FakeToolUseBlock(
                id=f"hw_fake_{turn}_component_context",
                name="get_component_context",
                input={"refdes": refdes, "neighbor_limit": 24},
            )
        ]
    if _needs_net_topology_search(question):
        return [
            _FakeToolUseBlock(
                id=f"hw_fake_{turn}_net_search",
                name="search_nets",
                input={"query": _net_search_query(question), "limit": 12, "member_sample_limit": 6},
            )
        ]
    return []


def _needs_project_topology(question: str) -> bool:
    text = question.lower()
    needles = (
        "project topology",
        "board topology",
        "topology summary",
        "schematic overview",
        "project overview",
        "这张板",
        "整板",
        "项目概览",
        "原理图概览",
        "拓扑概览",
        "待补 profile",
        "profile 缺口",
    )
    return any(needle in text for needle in needles)


def _needs_component_topology(question: str) -> bool:
    text = question.lower()
    if not re.search(r"\b[A-Z]{1,3}\d{1,4}\b", question.upper()):
        return False
    needles = (
        "connected",
        "connects",
        "connection",
        "topology",
        "netlist",
        "接了哪些",
        "连接",
        "相连",
        "接到",
        "网络",
        "拓扑",
    )
    return any(needle in text for needle in needles)


def _needs_net_topology_search(question: str) -> bool:
    text = question.lower()
    if re.search(r"\b[A-Z]{1,3}\d{1,4}\b", question.upper()):
        return False
    topology_words = ("net", "network", "网络", "相关", "有哪些", "搜索", "查找")
    net_tokens = ("reset", "nrst", "rst", "boot", "vin", "3v3", "sda", "scl", "swd", "swclk", "swdio", "pwm")
    return any(word in text for word in topology_words) and any(token in text for token in net_tokens)


def _net_search_query(question: str) -> str:
    known = ("RESET", "NRST", "RST", "BOOT", "VIN", "3V3", "SDA", "SCL", "SWD", "SWCLK", "SWDIO", "PWM")
    upper = question.upper()
    found = [token for token in known if token in upper]
    return " ".join(found) if found else question


def _summarize_component_context_payload(question: str, payload: dict[str, Any]) -> str:
    status = str(payload.get("status") or "")
    component = payload.get("component") if isinstance(payload.get("component"), dict) else {}
    refdes = str(component.get("refdes") or payload.get("refdes") or "")
    if status == "not_found":
        matches = payload.get("closest_matches")
        suggestions = ", ".join(matches[:3]) if isinstance(matches, list) else ""
        return _localized(
            question,
            f"I could not find {refdes}. Closest matches: {suggestions}.",
            f"我没有在当前设计里找到 {refdes}。最接近的是: {suggestions}。",
        )

    value = str(component.get("value") or component.get("part_number") or "")
    validation = str(payload.get("validation_status") or "-")
    pins = payload.get("pins") if isinstance(payload.get("pins"), list) else []
    pin_text = _format_pin_nets(pins[:8], english=_wants_english(question))
    neighbors = payload.get("neighbors") if isinstance(payload.get("neighbors"), list) else []
    neighbor_text = _format_neighbor_nets(neighbors[:4], english=_wants_english(question))
    if _wants_english(question):
        return (
            f"{refdes} ({value}) is from parsed Allegro/PST topology; validation status is {validation}. "
            f"Pin nets: {pin_text}. Neighbor nets: {neighbor_text}."
        )
    return (
        f"{refdes}（{value}）来自已解析的 Allegro/PST 原理图拓扑，验证状态是 {validation}。"
        f"引脚网络: {pin_text}。相邻网络: {neighbor_text}。"
    )


def _summarize_net_context_payload(question: str, payload: dict[str, Any]) -> str:
    status = str(payload.get("status") or "")
    net_name = str(payload.get("net_name") or "")
    if status == "not_found":
        matches = payload.get("closest_matches")
        suggestions = ", ".join(matches[:3]) if isinstance(matches, list) else ""
        return _localized(
            question,
            f"I could not find net {net_name}. Closest matches: {suggestions}.",
            f"我没有在当前 netlist 里找到网络 {net_name}。最接近的是: {suggestions}。",
        )
    members = payload.get("members") if isinstance(payload.get("members"), list) else []
    member_text = _format_members(members[:8])
    count = int(payload.get("member_count") or len(members))
    return _localized(
        question,
        f"Net {net_name} has {count} parsed member pins. Sample: {member_text}.",
        f"网络 {net_name} 有 {count} 个已解析成员引脚。样例: {member_text}。",
    )


def _summarize_net_search_payload(question: str, payload: dict[str, Any]) -> str:
    query = str(payload.get("query") or "")
    hits = payload.get("hits") if isinstance(payload.get("hits"), list) else []
    if not hits:
        matches = payload.get("closest_matches")
        suggestions = ", ".join(matches[:3]) if isinstance(matches, list) else ""
        return _localized(
            question,
            f"No parsed net names matched {query}. Closest matches: {suggestions}.",
            f"没有解析到匹配 {query} 的网络名。最接近的是: {suggestions}。",
        )
    rendered = []
    for hit in hits[:5]:
        if not isinstance(hit, dict):
            continue
        sample = _format_members(hit.get("sample_members") if isinstance(hit.get("sample_members"), list) else [])
        rendered.append(f"{hit.get('net_name')}({hit.get('member_count')}): {sample}")
    joined = "; ".join(rendered)
    return _localized(
        question,
        f"Parsed net search for {query} returned: {joined}.",
        f"按已解析 netlist 搜索 {query}，命中: {joined}。",
    )


def _summarize_topology_payload(question: str, payload: dict[str, Any]) -> str:
    totals = payload.get("validation_totals") if isinstance(payload.get("validation_totals"), dict) else {}
    power = _format_net_hits(payload.get("power_like_nets") if isinstance(payload.get("power_like_nets"), list) else [])
    interface = _format_net_hits(
        payload.get("interface_like_nets") if isinstance(payload.get("interface_like_nets"), list) else []
    )
    control = _format_net_hits(
        payload.get("control_like_nets") if isinstance(payload.get("control_like_nets"), list) else []
    )
    gaps = payload.get("profile_gap_groups") if isinstance(payload.get("profile_gap_groups"), list) else []
    first_gap = gaps[0] if gaps and isinstance(gaps[0], dict) else {}
    if _wants_english(question):
        return (
            "Topology summary is schematic/netlist-only: "
            f"{payload.get('component_count')} components, {payload.get('net_count')} nets, "
            f"validated={payload.get('validated_count')}, manual={payload.get('manual_count')}, "
            f"PASS/WARN/ERROR={totals.get('PASS', 0)}/{totals.get('WARN', 0)}/{totals.get('ERROR', 0)}. "
            f"Power-like nets: {power}. Interface-like nets: {interface}. Control-like nets: {control}. "
            f"First profile gap: {first_gap.get('identity', '-')} ({first_gap.get('refdes_count', 0)} refs)."
        )
    return (
        "拓扑摘要只基于解析后的原理图/netlist："
        f"{payload.get('component_count')} 个器件，{payload.get('net_count')} 条网络，"
        f"已验证 {payload.get('validated_count')} 个，待人工补档案 {payload.get('manual_count')} 个，"
        f"PASS/WARN/ERROR={totals.get('PASS', 0)}/{totals.get('WARN', 0)}/{totals.get('ERROR', 0)}。"
        f"电源类网络: {power}。接口类网络: {interface}。控制类网络: {control}。"
        f"首个器件档案缺口: {first_gap.get('identity', '-')}（{first_gap.get('refdes_count', 0)} 个位号）。"
    )


def _format_pin_nets(pins: list[Any], *, english: bool) -> str:
    rendered = []
    for pin in pins:
        if isinstance(pin, dict):
            rendered.append(f"{pin.get('pin_number')}/{pin.get('pin_name') or '-'}->{pin.get('net') or '-'}")
    if not rendered:
        return "none" if english else "无"
    return ", ".join(rendered)


def _format_neighbor_nets(neighbors: list[Any], *, english: bool) -> str:
    rendered = []
    for net in neighbors:
        if not isinstance(net, dict):
            continue
        members = net.get("members") if isinstance(net.get("members"), list) else []
        rendered.append(f"{net.get('net_name')}[{_format_members(members[:4])}]")
    if not rendered:
        return "none" if english else "无"
    return "; ".join(rendered)


def _format_members(members: list[Any]) -> str:
    rendered = []
    for member in members:
        if isinstance(member, dict):
            rendered.append(f"{member.get('refdes')}.{member.get('pin_number')}")
    return ", ".join(rendered) if rendered else "-"


def _format_net_hits(hits: list[Any]) -> str:
    rendered = []
    for hit in hits[:5]:
        if isinstance(hit, dict):
            rendered.append(f"{hit.get('net_name')}({hit.get('member_count')})")
    return ", ".join(rendered) if rendered else "-"


def _needs_document_coverage(question: str) -> bool:
    text = question.lower()
    if any(term in text for term in ("absolute maximum", "abs max", "rating", "rated", "绝对最大", "额定")):
        return False
    needles = (
        "public document",
        "document coverage",
        "document gap",
        "datasheet gap",
        "has datasheet",
        "have datasheet",
        "matched document",
        "公开资料",
        "资料覆盖",
        "资料缺口",
        "文档缺口",
        "datasheet 缺口",
        "缺 datasheet",
        "有没有 datasheet",
        "有没有数据手册",
        "有没有资料",
        "匹配到公开",
    )
    return any(needle in text for needle in needles)


def _needs_document_summary(question: str) -> bool:
    text = question.lower()
    return any(term in text for term in ("gap", "coverage", "缺口", "哪些", "summary", "summarize"))


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


def _is_evidence_chain_smoke(question: str) -> bool:
    text = question.lower()
    return "evidence-chain smoke" in text or "证据链" in question


def _important_checks(checks: list[Any], *, localized: bool = False) -> list[str]:
    rendered: list[str] = []
    for status in ("ERROR", "WARN"):
        for check in checks:
            if not isinstance(check, dict) or check.get("status") != status:
                continue
            name = str(check.get("check") or "check")
            summary = str(check.get("summary") or "")
            if localized:
                name = check_label(name)
            if localized:
                summary = validation_summary_label(summary)
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
