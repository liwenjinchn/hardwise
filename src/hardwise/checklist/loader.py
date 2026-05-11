"""Load Hardwise checklist rule specs from `data/checklists/sch_review.yaml`.

`load_rules(path)` returns only `status == "active"` rules — `planned` /
`candidate` / `deprecated` rules stay in the yaml as documentation but are
not handed to the agent / check runner.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from hardwise.checklist.finding import Severity

RuleStatus = Literal["active", "planned", "candidate", "deprecated"]


class RuleSpec(BaseModel):
    """One rule loaded from sch_review.yaml."""

    id: str
    title: str
    source: str
    status: RuleStatus
    severity: Severity
    required_evidence: list[str] = Field(default_factory=list)
    check_function: str
    rule: str
    slice: int


def load_rules(yaml_path: Path) -> list[RuleSpec]:
    """Parse a checklist yaml file and return only active rules."""

    if not yaml_path.exists():
        raise FileNotFoundError(f"checklist yaml not found: {yaml_path}")

    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"checklist yaml at {yaml_path} must be a top-level list of rule blocks")

    rules = [RuleSpec.model_validate(item) for item in raw]
    return [r for r in rules if r.status == "active"]
