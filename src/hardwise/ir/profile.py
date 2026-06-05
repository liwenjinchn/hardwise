"""Datasheet profile JSON model for V2.4."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Union

from pydantic import BaseModel, Field

ProfileValue = Union[bool, float, str]


class PinProfile(BaseModel):
    """Structured datasheet facts for one package pin."""

    number: str
    name: str
    schematic_pin_aliases: list[str] = Field(default_factory=list)
    category: str
    function: str
    limits: dict[str, ProfileValue] = Field(default_factory=dict)
    recommended_topology: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class DatasheetProfile(BaseModel):
    """Structured electrical limits extracted from one datasheet."""

    part_number: str
    part_number_aliases: list[str] = Field(default_factory=list)
    review_status: Literal["ready", "needs_review"] = "ready"
    abs_max: dict[str, ProfileValue] = Field(default_factory=dict)
    recommended: dict[str, ProfileValue] = Field(default_factory=dict)
    pin_function: dict[str, str] = Field(default_factory=dict)
    pins: list[PinProfile] = Field(default_factory=list)
    evidence: dict[str, str] = Field(default_factory=dict)
    extracted_at: str
    extracted_model: str
    schema_version: str = "v1"

    @classmethod
    def load(cls, path: Path) -> "DatasheetProfile":
        """Load and validate a profile JSON file."""

        return cls.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, path: Path) -> None:
        """Write profile JSON with stable formatting."""

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def pin_by_number(self, number: str) -> PinProfile | None:
        """Return structured pin facts for a pin number, if present."""

        return next((pin for pin in self.pins if pin.number == number), None)


def extract_l78_profile(pdf_path: Path) -> DatasheetProfile:
    """Return the deterministic V2.4 profile for ST's public L78 datasheet.

    The extraction is intentionally narrow and reproducible: V2.4 proves the
    profile path and DS001 check without relying on a live LLM. The source PDF
    is still validated by filename so callers cannot accidentally label another
    datasheet as L78.
    """

    if pdf_path.name.lower() != "l78.pdf":
        raise ValueError("V2.4 deterministic profile extraction only supports l78.pdf")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return DatasheetProfile(
        part_number="L7805",
        abs_max={
            "vin": 35.0,
            "iout": "internally limited",
            "power_dissipation": "internally limited",
            "tj": 125.0,
        },
        recommended={
            "vin_min": 7.5,
            "vin_max": 25.0,
            "iout_max": 1.5,
        },
        pin_function={
            "1": "VI (input)",
            "2": "GND (ground)",
            "3": "VO (5 V output)",
        },
        pins=[
            PinProfile(
                number="1",
                name="VI",
                category="power_input",
                function="Voltage input for the linear regulator.",
                limits={
                    "abs_max_voltage": 35.0,
                    "recommended_voltage_min": 7.5,
                    "recommended_voltage_max": 25.0,
                },
                recommended_topology=[
                    "Connect to the unregulated input rail.",
                    "Place the input bypass capacitor close to VI and GND.",
                ],
                evidence=[
                    "datasheet:l78.pdf#p3",
                    "datasheet:l78.pdf#p4",
                    "datasheet:l78.pdf#p6",
                ],
            ),
            PinProfile(
                number="2",
                name="GND",
                category="ground",
                function="Ground reference for input and output regulation.",
                recommended_topology=[
                    "Connect directly to the system ground return.",
                    "Share the local return path with input and output bypass capacitors.",
                ],
                evidence=["datasheet:l78.pdf#p3"],
            ),
            PinProfile(
                number="3",
                name="VO",
                category="power_output",
                function="Regulated 5 V output.",
                limits={"nominal_voltage": 5.0, "recommended_current_max": 1.5},
                recommended_topology=[
                    "Connect to the regulated 5 V rail.",
                    "Place the output bypass capacitor close to VO and GND.",
                ],
                evidence=[
                    "datasheet:l78.pdf#p3",
                    "datasheet:l78.pdf#p6",
                ],
            ),
        ],
        evidence={
            "abs_max.vin": "datasheet:l78.pdf#p4",
            "abs_max.iout": "datasheet:l78.pdf#p4",
            "abs_max.power_dissipation": "datasheet:l78.pdf#p4",
            "abs_max.tj": "datasheet:l78.pdf#p4",
            "recommended.vin_min": "datasheet:l78.pdf#p6",
            "recommended.vin_max": "datasheet:l78.pdf#p6",
            "recommended.iout_max": "datasheet:l78.pdf#p6",
            "pin_function.1": "datasheet:l78.pdf#p3",
            "pin_function.2": "datasheet:l78.pdf#p3",
            "pin_function.3": "datasheet:l78.pdf#p3",
            "pins.1": "datasheet:l78.pdf#p3",
            "pins.2": "datasheet:l78.pdf#p3",
            "pins.3": "datasheet:l78.pdf#p3",
        },
        extracted_at=now,
        extracted_model="deterministic-l78-v3.0",
        schema_version="v2",
    )
