"""Deterministic source comparison. No validators, profiles, AI calls or review state."""

from collections import Counter
import hashlib
import json
from pathlib import Path

from hardwise.bom.types import sort_refdes_key
from hardwise.revision.connections import ConnectionIndex
from hardwise.revision.intake import load_revision
from hardwise.revision.models import (
    ComparisonIssue,
    ComparisonResult,
    ComparisonSummary,
    Observation,
    RevisionChange,
    RevisionSnapshot,
)


def _hash(value) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def _semantic(observation):
    return None if observation is None else (observation.state, observation.values)


def _component_observation(component):
    values = tuple(
        f"{field} = {' / '.join(item.values) if item.values else '未声明'}"
        for field, item in sorted(component.attributes.items())
    )
    return Observation(
        values=values,
        evidence=component.evidence
        + tuple(evidence for item in component.attributes.values() for evidence in item.evidence),
    )


def compare_revisions(before: RevisionSnapshot, after: RevisionSnapshot) -> ComparisonResult:
    """Compare exact refdes and declared net memberships; do not infer design intent."""
    if before.input_format != after.input_format:
        raise ValueError("两版必须使用相同的网表格式；不跨 Telesis/PST 猜测字段对应。")
    left, right = ConnectionIndex(before), ConnectionIndex(after)
    old_refs, new_refs = set(before.components), set(after.components)
    added, removed = new_refs - old_refs, old_refs - new_refs
    common = old_refs & new_refs
    changes, issues = [], list(before.issues + after.issues)
    changed_refs: set[str] = set()

    def emit(kind, ref, field, old, new, explanation, pin=None):
        related = left.neighbors(ref) | right.neighbors(ref)
        changes.append(
            RevisionChange(
                id=_hash((kind, ref, pin, field, _semantic(old), _semantic(new)))[:24],
                kind=kind,
                refdes=ref,
                pin=pin,
                field=field,
                before=old,
                after=new,
                explanation=explanation,
                related_refdes=tuple(sorted(related, key=sort_refdes_key)[:50]),
                related_count=len(related),
            )
        )
        changed_refs.add(ref)

    for ref in sorted(removed, key=sort_refdes_key):
        emit(
            "component_removed",
            ref,
            "component",
            _component_observation(before.components[ref]),
            None,
            "该位号不再出现在新版网表中；可能是移除或重编号，未自动识别物理器件延续。",
        )
    for ref in sorted(added, key=sort_refdes_key):
        emit(
            "component_added",
            ref,
            "component",
            None,
            _component_observation(after.components[ref]),
            "该位号新出现在新版网表中；可能是新增或重编号，未自动识别物理器件延续。",
        )
    if added and removed:
        issues.append(
            ComparisonIssue(
                side="both",
                code="identity_mapping_unverified",
                explanation="两版同时存在位号增删；首版不猜测重编号对应关系，请确认是否为同一设计修订。",
            )
        )
    if not common:
        issues.append(
            ComparisonIssue(
                side="both",
                code="no_common_refdes",
                explanation="两版没有共同位号，不能确认版本对应关系；仅列出各自的位号声明，不认定全部器件换新。",
            )
        )

    renamed = set()
    for ref in sorted(common, key=sort_refdes_key):
        old_component, new_component = before.components[ref], after.components[ref]
        keys = set(old_component.attributes) | set(new_component.attributes)
        for field in sorted(keys):
            if field.startswith("bom.") and (
                old_component.identity_ambiguous or new_component.identity_ambiguous
            ):
                continue
            old = old_component.attributes.get(
                field, Observation(state="missing", evidence=old_component.evidence)
            )
            new = new_component.attributes.get(
                field, Observation(state="missing", evidence=new_component.evidence)
            )
            if "ambiguous" in {old.state, new.state} or _semantic(old) == _semantic(new):
                continue
            emit(
                "attribute_changed",
                ref,
                field,
                old,
                new,
                "源字段声明发生变化；仅做去除首尾空白后的文本比较，不判断电气等价或替代兼容性。",
            )
        pins = set(before.pin_networks.get(ref, {})) | set(after.pin_networks.get(ref, {}))
        for pin in sorted(pins):
            old, old_signature = left.observation(ref, pin)
            new, new_signature = right.observation(ref, pin)
            if "ambiguous" in {old.state, new.state}:
                continue
            if old_signature == new_signature:
                if old.values != new.values and (old.values, new.values) not in renamed:
                    renamed.add((old.values, new.values))
                    emit(
                        "net_renamed",
                        ref,
                        "net.name",
                        old,
                        new,
                        "网络名称改变，但导出端点集合完全相同；该网络仅列一次，不认定为重新接线。",
                        pin,
                    )
                    changed_refs.update(p.refdes for p in left.networks[old.values[0]].endpoints)
                continue
            emit(
                "connection_changed",
                ref,
                "pin.connection",
                old,
                new,
                "该引脚所属网络的端点集合变化；即使网络名相同也记录。未声明不等于开路，详见前后网络端点。",
                pin,
            )
            if "missing" in {old.state, new.state}:
                issues.append(
                    ComparisonIssue(
                        side="before" if old.state == "missing" else "after",
                        code="pin_declaration_missing",
                        refdes=ref,
                        explanation=f"{ref}.{pin} 在一版没有连接声明，不能据此认定为明确的未连接引脚。",
                        evidence=old.evidence + new.evidence,
                    )
                )

    affected_unknown = {issue.refdes for issue in issues if issue.refdes is not None}
    affected_unknown |= left.ambiguous_refdes() | right.ambiguous_refdes()
    counts = Counter(change.kind for change in changes)
    summary = ComparisonSummary(
        added=len(added),
        removed=len(removed),
        attribute_changes=counts["attribute_changed"],
        connection_changes=counts["connection_changed"],
        net_renames=counts["net_renamed"],
        changed_components=len(changed_refs),
        unresolved=len(issues),
        unchanged_components=len(common - changed_refs - affected_unknown),
    )
    # File digests bind the run; change IDs deliberately ignore source ordering and paths.
    comparison_id = _hash(
        [
            [(source.role, source.sha256) for source in snapshot.view.sources]
            for snapshot in (before, after)
        ]
    )
    return ComparisonResult(
        comparison_id=comparison_id,
        input_format=before.input_format,
        status="needs_review" if issues else "differences" if changes else "no_observed_difference",
        before=before.view,
        after=after.view,
        summary=summary,
        changes=tuple(changes),
        issues=tuple(issues),
    )


def compare_files(
    before_netlist: Path,
    before_bom: Path,
    after_netlist: Path,
    after_bom: Path,
) -> ComparisonResult:
    return compare_revisions(
        load_revision(Path(before_netlist), Path(before_bom), side="before"),
        load_revision(Path(after_netlist), Path(after_bom), side="after"),
    )
