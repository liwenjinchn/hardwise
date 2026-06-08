"""External reviewer risk hints anchored to registry-verified refdes.

This module is intentionally narrow: it only imports external JSON hints and
keeps entries whose anchor refdes exists in the current ``Design``. It does not
generate validator, BOM, profile-gap, renderer, CLI, or workbench hints.
"""

from __future__ import annotations

import json
from difflib import get_close_matches
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from hardwise.adapters.base import BoardRegistry, ComponentRecord
from hardwise.bom.types import sort_refdes_key
from hardwise.guards.refdes import sanitize_text
from hardwise.ir.types import Design


class RiskHintInput(BaseModel):
    """One externally supplied reviewer hint before registry validation."""

    refdes: str
    title: str
    body: str
    severity: str | None = None
    source: str | None = None

    @field_validator("refdes", "title", "body", mode="before")
    @classmethod
    def _coerce_required_text(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value)

    @field_validator("severity", "source", mode="before")
    @classmethod
    def _coerce_optional_text(cls, value: object) -> str | None:
        if value is None:
            return None
        return str(value)


class RiskHintsPayload(BaseModel):
    """Top-level JSON shape accepted by future adapters."""

    hints: list[RiskHintInput] = Field(default_factory=list)


class RiskHint(BaseModel):
    """A reviewer hint whose anchor refdes is present in the parsed design."""

    refdes: str
    title: str
    body: str
    severity: str | None = None
    source: str | None = None
    input_index: int
    wrapped_refdes_count: int = 0


class RejectedRiskHint(BaseModel):
    """A hint skipped before display because it cannot be safely anchored."""

    input_index: int
    reason: str
    refdes: str = ""
    title: str = ""
    closest_matches: list[str] = Field(default_factory=list)
    wrapped_refdes_count: int = 0


class RiskHintReport(BaseModel):
    """Registry-verified external hints plus rejected/skipped inputs."""

    accepted: list[RiskHint] = Field(default_factory=list)
    rejected: list[RejectedRiskHint] = Field(default_factory=list)
    source_path: str | None = None

    @property
    def accepted_count(self) -> int:
        """Number of hints accepted for user-visible rendering."""

        return len(self.accepted)

    @property
    def rejected_count(self) -> int:
        """Number of hints skipped before user-visible rendering."""

        return len(self.rejected)

    @property
    def total_count(self) -> int:
        """Total input rows considered."""

        return self.accepted_count + self.rejected_count

    @property
    def wrapped_refdes_count(self) -> int:
        """Total unverified refdes-shaped tokens wrapped in text fields."""

        return sum(item.wrapped_refdes_count for item in [*self.accepted, *self.rejected])

    @property
    def counts(self) -> dict[str, int]:
        """Stable count summary for downstream adapters."""

        return {
            "accepted": self.accepted_count,
            "rejected": self.rejected_count,
            "total": self.total_count,
            "wrapped_refdes": self.wrapped_refdes_count,
        }


def load_risk_hint_report(path: Path | str, design: Design) -> RiskHintReport:
    """Load external risk-hints JSON from ``path`` and build a verified report."""

    hint_path = Path(path)
    raw_payload = json.loads(hint_path.read_text(encoding="utf-8"))
    report = build_risk_hint_report(raw_payload, design)
    return report.model_copy(update={"source_path": str(hint_path)})


def build_risk_hint_report(payload: Any, design: Design) -> RiskHintReport:
    """Build a ``RiskHintReport`` from a dict/list JSON payload or model."""

    registry = _registry_from_design(design)
    rows, shape_rejections = _payload_rows(payload, registry)
    accepted: list[RiskHint] = []
    rejected: list[RejectedRiskHint] = list(shape_rejections)
    known_refdes = sorted(design.refdes_set, key=sort_refdes_key)

    for input_index, row in rows:
        title, title_wrapped = sanitize_text(row.title.strip(), registry)
        body, body_wrapped = sanitize_text(row.body.strip(), registry)
        source, source_wrapped = _sanitize_optional(row.source, registry)
        wrapped = title_wrapped + body_wrapped + source_wrapped
        refdes = row.refdes.strip()

        if not refdes:
            rejected.append(
                RejectedRiskHint(
                    input_index=input_index,
                    reason="missing_refdes",
                    title=title,
                    wrapped_refdes_count=wrapped,
                )
            )
            continue
        if refdes not in design.refdes_set:
            rejected.append(
                RejectedRiskHint(
                    input_index=input_index,
                    reason="unknown_refdes",
                    refdes=refdes,
                    title=title,
                    closest_matches=get_close_matches(refdes, known_refdes, n=5, cutoff=0.45),
                    wrapped_refdes_count=wrapped,
                )
            )
            continue
        if not title:
            rejected.append(
                RejectedRiskHint(
                    input_index=input_index,
                    reason="missing_title",
                    refdes=refdes,
                    wrapped_refdes_count=wrapped,
                )
            )
            continue
        if not body:
            rejected.append(
                RejectedRiskHint(
                    input_index=input_index,
                    reason="missing_body",
                    refdes=refdes,
                    title=title,
                    wrapped_refdes_count=wrapped,
                )
            )
            continue

        accepted.append(
            RiskHint(
                input_index=input_index,
                refdes=refdes,
                title=title,
                body=body,
                severity=_clean_optional(row.severity),
                source=source,
                wrapped_refdes_count=wrapped,
            )
        )

    return RiskHintReport(accepted=accepted, rejected=rejected)


def _payload_rows(
    payload: Any,
    registry: BoardRegistry,
) -> tuple[list[tuple[int, RiskHintInput]], list[RejectedRiskHint]]:
    raw_rows = _raw_hint_rows(payload)
    rows: list[tuple[int, RiskHintInput]] = []
    rejected: list[RejectedRiskHint] = []

    for input_index, raw_row in enumerate(raw_rows):
        if not isinstance(raw_row, dict):
            rejected.append(
                RejectedRiskHint(input_index=input_index, reason="invalid_hint_shape")
            )
            continue
        try:
            rows.append((input_index, RiskHintInput.model_validate(raw_row)))
        except ValidationError as exc:
            title = raw_row.get("title", "")
            safe_title, wrapped = sanitize_text(str(title), registry)
            rejected.append(
                RejectedRiskHint(
                    input_index=input_index,
                    reason=f"invalid_hint: {exc.errors()[0]['type']}",
                    refdes=str(raw_row.get("refdes", "")),
                    title=safe_title,
                    wrapped_refdes_count=wrapped,
                )
            )
    return rows, rejected


def _raw_hint_rows(payload: Any) -> list[Any]:
    if isinstance(payload, RiskHintsPayload):
        return [item.model_dump() for item in payload.hints]
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        hints = payload.get("hints")
        if hints is None:
            return [payload]
        if isinstance(hints, list):
            return hints
    raise ValueError("risk-hints JSON must be a hint object, a list, or an object with 'hints'")


def _sanitize_optional(value: str | None, registry: BoardRegistry) -> tuple[str | None, int]:
    cleaned = _clean_optional(value)
    if cleaned is None:
        return None, 0
    return sanitize_text(cleaned, registry)


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _registry_from_design(design: Design) -> BoardRegistry:
    components = [
        ComponentRecord(
            refdes=component.refdes,
            value=" ".join(
                item
                for item in (
                    component.value,
                    component.part_number,
                    component.manufacturer,
                )
                if item
            ),
            footprint=component.package or component.properties.get("Footprint") or "",
            datasheet=component.datasheet_path or "",
            source_file=design.project_path,
            source_kind=design.source_eda,
        )
        for component in design.components.values()
    ]
    return BoardRegistry(project_dir=design.project_path, components=components)
