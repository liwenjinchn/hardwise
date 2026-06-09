"""Scoped datasheet/profile evidence locator for workbench questions.

The locator is intentionally narrower than ``search_datasheet``. It does not
search PDFs or infer new electrical facts; it only points to evidence already
present in reviewed ``DatasheetProfile`` objects, with document-index coverage
kept as a clearly labeled non-spec fallback.
"""

from __future__ import annotations

import difflib
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from hardwise.bom.types import sort_refdes_key
from hardwise.documents.types import DocumentMatchReport
from hardwise.ir.profile import DatasheetProfile, PinProfile, ProfileValue
from hardwise.ir.types import Component, Design
from hardwise.validation.project_index import ProjectValidationIndex, ProjectValidationRow


EvidenceLocatorStatus = Literal[
    "found",
    "no_result",
    "no_profile",
    "not_found",
    "not_configured",
]
EvidenceLocatorSourceKind = Literal[
    "profile_fact",
    "profile_pin",
    "validation_check",
    "document_coverage",
]


class LocateComponentEvidenceInput(BaseModel):
    """Bounded lookup for one component's reviewed datasheet/profile evidence."""

    refdes: str
    topic: str = Field(
        default="all",
        description=(
            "Bounded topic such as abs_max, recommended, pin_function, enable, "
            "reset, boot, bootstrap, decoupling, power, or debug."
        ),
    )
    pin_number: str | None = Field(
        default=None,
        description="Optional exact package pin number to narrow profile pin facts.",
    )
    limit: int = Field(default=12, ge=1, le=50)


class EvidenceLocatorHit(BaseModel):
    """One located reviewed-profile or document-coverage evidence row."""

    source_kind: EvidenceLocatorSourceKind
    topic: str
    fact_key: str
    title: str
    value: str
    pin_number: str | None = None
    pin_name: str | None = None
    evidence: list[str] = Field(default_factory=list)
    note: str = ""


class LocateComponentEvidenceResult(BaseModel):
    """Structured result for a scoped evidence lookup."""

    status: EvidenceLocatorStatus
    found: bool
    refdes: str
    topic: str
    normalized_topic: str
    profile_part_number: str = ""
    document_status: str = "not_configured"
    reason: str = ""
    hits: list[EvidenceLocatorHit] = Field(default_factory=list)
    closest_matches: list[str] = Field(default_factory=list)


EVIDENCE_LOCATOR_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "locate_component_evidence",
        "description": (
            "Locate reviewed DatasheetProfile evidence for one exact component refdes "
            "and a bounded topic such as abs_max, recommended application/topology, "
            "pin_function, enable, reset, boot, bootstrap, decoupling, power, or debug. "
            "This is not broad datasheet chat and does not search PDFs. If no reviewed "
            "profile exists, it returns no_profile and may include document-index "
            "coverage only as a non-spec fallback."
        ),
        "input_schema": LocateComponentEvidenceInput.model_json_schema(),
    }
]


def locate_component_evidence(
    design: Design | None,
    targets: dict[str, DatasheetProfile],
    project_index: ProjectValidationIndex | None,
    document_report: DocumentMatchReport | None,
    tool_input: LocateComponentEvidenceInput,
) -> LocateComponentEvidenceResult:
    """Locate reviewed profile evidence for one component/topic pair."""

    normalized_topic = normalize_evidence_topic(tool_input.topic)
    if design is None:
        return LocateComponentEvidenceResult(
            status="not_configured",
            found=False,
            refdes=tool_input.refdes,
            topic=tool_input.topic,
            normalized_topic=normalized_topic,
            reason="No IR Design is loaded for this run.",
        )

    refdes = tool_input.refdes
    component = design.components.get(refdes)
    if component is None:
        return LocateComponentEvidenceResult(
            status="not_found",
            found=False,
            refdes=refdes,
            topic=tool_input.topic,
            normalized_topic=normalized_topic,
            reason="Refdes is not present in the parsed EDA registry.",
            closest_matches=_closest(refdes, design.components.keys()),
        )

    profile = targets.get(refdes)
    document_hit, document_status = _document_coverage_hit(
        project_index,
        document_report,
        refdes,
        normalized_topic,
    )
    if profile is None:
        hits = [document_hit] if document_hit is not None else []
        return LocateComponentEvidenceResult(
            status="no_profile",
            found=False,
            refdes=refdes,
            topic=tool_input.topic,
            normalized_topic=normalized_topic,
            document_status=document_status,
            reason=(
                "This refdes has no assigned reviewed DatasheetProfile; "
                "document coverage is not electrical proof."
            ),
            hits=hits[: tool_input.limit],
        )

    hits = [
        *_profile_fact_hits(profile, normalized_topic, tool_input.pin_number),
        *_profile_pin_hits(profile, component, normalized_topic, tool_input.pin_number),
        *_validation_hits(project_index, refdes, normalized_topic),
    ]
    hits = _dedupe_hits(hits)[: tool_input.limit]
    return LocateComponentEvidenceResult(
        status="found" if hits else "no_result",
        found=bool(hits),
        refdes=refdes,
        topic=tool_input.topic,
        normalized_topic=normalized_topic,
        profile_part_number=profile.part_number,
        document_status=document_status,
        reason=(
            "Located reviewed profile evidence."
            if hits
            else "No reviewed profile fact matched this bounded topic."
        ),
        hits=hits,
    )


def evidence_locator_tokens(result: LocateComponentEvidenceResult) -> list[str]:
    """Collect unique evidence tokens from a locator result."""

    tokens: list[str] = []
    for hit in result.hits:
        for token in hit.evidence:
            if token and token not in tokens:
                tokens.append(token)
    return tokens


def normalize_evidence_topic(topic: str | None) -> str:
    """Map user-facing topic text into a small deterministic topic set."""

    text = (topic or "all").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "all": ("all", "*", "any", "全部", "所有"),
        "abs_max": (
            "abs_max",
            "absolute_max",
            "absolute_maximum",
            "rating",
            "ratings",
            "rated",
            "limit",
            "limits",
            "绝对最大",
            "额定",
            "耐压",
        ),
        "recommended": (
            "recommended",
            "recommendation",
            "application",
            "topology",
            "typical_application",
            "应用",
            "推荐",
            "拓扑",
        ),
        "pin_function": ("pin", "pin_function", "pinout", "引脚", "管脚", "功能"),
        "enable": ("enable", "en", "on_off", "on/off", "shutdown", "使能"),
        "reset": ("reset", "rst", "nrst", "复位"),
        "boot": ("boot", "boot0", "启动"),
        "bootstrap": ("bootstrap", "bst", "vb", "自举"),
        "decoupling": ("decoupling", "bypass", "capacitor", "cap", "去耦", "旁路"),
        "power": ("power", "rail", "supply", "vin", "vout", "vcc", "vdd", "gnd", "电源"),
        "debug": ("debug", "swd", "swclk", "swdio", "jtag", "调试"),
    }
    for canonical, values in aliases.items():
        if text in values:
            return canonical
    if "absolute" in text or "abs" in text:
        return "abs_max"
    if "boot" in text:
        return "boot"
    if "reset" in text or "nrst" in text:
        return "reset"
    if "swd" in text or "debug" in text:
        return "debug"
    return text or "all"


def _profile_fact_hits(
    profile: DatasheetProfile,
    topic: str,
    pin_number: str | None,
) -> list[EvidenceLocatorHit]:
    hits: list[EvidenceLocatorHit] = []
    if pin_number is not None:
        return hits

    for namespace, facts in (
        ("abs_max", profile.abs_max),
        ("recommended", profile.recommended),
        ("pin_function", profile.pin_function),
    ):
        for key, value in facts.items():
            fact_key = f"{namespace}.{key}"
            title = f"{_namespace_label(namespace)} · {key}"
            corpus = f"{namespace} {key} {title} {_value_text(value)}"
            if not _matches_topic(corpus, topic):
                continue
            hits.append(
                EvidenceLocatorHit(
                    source_kind="profile_fact",
                    topic=topic,
                    fact_key=fact_key,
                    title=title,
                    value=_value_text(value),
                    pin_number=key if namespace == "pin_function" else None,
                    evidence=_profile_fact_evidence(profile, fact_key),
                    note="Reviewed DatasheetProfile fact; not live PDF search.",
                )
            )
    return hits


def _profile_pin_hits(
    profile: DatasheetProfile,
    component: Component,
    topic: str,
    pin_number: str | None,
) -> list[EvidenceLocatorHit]:
    schematic_pins = {pin.number: pin for pin in component.pins}
    hits: list[EvidenceLocatorHit] = []
    for pin in profile.pins:
        if pin_number is not None and pin.number != pin_number:
            continue
        schematic_pin = schematic_pins.get(pin.number)
        corpus = _pin_corpus(pin, schematic_pin.net if schematic_pin is not None else "")
        if not _matches_topic(corpus, topic):
            continue
        value = _pin_value(pin)
        hits.append(
            EvidenceLocatorHit(
                source_kind="profile_pin",
                topic=topic,
                fact_key=f"pins.{pin.number}",
                title=f"Pin {pin.number} {pin.name} · {pin.category}",
                value=value,
                pin_number=pin.number,
                pin_name=pin.name,
                evidence=_dedupe([*pin.evidence, profile.evidence.get(f"pins.{pin.number}", "")]),
                note="Reviewed profile pin fact; schematic net shown only for orientation.",
            )
        )
    return hits


def _validation_hits(
    project_index: ProjectValidationIndex | None,
    refdes: str,
    topic: str,
) -> list[EvidenceLocatorHit]:
    row = _row_for_refdes(project_index, refdes)
    if row is None or row.validation is None:
        return []
    hits: list[EvidenceLocatorHit] = []
    checks = [
        *[
            (
                pin.pin_name or pin.pin_number,
                pin.summary,
                pin.evidence,
                pin.pin_number,
                pin.pin_name,
            )
            for pin in row.validation.pin_results
        ],
        *[
            (check.check, check.summary, check.evidence, None, None)
            for check in row.validation.component_checks
        ],
    ]
    for name, summary, evidence, pin_number, pin_name in checks:
        corpus = f"{name} {summary} {' '.join(evidence)}"
        if not evidence or not _matches_topic(corpus, topic):
            continue
        hits.append(
            EvidenceLocatorHit(
                source_kind="validation_check",
                topic=topic,
                fact_key=f"validation.{name}",
                title=f"Validation evidence · {name}",
                value=summary,
                pin_number=pin_number,
                pin_name=pin_name,
                evidence=_dedupe(evidence),
                note="Existing deterministic validation evidence; verdict is not recalculated here.",
            )
        )
    return hits


def _document_coverage_hit(
    project_index: ProjectValidationIndex | None,
    document_report: DocumentMatchReport | None,
    refdes: str,
    topic: str,
) -> tuple[EvidenceLocatorHit | None, str]:
    if project_index is None:
        return None, "not_configured"
    group = next((item for item in project_index.component_groups if refdes in item.refdes), None)
    if group is None:
        return None, "not_found"
    if document_report is None or group.document_status == "not_requested":
        return None, group.document_status
    if group.document_source is None and group.document_title is None:
        return None, group.document_status
    return (
        EvidenceLocatorHit(
            source_kind="document_coverage",
            topic=topic,
            fact_key=f"document.{group.group_id}",
            title=group.document_title or "Matched public document",
            value=group.document_url or group.document_reason,
            evidence=[group.document_source] if group.document_source else [],
            note=(
                "Document-index coverage only; this is not proof of voltage, pinout, "
                "timing, or topology facts."
            ),
        ),
        group.document_status,
    )


def _profile_fact_evidence(profile: DatasheetProfile, fact_key: str) -> list[str]:
    tokens: list[str] = []
    _append(tokens, profile.evidence.get(fact_key))
    namespace, _dot, key = fact_key.partition(".")
    if namespace == "pin_function":
        _append(tokens, profile.evidence.get(f"pins.{key}"))
    if namespace == "recommended":
        key_parts = set(_words(key))
        for evidence_key, token in profile.evidence.items():
            if not evidence_key.startswith("recommended."):
                continue
            if key_parts & set(_words(evidence_key.removeprefix("recommended."))):
                _append(tokens, token)
    return tokens


def _matches_topic(corpus: str, topic: str) -> bool:
    if topic == "all":
        return True
    text = corpus.lower()
    needles = {
        "abs_max": ("abs_max", "absolute", "rating", "rated", "limit", "limits", "耐压", "额定"),
        "recommended": (
            "recommended",
            "topology",
            "application",
            "typical",
            "connect",
            "推荐",
            "拓扑",
        ),
        "pin_function": ("pin_function", "pin ", "pin.", "function", "pinout", "引脚", "管脚"),
        "enable": ("enable", " on/off", "on_off", "shutdown", " en ", "使能"),
        "reset": ("reset", "nrst", "rst", "复位"),
        "boot": ("boot", "boot0", "启动"),
        "bootstrap": ("bootstrap", " bst", " vb ", "bootstrap_supply", "自举"),
        "decoupling": ("decouple", "decoupling", "bypass", "capacitor", " cap", "去耦", "旁路"),
        "power": ("power", "supply", "ground", "rail", "vin", "vout", "vcc", "vdd", "gnd", "电源"),
        "debug": ("debug", "swd", "swclk", "swdio", "jtag", "调试"),
    }.get(topic, (topic,))
    padded = f" {text} "
    return any(needle in padded for needle in needles)


def _pin_corpus(pin: PinProfile, schematic_net: str) -> str:
    fields = [
        "pin_function",
        pin.number,
        pin.name,
        pin.category,
        pin.function,
        schematic_net,
        json.dumps(pin.limits, ensure_ascii=False, sort_keys=True),
        " ".join(pin.recommended_topology),
        " ".join(pin.evidence),
    ]
    return " ".join(item for item in fields if item)


def _pin_value(pin: PinProfile) -> str:
    parts = [pin.function]
    if pin.limits:
        parts.append(f"limits={json.dumps(pin.limits, ensure_ascii=False, sort_keys=True)}")
    if pin.recommended_topology:
        parts.append("topology=" + " ".join(pin.recommended_topology))
    return "; ".join(part for part in parts if part)


def _value_text(value: ProfileValue | Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _namespace_label(namespace: str) -> str:
    return {
        "abs_max": "Absolute maximum",
        "recommended": "Recommended",
        "pin_function": "Pin function",
    }.get(namespace, namespace)


def _row_for_refdes(
    project_index: ProjectValidationIndex | None,
    refdes: str,
) -> ProjectValidationRow | None:
    if project_index is None:
        return None
    return next((row for row in project_index.rows if row.refdes == refdes), None)


def _closest(value: str, candidates: Any) -> list[str]:
    ordered = sorted(candidates, key=sort_refdes_key)
    return difflib.get_close_matches(value, ordered, n=5, cutoff=0.45) or ordered[:5]


def _dedupe_hits(hits: list[EvidenceLocatorHit]) -> list[EvidenceLocatorHit]:
    seen: set[tuple[str, str, str | None]] = set()
    deduped: list[EvidenceLocatorHit] = []
    for hit in hits:
        key = (hit.source_kind, hit.fact_key, hit.pin_number)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(hit)
    return deduped


def _dedupe(tokens: list[str]) -> list[str]:
    out: list[str] = []
    for token in tokens:
        if token and token not in out:
            out.append(token)
    return out


def _append(tokens: list[str], token: str | None) -> None:
    if token and token not in tokens:
        tokens.append(token)


def _words(value: str) -> list[str]:
    return [part for part in re.split(r"[^a-zA-Z0-9]+", value.lower()) if part]
