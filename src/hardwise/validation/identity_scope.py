"""Unresolved BOM identities cannot authorize electrical or topology conclusions."""

from hardwise.bom.conflicts import CONFLICT_PROPERTY
from hardwise.ir.types import Component, Design
from hardwise.ir.identity_sources import netlist_mpn_sources
from hardwise.ir.profile import DatasheetProfile
from hardwise.validation.types import ComponentValidation, ValidationReport


def _identity_conflict_reason(component: Component) -> str | None:
    reason = component.properties.get(CONFLICT_PROPERTY)
    if reason:
        return reason
    records = netlist_mpn_sources(component)
    if len({record["value"].strip().casefold() for record in records}) > 1:
        return (
            f"{component.refdes} 的网表明确 MPN 声明互相不一致，身份未确认；停止相关检查。"
            + "; ".join(
                f"{record['source']} [{record['field']}={record['value']}]" for record in records
            )
        )
    return None


def identity_conflict_report(component: Component) -> ValidationReport | None:
    reason = _identity_conflict_reason(component)
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
                rule_version="2",
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
    blocked = sorted(c.refdes for c in design.components.values() if _identity_conflict_reason(c))
    if not blocked:
        return checks
    return [
        check.model_copy(
            update={
                "result": "UNKNOWN",
                "needs_review": True,
                "evidence_kind": "HYPOTHESIS",
                "rule_version": f"{check.rule_version}.bom-scope2",
                "summary": f"项目存在未解决的身份冲突（来自 BOM 或网表）（{', '.join(blocked)}）；当前规则未声明精确依赖，暂按项目范围暂停拓扑结论。原始观察（不构成判定）：{check.summary}",
            }
        )
        for check in checks
    ]


def profile_identity_conflict_report(
    component: Component, profile: DatasheetProfile
) -> ValidationReport | None:
    records = netlist_mpn_sources(component)
    identities = {
        value.strip().casefold() for value in [profile.part_number, *profile.part_number_aliases]
    }
    if not any(record["value"].strip().casefold() not in identities for record in records):
        return None
    reason = (
        f"{component.refdes} 的网表明确 MPN 声明与档案 {profile.part_number} 及其声明别名不一致；"
        "身份未确认，不执行引脚或数值规则。原始声明："
        + "; ".join(f"{r['source']} [{r['field']}={r['value']}]" for r in records)
    )
    blocked = component.model_copy(
        update={"properties": {**component.properties, CONFLICT_PROPERTY: reason}}
    )
    report = identity_conflict_report(blocked)
    assert report is not None
    report.component_checks[0].check = "profile_identity_conflict"
    report.component_checks[0].evidence = [f"rule:profile_identity_conflict#{component.refdes}"]
    return report
