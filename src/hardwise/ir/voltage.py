"""Explicit voltage facts; net names and legacy hints are never confirmations."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator, model_validator


class VoltageFact(BaseModel):
    """One user-supplied DC envelope relative to an identified reference net."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    net: str = Field(min_length=1)
    reference_net: str = Field(min_length=1)
    mode: str = Field(default="dc", min_length=1)
    unit: Literal["V"] = "V"
    minimum: FiniteFloat | None = None
    typical: FiniteFloat | None = None
    maximum: FiniteFloat | None = None
    source: str = Field(min_length=1)
    confirmed: bool = False
    confirmed_by: str = ""

    @field_validator("net", "reference_net", "mode", "source", "confirmed_by")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def coherent_envelope(self) -> VoltageFact:
        if not all((self.net, self.reference_net, self.mode, self.source)):
            raise ValueError("net, reference_net, mode and source must be nonempty")
        if self.confirmed and not self.confirmed_by:
            raise ValueError("confirmed facts require a confirmed_by name")
        if self.minimum is not None and self.maximum is not None:
            if self.minimum > self.maximum:
                raise ValueError("minimum must not exceed maximum")
        if self.typical is not None:
            if self.minimum is not None and self.typical < self.minimum:
                raise ValueError("typical is below minimum")
            if self.maximum is not None and self.typical > self.maximum:
                raise ValueError("typical is above maximum")
        if self.net == self.reference_net:
            if any(
                value != 0
                for value in (self.minimum, self.typical, self.maximum)
                if value is not None
            ):
                raise ValueError("a reference net cannot have nonzero voltage relative to itself")
        return self


class VoltageFactsDocument(BaseModel):
    """Portable project input, validated atomically before replacing active state."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["hardwise.voltage_facts.v1"] = "hardwise.voltage_facts.v1"
    active_mode: str = Field(default="dc", min_length=1)
    facts: list[VoltageFact] = Field(default_factory=list)

    @model_validator(mode="after")
    def reject_conflicts(self) -> VoltageFactsDocument:
        keys = [(fact.net, fact.mode) for fact in self.facts]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate or conflicting voltage facts for the same net and mode")
        if not self.active_mode.strip():
            raise ValueError("active_mode must be nonempty")
        return self
