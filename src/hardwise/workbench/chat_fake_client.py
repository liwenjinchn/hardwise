"""Anthropic-compatible deterministic fake client and snapshot collection."""

from __future__ import annotations

from typing import Any

from hardwise.workbench.chat_fake_parsing import (
    _FakeResponse,
    _FakeTextBlock,
    _FakeToolUseBlock,
    _choose_refdes,
    _document_payload,
    _evidence_locator_payload,
    _is_evidence_chain_smoke,
    _locator_topic,
    _needs_datasheet_search,
    _needs_document_coverage,
    _needs_document_summary,
    _needs_evidence_locator,
    _parse_runner_prompt,
    _search_payload,
    _tool_payloads,
    _topology_payload,
    _topology_tool_uses,
    _validation_payload,
    _wants_english,
    _localized,
)
from hardwise.workbench.chat_fake_responses import (
    _evidence_from_checks,
    _important_checks,
    _summarize_component_context_payload,
    _summarize_net_context_payload,
    _summarize_net_search_payload,
    _summarize_topology_payload,
)


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
        if _needs_evidence_locator(self._last_question):
            return _FakeResponse(
                [
                    _FakeToolUseBlock(
                        id=f"hw_fake_{self._turn}_evidence_locator",
                        name="locate_component_evidence",
                        input={
                            "refdes": refdes,
                            "topic": _locator_topic(self._last_question),
                            "limit": 8,
                        },
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
        evidence_locator_payload = _evidence_locator_payload(payloads)
        validation_payload = _validation_payload(payloads)
        if topology_payload is not None:
            return self._answer_from_topology_result(topology_payload)
        if evidence_locator_payload is not None:
            return self._answer_from_evidence_locator_result(evidence_locator_payload)
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
                    "这次原理图检验工具没有配置向量数据手册搜索。先回退到结构化器件档案/验证证据："
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
            return (
                "The tool returned a result, but this fake workbench mode cannot summarize it yet."
            )
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
            counts = (
                payload.get("counts_by_status")
                if isinstance(payload.get("counts_by_status"), dict)
                else {}
            )
            groups = payload.get("groups") if isinstance(payload.get("groups"), list) else []
            missing = [
                group
                for group in groups
                if isinstance(group, dict)
                and group.get("document_status") in {"no_result", "ambiguous", "manual_needed"}
            ]
            first = (
                missing[0]
                if missing
                else (groups[0] if groups and isinstance(groups[0], dict) else {})
            )
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
        candidates = (
            payload.get("candidates") if isinstance(payload.get("candidates"), list) else []
        )
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

    def _answer_from_evidence_locator_result(self, payload: dict[str, Any]) -> str:
        status = str(payload.get("status") or "")
        refdes = str(payload.get("refdes") or self._last_selected or "")
        topic = str(payload.get("normalized_topic") or payload.get("topic") or "evidence")
        hits = payload.get("hits") if isinstance(payload.get("hits"), list) else []
        if status == "found" and hits:
            rendered = []
            evidence: list[str] = []
            for hit in hits[:3]:
                if not isinstance(hit, dict):
                    continue
                title = str(hit.get("title") or hit.get("fact_key") or "fact")
                tokens = hit.get("evidence") if isinstance(hit.get("evidence"), list) else []
                token_text = ", ".join(str(token) for token in tokens[:3]) or "no direct token"
                rendered.append(f"{title}: {token_text}")
                for token in tokens:
                    token = str(token)
                    if token and token not in evidence:
                        evidence.append(token)
            if _wants_english(self._last_question):
                return (
                    f"{refdes} {topic} evidence is from reviewed profile facts, not broad "
                    f"datasheet chat: {'; '.join(rendered)}."
                )
            return (
                f"{refdes} 的 {topic} 证据来自已审结构化 profile，不是自由 datasheet 问答："
                f"{'；'.join(rendered)}。"
            )
        if status == "no_profile":
            if _wants_english(self._last_question):
                return (
                    f"{refdes} exists, but no reviewed DatasheetProfile is assigned. "
                    "Document coverage, if present, is not electrical proof."
                )
            return (
                f"{refdes} 在板上，但没有已审结构化 DatasheetProfile。"
                "即使有资料覆盖，也不能当作电气规格证据。"
            )
        if status == "not_found":
            matches = payload.get("closest_matches")
            suggestions = ", ".join(matches[:3]) if isinstance(matches, list) else ""
            if _wants_english(self._last_question):
                return f"I could not find {refdes}. Closest matches: {suggestions}."
            return f"我没有在当前设计里找到 {refdes}。最接近的是: {suggestions}。"
        if _wants_english(self._last_question):
            return f"No reviewed profile evidence matched {refdes} topic {topic}."
        return f"没有找到 {refdes} 关于 {topic} 的已审 profile evidence。"


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
                [("Absolute maximum ratings table: input voltage VI is 35 V for VO = 5 to 18 V.")]
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
