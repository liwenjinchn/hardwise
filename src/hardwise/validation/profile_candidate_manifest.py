"""Render profile candidate manifests."""

from __future__ import annotations

from typing import Any

import yaml

from hardwise.path_display import display_path


def render_manifest(report: Any, *, matched_only: bool = False) -> str:
    """Render a YAML candidate manifest for human review."""

    matched = [candidate for candidate in report.candidates if candidate.match_status == "matched"]
    if matched_only:
        return yaml.safe_dump(
            {
                "project": report.project,
                "targets": [
                    {
                        "refdes": candidate.refdes,
                        "profile": display_path(candidate.profile),
                    }
                    for candidate in matched
                ],
            },
            sort_keys=False,
            allow_unicode=True,
        )

    unmatched = [
        candidate for candidate in report.candidates if candidate.match_status != "matched"
    ]
    doc: dict[str, object] = {
        "project": report.project,
        "status": report.status,
        "targets": [_target_row(candidate) for candidate in matched],
        "unmatched": [_unmatched_row(candidate) for candidate in unmatched],
    }
    doc["summary"] = {
        "bom": display_path(report.bom_file),
        "profiles": display_path(report.profiles_dir),
        **report.counts_by_status,
    }
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)


def _target_row(candidate: Any) -> dict[str, object]:
    row: dict[str, object] = {
        "refdes": candidate.refdes,
        "profile": display_path(candidate.profile),
        "match_status": candidate.match_status,
        "identity": candidate.identity,
        "identity_kind": candidate.identity_kind,
    }
    return row


def _unmatched_row(candidate: Any) -> dict[str, object]:
    row: dict[str, object] = {
        "refdes": candidate.refdes,
        "match_status": candidate.match_status,
        "identity": candidate.identity,
        "identity_kind": candidate.identity_kind,
        "reason": candidate.reason,
    }
    if candidate.candidates:
        row["candidates"] = [display_path(path) for path in candidate.candidates]
    return row
