"""Condition-bearing public datasheet relationships, never flattened constants."""

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat


class PinVoltageRelation(BaseModel):
    """Target pin range relative to ground, with an upper bound at another pin."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    required_package: str = Field(min_length=1)
    target_pin: str = Field(min_length=1)
    supply_pin: str = Field(min_length=1)
    ground_pin: str = Field(min_length=1)
    minimum_voltage: FiniteFloat
    evidence: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    document_revision: str = Field(min_length=1)
    document_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    page: int = Field(ge=1)
