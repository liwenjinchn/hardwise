"""Shared facts and primitive checks for generic passives."""

from __future__ import annotations

from hardwise.validation.assessment import result_for_attention, severity_for_attention

import re
from typing import Literal

from hardwise.bom.types import BomRow
from hardwise.ir.types import Component
from hardwise.validation.passive_contracts import (
    FAMILY_LABELS as _FAMILY_LABELS,
)
from hardwise.validation.passive_contracts import PassiveFamily
from hardwise.validation.types import ComponentValidation, PinValidation
from hardwise.validation.value_parsing import ParsedCurrentRating


def _component_value(component: Component, bom_row: BomRow | None) -> str:
    return (bom_row.value if bom_row and bom_row.value else component.value) or ""


def _bom_evidence(bom_row: BomRow | None) -> list[str]:
    if bom_row is None:
        return []
    return [f"bom:{bom_row.source_file.name}#line{bom_row.source_line}"]


def _terminal_connectivity(
    component: Component,
    family: PassiveFamily,
    evidence: list[str],
) -> list[PinValidation]:
    label = _FAMILY_LABELS[family]
    return [
        PinValidation(
            pin_number=pin.number,
            pin_name=pin.name or f"Terminal {pin.number}",
            category=f"generic_{family}_terminal",
            result=result_for_attention("PASS" if pin.net else "ERROR", warning_result="UNKNOWN"),
            severity=severity_for_attention("PASS" if pin.net else "ERROR"),
            evidence_kind="SOURCE_FACT",
            net=pin.net,
            summary=(
                f"Generic {label} terminal is connected to {pin.net}."
                if pin.net
                else f"Generic {label} terminal is not connected in the schematic/netlist."
            ),
            evidence=evidence,
        )
        for pin in component.pins
    ]


def _value_check(
    component: Component,
    check: str,
    label: str,
    value: str,
    parsed: bool,
    evidence: list[str],
) -> ComponentValidation:
    return ComponentValidation(
        check=check,
        result=result_for_attention("PASS" if parsed else "WARN", warning_result="UNKNOWN"),
        severity=severity_for_attention("PASS" if parsed else "WARN"),
        evidence_kind="SOURCE_FACT",
        refdes=component.refdes,
        summary=(
            f"{label} value was parsed from BOM/component value '{value}'."
            if parsed
            else f"{label} value could not be parsed deterministically from '{value}'."
        ),
        evidence=evidence,
    )


def _package_check(
    component: Component,
    family: PassiveFamily,
    evidence: list[str],
) -> ComponentValidation:
    package = component.package or ""
    if not package:
        return ComponentValidation(
            check=f"{family}_package_presence",
            result="UNKNOWN",
            severity="WARNING",
            evidence_kind="DERIVED",
            refdes=component.refdes,
            summary=f"Generic {family} check has no schematic package field to inspect.",
            evidence=evidence,
        )

    upper = package.upper()
    conflict = _passive_package_conflict(family, upper)
    return ComponentValidation(
        check=f"{family}_package_presence",
        result=result_for_attention("WARN" if conflict else "PASS", warning_result="FAIL"),
        severity=severity_for_attention("WARN" if conflict else "PASS"),
        evidence_kind="DERIVED",
        refdes=component.refdes,
        summary=(
            f"Schematic package '{package}' looks inconsistent with generic {family} family."
            if conflict
            else f"Schematic package '{package}' is present for generic {family} review."
        ),
        evidence=evidence,
    )


def _passive_package_conflict(family: PassiveFamily, upper_package: str) -> bool:
    conflict_patterns: dict[PassiveFamily, tuple[str, ...]] = {
        "capacitor": (r"R\d", r"L\d", r"FB\d"),
        "resistor": (r"C\d", r"L\d", r"FB\d"),
        "inductor": (r"C\d", r"R\d", r"FB\d"),
        "ferrite": (r"C\d", r"R\d", r"L\d"),
    }
    return any(re.match(pattern, upper_package) for pattern in conflict_patterns[family])


def _current_rating_token_check(
    component: Component,
    family: Literal["inductor", "ferrite"],
    value: str,
    current_rating: ParsedCurrentRating | None,
    evidence: list[str],
) -> ComponentValidation:
    label = _FAMILY_LABELS[family]
    if current_rating is None:
        summary = (
            f"Generic {label} BOM/component value '{value}' has no explicit current-rating "
            "token; current, ripple, and saturation suitability were not checked."
        )
    else:
        summary = (
            f"Generic {label} current-rating token {current_rating.token} "
            f"({current_rating.amps:g} A) was parsed from '{value}'; current, ripple, "
            "and saturation suitability were not checked without topology/profile evidence."
        )
    return ComponentValidation(
        check=f"{family}_current_rating_token",
        result="PASS" if current_rating is not None else "UNKNOWN",
        evidence_kind="SOURCE_FACT",
        severity="INFO",
        refdes=component.refdes,
        summary=summary,
        evidence=evidence,
    )
