"""Bind effective field approval to the actual component before formal validation."""

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component

PROFILE_RULE_SUFFIX = ".profile-review1"


def approval_reason(
    component: Component, profile: DatasheetProfile, *, lifecycle=None
) -> str | None:
    lifecycle = lifecycle if lifecycle is not None else profile.lifecycle
    if lifecycle == "RETIRED":
        return "档案已停用（RETIRED），不参与新判定。"
    if lifecycle != "READY":
        return f"档案有效状态 {lifecycle}，缺少适用的逐字段人工批准；旧标签 {profile.review_status} 不构成批准。"
    identity = profile.field_review.identity
    part = component.part_number or component.value
    if part not in identity.part_numbers:
        return "当前器件的精确型号/后缀不在字段批准作用域。"
    if component.package not in identity.packages:
        return "当前器件封装未确认或不在字段批准作用域。"
    if component.manufacturer != identity.manufacturer:
        return "当前器件厂商未确认或不在字段批准作用域。"
    return None


def scope_result(item, reason):
    update = {"rule_version": item.rule_version + PROFILE_RULE_SUFFIX}
    if reason:
        update.update(
            result="UNKNOWN",
            severity="WARNING",
            evidence_kind="HYPOTHESIS",
            needs_review=True,
            summary=(
                item.summary
                if item.summary == reason
                else f"{reason} 候选观察（不构成判定）：{item.summary}"
            ),
        )
    return item.model_copy(update=update)


def approved_tokens(profile):
    if not profile.approved_for_validation:
        return set()
    return {
        *profile.evidence.values(),
        *(token for pin in profile.pins for token in pin.evidence),
        *(relation.evidence for relation in profile.voltage_relations),
    }
