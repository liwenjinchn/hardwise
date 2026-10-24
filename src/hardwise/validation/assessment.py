"""Independent result, severity and evidence axes for deterministic checks."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field, model_validator

CheckResult = Literal["PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"]
Severity = Literal["ERROR", "WARNING", "INFO"]
EvidenceKind = Literal["SOURCE_FACT", "DERIVED", "HYPOTHESIS"]
AttentionStatus = Literal["PASS", "WARN", "ERROR", "UNKNOWN", "NOT_APPLICABLE"]
CHECK_RESULTS: tuple[CheckResult, ...] = ("PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE")


def result_for_attention(status: AttentionStatus, *, warning_result: CheckResult) -> CheckResult:
    """Current rule adapters must state what their WARN branch actually means."""
    return {
        "PASS": "PASS",
        "ERROR": "FAIL",
        "WARN": warning_result,
        "UNKNOWN": "UNKNOWN",
        "NOT_APPLICABLE": "NOT_APPLICABLE",
    }[status]


def severity_for_attention(status: AttentionStatus) -> Severity:
    return {"ERROR": "ERROR", "WARN": "WARNING"}.get(status, "INFO")


def attention_status(result: CheckResult, severity: Severity) -> AttentionStatus:
    if result == "FAIL":
        return "ERROR" if severity == "ERROR" else "WARN"
    return result


class Assessment(BaseModel):
    """Canonical check contract; old status-only records cannot certify a result."""

    contract_version: Literal["hardwise.assessment.v1"] = "hardwise.assessment.v1"
    result: CheckResult = "UNKNOWN"
    severity: Severity = "INFO"
    evidence_kind: EvidenceKind = "DERIVED"
    rule_version: str = Field(default="1", min_length=1)
    needs_review: bool = False
    migration_state: Literal["current", "legacy_needs_review"] = "current"
    legacy_status: AttentionStatus | None = None
    not_applicable_reason: str | None = None

    @model_validator(mode="before")
    @classmethod
    def load_legacy_record(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        values = dict(data)
        status = values.pop("status", None)
        if "result" not in values:
            # A replay of original inputs is needed; do not guess the meaning of WARN.
            values.update(
                result="UNKNOWN",
                needs_review=True,
                evidence_kind="HYPOTHESIS",
                migration_state="legacy_needs_review",
            )
            if status is not None:
                values["legacy_status"] = status
                values.setdefault("severity", severity_for_attention(status))
        elif status is not None and status != attention_status(
            values["result"], values.get("severity", "INFO")
        ):
            raise ValueError("status disagrees with canonical result/severity")
        return values

    @model_validator(mode="after")
    def validate_scope(self) -> Assessment:
        if self.migration_state == "legacy_needs_review" and (
            self.result != "UNKNOWN" or not self.needs_review
        ):
            raise ValueError("legacy assessments must remain unknown and require review")
        if self.result == "NOT_APPLICABLE" and not (self.not_applicable_reason or "").strip():
            raise ValueError("NOT_APPLICABLE requires a reason")
        if self.evidence_kind == "HYPOTHESIS" and self.result in {"PASS", "FAIL"}:
            raise ValueError("hypotheses cannot certify PASS or FAIL")
        if self.needs_review and self.result == "PASS":
            raise ValueError("an assessment needing review cannot certify PASS")
        return self

    @computed_field
    @property
    def status(self) -> AttentionStatus:
        """Legacy attention alias; use result/severity for new decisions."""
        return attention_status(self.result, self.severity)


class CheckCoverage(BaseModel):
    """An explicit emitted-record denominator, not claimed whole-design coverage."""

    rule_set_version: str = "hardwise.assessment.v1"
    basis: Literal["emitted_check_records"] = "emitted_check_records"
    generated_checks: int
    completed_checks: int
    unknown_checks: int
    not_applicable_checks: int
    legacy_needs_review: int
    needs_review_checks: int
    result_counts: dict[CheckResult, int]
    unsupported_components: int = 0
    full_candidate_count: int | None = None
    boundary: str = "只统计已生成的检查记录；尚未建立全板候选检查集合，不代表全板覆盖率。"


def check_coverage(checks: list[Assessment], unsupported_components: int = 0) -> CheckCoverage:
    counts = dict.fromkeys(CHECK_RESULTS, 0)
    for item in checks:
        counts[item.result] += 1
    return CheckCoverage(
        generated_checks=len(checks),
        completed_checks=counts["PASS"] + counts["FAIL"],
        unknown_checks=counts["UNKNOWN"],
        not_applicable_checks=counts["NOT_APPLICABLE"],
        legacy_needs_review=sum(item.migration_state == "legacy_needs_review" for item in checks),
        needs_review_checks=sum(item.needs_review for item in checks),
        result_counts=counts,
        unsupported_components=unsupported_components,
    )
