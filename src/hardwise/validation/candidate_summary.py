"""A display projection of a persisted candidate snapshot, never a new denominator."""

from typing import Literal

from pydantic import BaseModel, NonNegativeInt
from hardwise.validation.candidate_coverage import CandidateSnapshot
from hardwise.validation.assessment import CheckResult


class CandidateCounts(BaseModel):
    candidate_count: NonNegativeInt
    applicable_count: NonNegativeInt
    applicability_unknown_count: NonNegativeInt
    completed_count: NonNegativeInt
    unknown_count: NonNegativeInt
    not_applicable_count: NonNegativeInt
    unexecuted_count: NonNegativeInt
    unsupported_scope_count: NonNegativeInt


class CandidateCoverageSummary(BaseModel):
    basis: Literal["enumerated_rule_instances"] = "enumerated_rule_instances"
    catalog_version: str
    counts: CandidateCounts
    by_rule: dict[str, CandidateCounts]
    boundary: str = "候选数仅属于本版本目录的限定规则，含身份/清单核对及明确标注的分组检查，不代表所有工程检查或整板功能。未执行属于未知，不重复相加；不支持范围单列。"


class CandidateRecord(BaseModel):
    candidate_id: str
    rule_id: str
    object_kind: str
    object_id: str
    instance: tuple[tuple[str, str], ...]
    applicability: str
    applicability_reason: str
    executed: bool
    result: CheckResult
    reason: str


def candidate_records(snapshot: CandidateSnapshot) -> list[CandidateRecord]:
    outcomes = {o.candidate_id: o for o in snapshot.outcomes}
    records = []
    for c in snapshot.candidates:
        outcome = outcomes.get(c.candidate_id)
        records.append(
            CandidateRecord(
                candidate_id=c.candidate_id,
                rule_id=c.rule_id,
                object_kind=c.object_kind,
                object_id=c.object_id,
                instance=c.instance,
                applicability=c.applicability,
                applicability_reason=c.reason,
                executed=outcome is not None,
                result=outcome.result
                if outcome
                else "NOT_APPLICABLE"
                if c.applicability == "not_applicable"
                else "UNKNOWN",
                reason=outcome.reason
                if outcome
                else c.reason
                if c.applicability == "not_applicable"
                else "未执行：" + c.reason,
            )
        )
    return records


def summarize_candidates(snapshot: CandidateSnapshot) -> CandidateCoverageSummary:
    outcomes = {o.candidate_id: o for o in snapshot.outcomes}
    grouped = {}
    for c in snapshot.candidates:
        grouped.setdefault(c.rule_id, []).append(c)
    by_rule = {}
    for rule, candidates in sorted(grouped.items()):
        partial = CandidateSnapshot(
            catalog=snapshot.catalog,
            candidates=tuple(candidates),
            outcomes=tuple(
                outcomes[c.candidate_id] for c in candidates if c.candidate_id in outcomes
            ),
        )
        by_rule[rule] = CandidateCounts(**partial.counts())
    return CandidateCoverageSummary(
        catalog_version=snapshot.catalog.version,
        counts=CandidateCounts(**snapshot.counts()),
        by_rule=by_rule,
    )
