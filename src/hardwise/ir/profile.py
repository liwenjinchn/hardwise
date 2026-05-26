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
            "vout_nominal": 5.0,
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
            "recommended.vout_nominal": "datasheet:l78.pdf#p6",
            "recommended.iout_max": "datasheet:l78.pdf#p6",
            "pin_function.1": "datasheet:l78.pdf#p3",
            "pin_function.2": "datasheet:l78.pdf#p3",
            "pin_function.3": "datasheet:l78.pdf#p3",
        },
        extracted_at=now,
        extracted_model="deterministic-l78-v2.4",
    )


def extract_pca9548a_profile(pdf_path: Path) -> DatasheetProfile:
    """Return the deterministic V3.0 profile for NXP's public PCA9548A datasheet."""

    if pdf_path.name.lower() != "pca9548a.pdf":
        raise ValueError("V3.0 deterministic profile extraction only supports pca9548a.pdf")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return DatasheetProfile(
        part_number="PCA9548A",
        recommended={
            "vdd_min": 2.3,
            "vdd_max": 5.5,
        },
        pin_function={
            "1": "A0 (address input 0)",
            "2": "A1 (address input 1)",
            "3": "RESET (active-low reset input)",
            "4": "SD0 (downstream channel 0 serial data)",
            "5": "SC0 (downstream channel 0 serial clock)",
            "6": "SD1 (downstream channel 1 serial data)",
            "7": "SC1 (downstream channel 1 serial clock)",
            "8": "SD2 (downstream channel 2 serial data)",
            "9": "SC2 (downstream channel 2 serial clock)",
            "10": "SD3 (downstream channel 3 serial data)",
            "11": "SC3 (downstream channel 3 serial clock)",
            "12": "VSS (ground)",
            "13": "SD4 (downstream channel 4 serial data)",
            "14": "SC4 (downstream channel 4 serial clock)",
            "15": "SD5 (downstream channel 5 serial data)",
            "16": "SC5 (downstream channel 5 serial clock)",
            "17": "SD6 (downstream channel 6 serial data)",
            "18": "SC6 (downstream channel 6 serial clock)",
            "19": "SD7 (downstream channel 7 serial data)",
            "20": "SC7 (downstream channel 7 serial clock)",
            "21": "A2 (address input 2)",
            "22": "SCL (upstream serial clock input)",
            "23": "SDA (upstream serial data input/output)",
            "24": "VDD (supply voltage)",
        },
        evidence={
            "recommended.vdd_min": "datasheet:pca9548a.pdf#p15",
            "recommended.vdd_max": "datasheet:pca9548a.pdf#p15",
            **{
                f"pin_function.{pin}": "datasheet:pca9548a.pdf#p4"
                for pin in range(1, 25)
            },
        },
        extracted_at=now,
        extracted_model="deterministic-pca9548a-v3.0",
    )
