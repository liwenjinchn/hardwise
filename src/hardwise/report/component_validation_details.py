"""Shared display helpers for deterministic component validation reports."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.trust import TRUST_LABELS, TrustTier, trust_label_text
from hardwise.validation.types import ValidationReport

__all__ = [
    "TRUST_LABELS",
    "TrustTier",
    "trust_label_text",
    "trust_label_html",
    "evidence_chips_html",
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
            return "Profiled pins and schematic pins match for the rendered review scope."
        details: list[str] = []
        if self.missing_schematic:
            details.append(f"missing schematic pins: {', '.join(self.missing_schematic)}")
        if self.extra_schematic:
            details.append(f"extra schematic pins: {', '.join(self.extra_schematic)}")
        return "; ".join(details) or "pin count differs between profile and schematic."


def build_pin_consistency(
    component: Component,
    report: ValidationReport,
    profile: DatasheetProfile | None = None,
) -> PinConsistency:
    """Compare profile/report pins with parsed schematic pins without changing verdicts."""

    profile_numbers = (
        {pin.number for pin in profile.pins}
        if profile is not None
        else {pin.pin_number for pin in report.pin_results}
    )
    schematic_numbers = {pin.number for pin in component.pins}
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
            rendered.append(f"+{remaining} more")
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
    return f'<span class="trust trust-{tier}">{escape(label)}</span>'


def evidence_chips_html(tokens: list[str]) -> str:
    """Render copyable/searchable source tokens as compact HTML chips."""

    if not tokens:
        return '<span class="muted">-</span>'
    chips = []
    for token in tokens:
        source = token.split(":", 1)[0] if ":" in token else "source"
        chips.append(
            '<span class="evidence-chip" '
            f'data-source="{escape(source)}">{escape(token)}</span>'
        )
    return " ".join(chips)


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
