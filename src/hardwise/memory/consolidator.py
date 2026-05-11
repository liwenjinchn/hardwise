"""Sleep Consolidator — deterministic finding-pattern aggregator.

Slice 2 implementation (per `docs/PLAN.md` and the Slice 2 plan):

  - Pure statistical aggregation, no LLM, no embeddings.
  - Group findings by `(rule_id, severity)`; emit one `CandidateRule` per
    group whose count meets `_THRESHOLD`.
  - Append a markdown block to `memory/rules.md` with `STATUS: candidate`.
    The file is created on first call (with a header) and appended-to on
    subsequent calls; existing content is never overwritten.
  - Candidate entries are never auto-promoted to active rules. Promotion is
    a human action (edit the file, or migrate the candidate to
    `data/checklists/sch_review.yaml` with `status: active`).

Why a fixed threshold and a hand-written suggested-action table:
the goal of Slice 2 is to prove the mechanism (frequent-pattern detection
→ candidate file → human gate). Smarter pattern extraction (LLM-driven
"when X then Y" mining) is deferred — see `docs/rolling_log.md`.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from hardwise.checklist.finding import Finding, Severity

_THRESHOLD = 3
_HEADER = (
    "# Hardwise 候选规则池 — 人工 gate\n"
    "\n"
    "> Sleep Consolidator 沉淀的候选规则。每条 `STATUS: candidate` 需要\n"
    "> 评审者人工 review 后，迁到 `data/checklists/sch_review.yaml` 并改为\n"
    "> `status: active` 才会被 agent 调用。candidate 永不自我提升。\n"
)

# Hand-written templates for the suggested action when a particular
# (rule_id, severity) pattern fires. Add new rows here as new rules ship.
_SUGGESTED_ACTION: dict[tuple[str, Severity], str] = {
    ("R002", "medium"): (
        "本项目存在系统性 value 字段缺失耐压标注；建议反馈器件库维护者批量补全 "
        "rated voltage 字段（值 → 值/耐压V 形式）。"
    ),
}


class CandidateRule(BaseModel):
    """One row that will become a `STATUS: candidate` block in memory/rules.md."""

    rule_id: str
    severity: Severity
    count: int
    project_slug: str
    suggested_action: str
    generated_at: datetime


def consolidate(
    findings: list[Finding],
    project_slug: str,
    output_path: Path = Path("memory/rules.md"),
    now: datetime | None = None,
) -> list[CandidateRule]:
    """Aggregate findings into candidate rules; append any to `output_path`.

    Returns the list of `CandidateRule`s emitted this call (empty list if
    none of the buckets reached the threshold). Idempotent over the same
    `findings` only if `now` is pinned — otherwise the timestamp differs.
    """

    if now is None:
        now = datetime.now(timezone.utc)

    counts: Counter[tuple[str, Severity]] = Counter()
    for f in findings:
        counts[(f.rule_id, f.severity)] += 1

    candidates: list[CandidateRule] = []
    for (rule_id, severity), count in counts.items():
        if count < _THRESHOLD:
            continue
        candidates.append(
            CandidateRule(
                rule_id=rule_id,
                severity=severity,
                count=count,
                project_slug=project_slug,
                suggested_action=_SUGGESTED_ACTION.get(
                    (rule_id, severity),
                    (
                        f"本项目 {rule_id} 在一次评审中产生 {count} 个 "
                        f"{severity} 级 finding，值得追因。"
                    ),
                ),
                generated_at=now,
            )
        )

    if not candidates:
        return []

    candidates.sort(key=lambda c: (c.rule_id, c.severity))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not output_path.exists()
    with output_path.open("a", encoding="utf-8") as fh:
        if new_file:
            fh.write(_HEADER)
        for c in candidates:
            fh.write(_render_block(c))

    return candidates


def _render_block(c: CandidateRule) -> str:
    date_stamp = c.generated_at.strftime("%Y-%m-%d")
    return (
        f"\n## candidate / {date_stamp} / {c.project_slug}\n"
        f"- rule_id: {c.rule_id}\n"
        f"- severity: {c.severity}\n"
        f"- count: {c.count}\n"
        f"- suggested action: {c.suggested_action}\n"
        f"- STATUS: candidate\n"
    )
