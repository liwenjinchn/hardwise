"""Datasheet profile JSON model for V2.4."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

from pydantic import BaseModel, Field

ProfileValue = Union[float, str]


class DatasheetProfile(BaseModel):
    """Structured electrical limits extracted from one datasheet."""

    part_number: str
    abs_max: dict[str, ProfileValue] = Field(default_factory=dict)
    recommended: dict[str, ProfileValue] = Field(default_factory=dict)
    pin_function: dict[str, str] = Field(default_factory=dict)
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
        },
        extracted_at=now,
        extracted_model="deterministic-l78-v2.4",
    )
