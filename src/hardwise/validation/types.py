"""Shared validation result models."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, get_args

from pydantic import BaseModel, Field, computed_field

PinValidationStatus = Literal["PASS", "WARN", "ERROR", "UNKNOWN", "NOT_APPLICABLE"]
VALIDATION_STATUSES: tuple[PinValidationStatus, ...] = get_args(PinValidationStatus)


def status_counts(statuses: Iterable[PinValidationStatus]) -> dict[PinValidationStatus, int]:
    """Count every wire status, including unassessed and inapplicable checks."""
    counts: dict[PinValidationStatus, int] = dict.fromkeys(VALIDATION_STATUSES, 0)
    for status in statuses:
        counts[status] += 1
    return counts


class PinValidation(BaseModel):
    """Validation outcome for one profiled pin."""

    pin_number: str
    pin_name: str
    category: str
    status: PinValidationStatus
    summary: str
    net: str | None = None
    evidence: list[str] = Field(default_factory=list)


class ComponentValidation(BaseModel):
    """Validation outcome for one component-level topology/peripheral check."""

    check: str
    status: PinValidationStatus
    summary: str
    evidence: list[str] = Field(default_factory=list)
    refdes: str | None = None


class ValidationReport(BaseModel):
    """Single-component validation report."""

    refdes: str
    component_value: str
    part_number: str | None = None
    profile_part_number: str
    pin_results: list[PinValidation] = Field(default_factory=list)
    component_checks: list[ComponentValidation] = Field(default_factory=list)

    @computed_field
    @property
    def status(self) -> PinValidationStatus:
        """Roll up pin and component-level status to component status."""

        statuses = [
            *[pin.status for pin in self.pin_results],
            *[check.status for check in self.component_checks],
        ]
        if "ERROR" in statuses:
            return "ERROR"
        if "WARN" in statuses:
            return "WARN"
        if not statuses or "UNKNOWN" in statuses:
            return "UNKNOWN"
        if "PASS" in statuses:
            return "PASS"
        return "NOT_APPLICABLE"

    @computed_field
    @property
    def counts_by_status(self) -> dict[PinValidationStatus, int]:
        """Return pin-result counts for all known statuses."""

        return status_counts(pin.status for pin in self.pin_results)

    @computed_field
    @property
    def component_counts_by_status(self) -> dict[PinValidationStatus, int]:
        """Return component-check counts for all known statuses."""

        return status_counts(check.status for check in self.component_checks)
