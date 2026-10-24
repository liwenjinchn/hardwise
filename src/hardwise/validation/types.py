"""Shared validation result models."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, get_args

from pydantic import BaseModel, Field, computed_field

from hardwise.validation.assessment import Assessment, CHECK_RESULTS, CheckResult, Severity

PinValidationStatus = Literal["PASS", "WARN", "ERROR", "UNKNOWN", "NOT_APPLICABLE"]
VALIDATION_STATUSES: tuple[PinValidationStatus, ...] = get_args(PinValidationStatus)


def status_counts(statuses: Iterable[PinValidationStatus]) -> dict[PinValidationStatus, int]:
    """Count every wire status, including unassessed and inapplicable checks."""
    counts: dict[PinValidationStatus, int] = dict.fromkeys(VALIDATION_STATUSES, 0)
    for status in statuses:
        counts[status] += 1
    return counts


class PinValidation(Assessment):
    """Validation outcome for one profiled pin."""

    pin_number: str
    pin_name: str
    category: str
    summary: str
    net: str | None = None
    evidence: list[str] = Field(default_factory=list)


class ComponentValidation(Assessment):
    """Validation outcome for one component-level topology/peripheral check."""

    check: str
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

    @property
    def assessment(self) -> Assessment:
        return Assessment(
            result=self.result,
            severity=self.severity,
            needs_review=self.needs_review,
            evidence_kind="HYPOTHESIS" if self.needs_review else "DERIVED",
            not_applicable_reason="All emitted checks are inapplicable"
            if self.result == "NOT_APPLICABLE"
            else None,
        )

    @computed_field
    @property
    def result(self) -> CheckResult:
        results = [item.result for item in [*self.pin_results, *self.component_checks]]
        if "FAIL" in results:
            return "FAIL"
        if not results or "UNKNOWN" in results:
            return "UNKNOWN"
        return "PASS" if "PASS" in results else "NOT_APPLICABLE"

    @computed_field
    @property
    def severity(self) -> Severity:
        checks = [*self.pin_results, *self.component_checks]
        failures = [item for item in checks if item.result == "FAIL"]
        severities = [item.severity for item in (failures or checks)]
        return max(severities, key={"INFO": 0, "WARNING": 1, "ERROR": 2}.get, default="INFO")

    @computed_field
    @property
    def needs_review(self) -> bool:
        return any(item.needs_review for item in [*self.pin_results, *self.component_checks])

    @computed_field
    @property
    def result_counts(self) -> dict[CheckResult, int]:
        counts = dict.fromkeys(CHECK_RESULTS, 0)
        for item in [*self.pin_results, *self.component_checks]:
            counts[item.result] += 1
        return counts

    @computed_field
    @property
    def status(self) -> PinValidationStatus:
        """Roll up pin and component-level status to component status."""

        from hardwise.validation.assessment import attention_status

        return attention_status(self.result, self.severity)

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
