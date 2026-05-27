"""Shared validation result models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PinValidationStatus = Literal["PASS", "WARN", "ERROR"]


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
        return "PASS"

    @property
    def counts_by_status(self) -> dict[PinValidationStatus, int]:
        """Return pin-result counts for all known statuses."""

        return {
            "PASS": sum(pin.status == "PASS" for pin in self.pin_results),
            "WARN": sum(pin.status == "WARN" for pin in self.pin_results),
            "ERROR": sum(pin.status == "ERROR" for pin in self.pin_results),
        }

    @property
    def component_counts_by_status(self) -> dict[PinValidationStatus, int]:
        """Return component-check counts for all known statuses."""

        return {
            "PASS": sum(check.status == "PASS" for check in self.component_checks),
            "WARN": sum(check.status == "WARN" for check in self.component_checks),
            "ERROR": sum(check.status == "ERROR" for check in self.component_checks),
        }
