"""Shared display helpers for deterministic component validation reports."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from hardwise.guards.evidence_class import EvidenceClassification, classify_evidence_token
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.trust import TRUST_LABELS, TrustTier, trust_label_text
from hardwise.validation.pin_resolver import schematic_pin_for_profile_pin
from hardwise.validation.types import ValidationReport

__all__ = [
    "TRUST_LABELS",
    "TrustTier",
    "trust_label_text",
    "trust_label_html",
    "evidence_chips_html",
    "evidence_source_label",
    "evidence_gap_chip",
    "build_pin_consistency",
    "schematic_connection_path",
    "profile_has_thermal_or_package_evidence",
]


@dataclass(frozen=True)
class PinConsistency:
    """Display-only comparison between profiled pins and schematic pins."""

    status: str
    profile_pin_count: int
    schematic_pin_count: int
    missing_schematic: tuple[str, ...]
    extra_schematic: tuple[str, ...]

    @property
    def note(self) -> str:
        if self.status == "PASS":
            return "器件档案引脚与原理图引脚在当前检验范围内一致。"
        details: list[str] = []
        if self.missing_schematic:
            details.append(f"原理图缺少引脚：{', '.join(self.missing_schematic)}")
        if self.extra_schematic:
            details.append(f"原理图多出引脚：{', '.join(self.extra_schematic)}")
        return "；".join(details) or "器件档案与原理图的引脚数量不同。"


def build_pin_consistency(
    component: Component,
    report: ValidationReport,
    profile: DatasheetProfile | None = None,
) -> PinConsistency:
    """Compare profile/report pins with parsed schematic pins without changing verdicts."""

    profile_numbers = {pin.number for pin in profile.pins} if profile is not None else {
        pin.pin_number for pin in report.pin_results
    }
    schematic_numbers = {pin.number for pin in component.pins}
    if profile is not None:
        resolved_schematic = {
            pin.number
            for profile_pin in profile.pins
            for pin in [schematic_pin_for_profile_pin(component, profile_pin)]
            if pin is not None
        }
        missing = tuple(
            sorted(
                [
                    pin.number
                    for pin in profile.pins
                    if schematic_pin_for_profile_pin(component, pin) is None
                ],
                key=_pin_sort_key,
            )
        )
        extra = tuple(sorted(schematic_numbers - resolved_schematic, key=_pin_sort_key))
    else:
        missing = tuple(sorted(profile_numbers - schematic_numbers, key=_pin_sort_key))
        extra = tuple(sorted(schematic_numbers - profile_numbers, key=_pin_sort_key))
    status = "PASS" if not missing and not extra else "WARN"
    return PinConsistency(
        status=status,
        profile_pin_count=len(profile_numbers),
        schematic_pin_count=len(schematic_numbers),
        missing_schematic=missing,
        extra_schematic=extra,
    )


def schematic_connection_path(
    component: Component,
    design: Design,
    pin_number: str,
    net_name: str | None,
    *,
    neighbor_limit: int = 4,
) -> str:
    """Return a bounded schematic-topology path for display only."""

    if not net_name:
        return "-"

    endpoint = f"{component.refdes}-{pin_number}"
    net = design.nets.get(net_name)
    if net is None:
        return f"{net_name} -> {endpoint}"

    current = (component.refdes, pin_number)
    neighbors = sorted(
        (node for node in net.nodes if node != current),
        key=lambda node: (_refdes_sort_key(node[0]), _pin_sort_key(node[1])),
    )
    segments = [net.name]
    if neighbors:
        shown = neighbors[:neighbor_limit]
        rendered = [f"{refdes}.{number}" for refdes, number in shown]
        remaining = len(neighbors) - len(shown)
        if remaining:
            rendered.append(f"+{remaining} 处")
        segments.append(" / ".join(rendered))
    segments.append(endpoint)
    return " -> ".join(segments)


def profile_has_thermal_or_package_evidence(profile: DatasheetProfile | None) -> bool:
    """Return whether profile evidence names a thermal/package source token."""

    if profile is None:
        return False
    markers = ("thermal", "theta", "rth", "tj", "junction", "package", "power_dissipation")
    return any(any(marker in key.lower() for marker in markers) for key in profile.evidence)


def trust_label_html(tier: TrustTier) -> str:
    """Render a short trust-tier label without changing validation status."""

    label = trust_label_text(tier)
    display = {
        "l1": "L1 确定性",
        "l2": "L2 有出处",
        "l3": "L3 人工确认",
    }[tier]
    return f'<span class="trust trust-{tier}" title="{escape(label)}">{escape(display)}</span>'


def evidence_chips_html(tokens: list[str], *, refdes: str | None = None) -> str:
    """Render copyable/searchable source tokens as compact HTML chips."""

    if not tokens:
        return '<span class="muted">-</span>'
    chips = []
    for token in tokens:
        source = token.split(":", 1)[0] if ":" in token else "source"
        href = _evidence_href(token, refdes=refdes)
        classification = classify_evidence_token(token)
        label = _evidence_source_label(classification)
        title = _evidence_title(token, classification)
        local_source_attr = (
            f' data-evidence-local-source="{escape(classification.local_source)}"'
            if classification.local_source
            else ""
        )
        chips.append(
            '<a class="evidence-chip" '
            f'data-source="{escape(source)}" '
            f'data-evidence-source-class="{escape(classification.source_class)}" '
            f'data-evidence-audit-status="{escape(classification.audit_status)}" '
            f'data-evidence-token="{escape(token)}" '
            f'href="{escape(href)}" title="{escape(title)}"{local_source_attr}>'
            f'{escape(token)} <span class="evidence-source-class">{escape(label)}</span></a>'
        )
    return " ".join(chips)


def evidence_source_label(token: str) -> str:
    """Return the display source class for one evidence token."""

    return _evidence_source_label(classify_evidence_token(token))


def _evidence_source_label(classification: EvidenceClassification) -> str:
    if classification.audit_status != "ok":
        return f"{classification.source_class}/{classification.audit_status}"
    return classification.source_class


def _evidence_href(token: str, *, refdes: str | None = None) -> str:
    """Return a safe in-page or external href for a visible evidence token."""

    if token.startswith(("http://", "https://")):
        return token
    if token.startswith("datasheet:"):
        return f"#{refdes}-evidence-details" if refdes else "#evidence-details"
    if token.startswith(("bom:", "doc:")):
        return "#component-index"
    if token.startswith("sch:"):
        return f"#{refdes}-connection-path" if refdes else "#connection-path"
    return f"#{refdes}-evidence-details" if refdes else "#evidence-details"


def _evidence_title(token: str, classification: EvidenceClassification) -> str:
    """Return a concise explanation for evidence-token chips."""

    if token.startswith("datasheet:"):
        title = "数据手册页码来源 token；点击跳到当前器件的证据详情，并复制 token。"
    elif token.startswith("bom:"):
        title = "BOM 行来源 token；点击跳到器件/覆盖清单，并复制 token。"
    elif token.startswith("doc:"):
        title = "本地公开资料索引 token；点击跳到器件/覆盖清单，并复制 token。"
    elif token.startswith("sch:"):
        title = "原理图拓扑来源 token；点击跳到连接路径，并复制 token。"
    elif token.startswith(("http://", "https://")):
        title = "打开外部来源链接。"
    else:
        title = "证据 token；点击复制。"
    return (
        f"{title} source_class={classification.source_class}; "
        f"audit_status={classification.audit_status}; {classification.reason}"
    )


def evidence_gap_chip(
    claim_key: str,
    value: object,
    evidence: dict[str, str],
) -> str:
    """Return gap warning HTML when a numeric datasheet spec has no source token.

    A fact is considered covered when its evidence key is present either exactly
    (``recommended.vin_max``) or by first-segment grouping (``recommended.inductor``
    backing ``recommended.inductor_min_uh``). Only numeric specs are flagged — text
    descriptors like ``topology_family=buck`` are design classifications, not
    datasheet quantities that demand a page citation. Board-topology (``sch:``),
    rule (``rule:``), and document-index (``doc:``) tokens are legitimate sources
    and never produce a gap.
    """

    is_numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
    if not is_numeric:
        return ""
    if _fact_has_evidence(claim_key, evidence):
        return ""
    return '<span class="evidence-gap" title="此规格声明应有 datasheet 页码来源但当前缺失">⚠ 无页码证据</span>'


def _fact_has_evidence(claim_key: str, evidence: dict[str, str]) -> bool:
    """Return whether a claim is covered by an exact or first-segment evidence key."""

    if evidence.get(claim_key):
        return True
    if "." not in claim_key:
        return False
    group, _, leaf = claim_key.partition(".")
    segment = leaf.split("_")[0]
    for key, token in evidence.items():
        if not token or "." not in key:
            continue
        key_group, _, key_leaf = key.partition(".")
        if key_group != group:
            continue
        if key_leaf.split("_")[0] == segment:
            return True
    return False


def _pin_sort_key(value: str) -> tuple[int, int | str]:
    if value.isdigit():
        return (0, int(value))
    return (1, value)


def _refdes_sort_key(value: str) -> tuple[str, int, str]:
    prefix = ""
    number = ""
    suffix = ""
    for char in value:
        if char.isdigit() and not suffix:
            number += char
        elif number:
            suffix += char
        else:
            prefix += char
    return (prefix, int(number or 0), suffix)
