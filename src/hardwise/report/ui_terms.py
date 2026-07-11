"""User-facing Chinese labels for validator UI terms.

This compatibility facade keeps the original import surface stable.
"""

from __future__ import annotations

from hardwise.report.ui_term_data import (
    STATUS_LABELS,
    IDENTITY_KIND_LABELS,
    FAMILY_LABELS,
    GENERIC_PASSIVE_TERM_LABELS,
    PROFILE_PART_LABELS,
    PIN_CATEGORY_LABELS,
    CHECK_LABELS,
    PROFILE_GROUP_LABELS,
    PROFILE_FACT_LABELS,
    LIMIT_LABELS,
    PROFILE_VALUE_LABELS,
    REVIEW_STATUS_LABELS,
    REASON_LABELS,
    VALIDATION_SUMMARY_LABELS,
    RECOMMENDED_TOPOLOGY_LABELS,
)
from hardwise.report.ui_term_validation import (
    _CLAUSE_LABELS,
    _VALIDATION_PATTERNS,
    _replace_known_clauses,
    validation_summary_label,
)

__all__ = [
    "_CLAUSE_LABELS",
    "_VALIDATION_PATTERNS",
    "_replace_known_clauses",
    "CHECK_LABELS",
    "FAMILY_LABELS",
    "GENERIC_PASSIVE_TERM_LABELS",
    "IDENTITY_KIND_LABELS",
    "LIMIT_LABELS",
    "PIN_CATEGORY_LABELS",
    "PROFILE_FACT_LABELS",
    "PROFILE_GROUP_LABELS",
    "PROFILE_PART_LABELS",
    "PROFILE_VALUE_LABELS",
    "REASON_LABELS",
    "RECOMMENDED_TOPOLOGY_LABELS",
    "REVIEW_STATUS_LABELS",
    "STATUS_LABELS",
    "VALIDATION_SUMMARY_LABELS",
    "check_label",
    "extraction_model_label",
    "family_label",
    "identity_kind_label",
    "limit_label",
    "pin_category_label",
    "profile_claim_label",
    "profile_fact_label",
    "profile_group_label",
    "profile_part_label",
    "profile_value_label",
    "reason_label",
    "recommended_topology_label",
    "review_status_label",
    "status_label",
    "validation_summary_label",
]


def status_label(status: str) -> str:
    """Return a user-facing label for coverage/document status strings."""

    return STATUS_LABELS.get(status, status)


def identity_kind_label(kind: str) -> str:
    """Return a user-facing label for normalized BOM identity kinds."""

    return IDENTITY_KIND_LABELS.get(kind, kind)


def family_label(family: str) -> str:
    """Return a user-facing label for suggested component families."""

    return FAMILY_LABELS.get(family, family)


def profile_part_label(part_number: str) -> str:
    """Return a readable label for synthetic and real profile identities."""

    return PROFILE_PART_LABELS.get(part_number, part_number)


def pin_category_label(category: str) -> str:
    """Return a readable label for profile pin categories."""

    return PIN_CATEGORY_LABELS.get(category, category)


def check_label(check: str) -> str:
    """Return a readable label for deterministic component check names."""

    return CHECK_LABELS.get(check, check)


def profile_group_label(group: str) -> str:
    """Return a readable label for profile fact groups."""

    return PROFILE_GROUP_LABELS.get(group, group)


def profile_fact_label(group: str, key: str) -> str:
    """Return a readable label for structured profile fact keys."""

    claim_key = f"{group}.{key}" if group else key
    return PROFILE_FACT_LABELS.get(claim_key, key)


def profile_claim_label(claim_key: str) -> str:
    """Return a readable label for evidence-ledger claim keys."""

    if claim_key in PROFILE_FACT_LABELS:
        return PROFILE_FACT_LABELS[claim_key]
    if claim_key.startswith("pins."):
        return f"引脚 {claim_key.split('.', 1)[1]}"
    if claim_key.startswith("pin_function."):
        return f"引脚 {claim_key.split('.', 1)[1]} 功能"
    if "." in claim_key:
        group, _, key = claim_key.partition(".")
        fact = profile_fact_label(group, key)
        if fact != key:
            return fact
    return claim_key


def limit_label(key: str) -> str:
    """Return a readable label for per-pin limit keys."""

    return LIMIT_LABELS.get(key, key)


def profile_value_label(value: object) -> str:
    """Return a readable value label without changing the underlying fact."""

    if isinstance(value, bool):
        return "是" if value else "否"
    text = str(value)
    return PROFILE_VALUE_LABELS.get(text, text)


def review_status_label(status: str) -> str:
    """Return a readable label for profile review status strings."""

    return REVIEW_STATUS_LABELS.get(status, status)


def extraction_model_label(model: str) -> str:
    """Return a readable label for profile extraction metadata."""

    if model.startswith("deterministic-"):
        return "确定性结构化抽取"
    if model.startswith("manual-"):
        return "人工结构化档案"
    if model.startswith("claude-"):
        return "模型辅助结构化抽取"
    return model


def reason_label(reason: str) -> str:
    """Return a localized reason while preserving unknown diagnostic text."""

    return REASON_LABELS.get(reason, reason)


def recommended_topology_label(text: str) -> str:
    """Return Chinese display text for common profile topology notes."""

    return RECOMMENDED_TOPOLOGY_LABELS.get(text, text)
