"""Unresolved BOM identities cannot authorize electrical or topology conclusions."""

from hardwise.bom.conflicts import CONFLICT_PROPERTY
from hardwise.ir.types import Component, Design
from hardwise.validation.types import ComponentValidation, ValidationReport


def identity_conflict_report(component: Component) -> ValidationReport | None:
    reason = component.properties.get(CONFLICT_PROPERTY)
    if not reason:
        return None
    return ValidationReport(
        refdes=component.refdes,
        component_value=component.value,
        part_number=None,
        profile_part_number="",
        component_checks=[
            ComponentValidation(
                check="bom_identity_conflict",
                refdes=component.refdes,
                result="UNKNOWN",
                severity="WARNING",
                evidence_kind="SOURCE_FACT",
                needs_review=True,
                summary=reason,
                evidence=[f"rule:bom_identity_conflict#{component.refdes}"],
            )
        ],
    )


def scope_topology_identities(checks: list[ComponentValidation], design: Design):
    """Conservative project scope until each topology rule declares dependencies."""
    blocked = sorted(
        c.refdes for c in design.components.values() if c.properties.get(CONFLICT_PROPERTY)
    )
    if not blocked:
        return checks
    return [
        check.model_copy(
            update={
                "result": "UNKNOWN",
                "needs_review": True,
                "evidence_kind": "HYPOTHESIS",
                "rule_version": f"{check.rule_version}.bom-scope1",
                "summary": f"项目存在未解决的 BOM 身份冲突（{', '.join(blocked)}）；当前规则未声明精确依赖，暂按项目范围暂停拓扑结论。原始观察（不构成判定）：{check.summary}",
            }
        )
        for check in checks
    ]
