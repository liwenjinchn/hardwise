"""Create human-review datasheet profile draft scaffolds from project coverage."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from hardwise.documents import match_documents_to_bom, parse_document_index
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.profile_archetypes import (
    ProfileArchetypeError,
    apply_profile_archetype,
)
from hardwise.validation.component_groups import ProjectComponentGroup
from hardwise.validation.project_index import ProjectValidationIndex


class ProfileDraftError(ValueError):
    """Raised when a profile draft cannot be generated."""


def draft_profile_from_project_index(
    index_path: Path,
    *,
    identity: str,
    document_index_path: Path | None = None,
    archetype_id: str | None = None,
    evidence_chunks_path: Path | None = None,
) -> DatasheetProfile:
    """Build a needs-review profile draft for one component group identity."""

    index = _load_project_index(index_path)
    group = _find_group(index, identity)
    document_title = group.document_title
    document_url = group.document_url
    document_source = group.document_source
    if document_index_path is not None:
        document_title, document_url, document_source = _document_from_index(
            index,
            group,
            document_index_path,
        )

    if not document_url and not document_title:
        raise ProfileDraftError(
            f"{identity}: no matched document is available; review document-index first"
        )

    part_number = group.part_number or group.identity
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    evidence_token = document_source or f"doc:{Path(document_url or document_title or identity).name}"
    profile = DatasheetProfile(
        part_number=part_number,
        part_number_aliases=_aliases(group, part_number),
        review_status="needs_review",
        recommended={"suggested_family": group.suggested_family},
        pin_function={},
        pins=[],
        evidence={
            "document.title": document_title or "",
            "document.url": document_url or "",
            "document.source": evidence_token,
            "draft.group_id": group.group_id,
        },
        extracted_at=now,
        extracted_model="manual-review-draft-v1.2",
        schema_version="v2",
    )
    if archetype_id is not None:
        try:
            profile = apply_profile_archetype(profile, archetype_id)
        except ProfileArchetypeError as exc:
            raise ProfileDraftError(str(exc)) from exc

    if evidence_chunks_path is not None:
        profile = _attach_evidence_chunks(profile, evidence_chunks_path)
    return profile


def _load_project_index(path: Path) -> ProjectValidationIndex:
    try:
        return ProjectValidationIndex.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError) as exc:
        raise ProfileDraftError(
            f"{path}: failed to load project validation index: {type(exc).__name__}: {exc}"
        ) from exc


def _find_group(index: ProjectValidationIndex, identity: str) -> ProjectComponentGroup:
    target = _normalize(identity)
    matches = [
        group
        for group in index.component_groups
        if target in {_normalize(group.identity), _normalize(group.part_number)}
    ]
    if not matches:
        raise ProfileDraftError(f"{identity}: no component group matched this identity")
    if len(matches) > 1:
        identities = ", ".join(sorted(group.identity for group in matches))
        raise ProfileDraftError(f"{identity}: matched multiple component groups: {identities}")
    return matches[0]


def _document_from_index(
    index: ProjectValidationIndex,
    group: ProjectComponentGroup,
    document_index_path: Path,
) -> tuple[str | None, str | None, str | None]:
    from hardwise.bom import parse_bom

    document_report = match_documents_to_bom(parse_bom(Path(index.bom_source)), parse_document_index(document_index_path))
    match = document_report.matches_by_item_key.get(group.group_id)
    if match is None or match.selected is None:
        raise ProfileDraftError(
            f"{group.identity}: document-index has no unique match for this component group"
        )
    return match.selected.title, match.selected.url, match.selected.source_token


def _aliases(group: ProjectComponentGroup, part_number: str) -> list[str]:
    aliases = []
    for value in [group.identity, group.value]:
        if value and _normalize(value) != _normalize(part_number):
            aliases.append(value)
    return aliases


def _attach_evidence_chunks(profile: DatasheetProfile, path: Path) -> DatasheetProfile:
    tokens, sources, chunk_count = _read_evidence_chunk_summary(path)
    if not tokens:
        raise ProfileDraftError(f"{path}: no datasheet evidence tokens found")
    evidence = dict(profile.evidence)
    evidence.update(
        {
            "evidence.chunks.path": str(path),
            "evidence.chunks.count": str(chunk_count),
            "evidence.chunks.sources": ", ".join(sources),
            "evidence.chunks.tokens": ", ".join(tokens),
        }
    )
    return profile.model_copy(update={"evidence": evidence})


def _read_evidence_chunk_summary(path: Path) -> tuple[list[str], list[str], int]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ProfileDraftError(f"{path}: evidence chunk JSONL unreadable") from exc

    tokens: list[str] = []
    sources: list[str] = []
    chunk_count = 0
    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProfileDraftError(f"{path}:{line_no}: invalid evidence chunk JSON") from exc
        if not isinstance(row, dict):
            raise ProfileDraftError(f"{path}:{line_no}: evidence chunk row must be an object")
        chunk_count += 1
        token = _evidence_token_from_chunk(row)
        if token and token not in tokens:
            tokens.append(token)
        source = _source_from_chunk(row)
        if source and source not in sources:
            sources.append(source)
    return tokens, sources, chunk_count


def _evidence_token_from_chunk(row: dict[str, Any]) -> str | None:
    token = row.get("evidence_token")
    if isinstance(token, str) and token.startswith("datasheet:") and "#p" in token:
        return token

    source_pdf = _source_from_chunk(row)
    page = row.get("page")
    if source_pdf and isinstance(page, int) and page >= 1:
        return f"datasheet:{source_pdf}#p{page}"
    return None


def _source_from_chunk(row: dict[str, Any]) -> str | None:
    source_pdf = row.get("source_pdf")
    if isinstance(source_pdf, str):
        stripped = source_pdf.strip()
        if stripped:
            return stripped
    return None


def _normalize(value: str | None) -> str:
    return "".join(ch.lower() for ch in value or "" if ch.isalnum())
