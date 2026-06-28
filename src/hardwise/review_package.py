"""Review-package artifact manifest for pre-layout evidence handoff."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

ReviewArtifactKind = Literal[
    "schematic_pdf",
    "erc_drc_report",
    "checklist",
    "review_notes",
    "other",
]
ReviewArtifactStatus = Literal["present", "missing", "hash_mismatch"]

ALLOWED_KINDS = {
    "schematic_pdf",
    "erc_drc_report",
    "checklist",
    "review_notes",
    "other",
}


class ReviewPackageParseError(ValueError):
    """Raised when a review-package manifest cannot be parsed safely."""


class ReviewPackageArtifactInput(BaseModel):
    """One manifest row before file-system resolution."""

    kind: ReviewArtifactKind
    path: str
    required: bool = True
    sha256: str | None = None
    note: str | None = None

    @field_validator("kind", mode="before")
    @classmethod
    def _normalize_kind(cls, value: object) -> str:
        normalized = str(value or "").strip().lower().replace("-", "_")
        if normalized not in ALLOWED_KINDS:
            raise ValueError(f"unknown review artifact kind: {value!r}")
        return normalized

    @field_validator("path", mode="before")
    @classmethod
    def _clean_path(cls, value: object) -> str:
        cleaned = str(value or "").strip()
        if not cleaned:
            raise ValueError("artifact path is required")
        return cleaned

    @field_validator("sha256", mode="before")
    @classmethod
    def _clean_sha256(cls, value: object) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip().lower()
        return cleaned or None

    @field_validator("note", mode="before")
    @classmethod
    def _clean_note(cls, value: object) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None


class ReviewPackagePayload(BaseModel):
    """Accepted top-level manifest shape."""

    artifacts: list[ReviewPackageArtifactInput] = Field(default_factory=list)


class ReviewPackageArtifact(BaseModel):
    """Resolved artifact state exposed to reports and workbench views."""

    kind: ReviewArtifactKind
    path: str
    name: str
    required: bool
    status: ReviewArtifactStatus
    sha256: str | None = None
    expected_sha256: str | None = None
    note: str | None = None


class ReviewPackageReport(BaseModel):
    """Resolved review-package manifest summary."""

    source_path: str | None = None
    artifacts: list[ReviewPackageArtifact] = Field(default_factory=list)

    @property
    def present_count(self) -> int:
        """Number of artifacts that exist and passed any hash check."""

        return sum(1 for artifact in self.artifacts if artifact.status == "present")

    @property
    def missing_required_count(self) -> int:
        """Number of required artifacts missing from disk."""

        return sum(
            1
            for artifact in self.artifacts
            if artifact.required and artifact.status == "missing"
        )

    @property
    def missing_optional_count(self) -> int:
        """Number of optional artifacts missing from disk."""

        return sum(
            1
            for artifact in self.artifacts
            if not artifact.required and artifact.status == "missing"
        )

    @property
    def hash_mismatch_count(self) -> int:
        """Number of present artifacts whose sha256 does not match the manifest."""

        return sum(1 for artifact in self.artifacts if artifact.status == "hash_mismatch")

    @property
    def counts(self) -> dict[str, int]:
        """Stable count summary for CLI and workbench."""

        return {
            "total": len(self.artifacts),
            "present": self.present_count,
            "missing_required": self.missing_required_count,
            "missing_optional": self.missing_optional_count,
            "hash_mismatch": self.hash_mismatch_count,
        }


def load_review_package_manifest(path: Path | str) -> ReviewPackageReport:
    """Load and resolve a YAML/JSON review-package manifest."""

    manifest_path = Path(path)
    try:
        raw_payload = _load_payload(manifest_path)
        payload = ReviewPackagePayload.model_validate(raw_payload)
    except (OSError, ValidationError, yaml.YAMLError, json.JSONDecodeError, TypeError) as exc:
        raise ReviewPackageParseError(f"{manifest_path}: {exc}") from exc

    if not payload.artifacts:
        raise ReviewPackageParseError(f"{manifest_path}: no artifacts listed")

    artifacts = [
        _resolve_artifact(item, manifest_path.parent) for item in payload.artifacts
    ]
    return ReviewPackageReport(source_path=str(manifest_path), artifacts=artifacts)


def render_review_package_markdown(report: ReviewPackageReport) -> str:
    """Render a review-package report without implying signoff."""

    counts = report.counts
    lines = [
        "# Review Package Evidence Manifest",
        "",
        f"- source: `{report.source_path or 'not_configured'}`",
        f"- artifacts: {counts['present']} present / {counts['total']} total",
        f"- missing required: {counts['missing_required']}",
        f"- missing optional: {counts['missing_optional']}",
        f"- hash mismatches: {counts['hash_mismatch']}",
        "",
        "| kind | status | required | name | sha256 | note |",
        "|---|---|---:|---|---|---|",
    ]
    for artifact in report.artifacts:
        sha = artifact.sha256 or ""
        if artifact.expected_sha256 and artifact.expected_sha256 != artifact.sha256:
            sha = f"{sha} (expected {artifact.expected_sha256})"
        lines.append(
            "| "
            f"{artifact.kind} | {artifact.status} | {artifact.required} | "
            f"`{artifact.name}` | `{sha}` | {artifact.note or ''} |"
        )
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "This manifest records exported review-package evidence only: schematic PDF, "
            "ERC/DRC reports, checklist exports, review notes, and similar handoff files. "
            "Hardwise stores presence, source path, sha256, and missing-artifact status; "
            "it does not parse these files into electrical findings and does not replace "
            "formal hardware signoff.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_payload(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


def _resolve_artifact(
    item: ReviewPackageArtifactInput,
    manifest_dir: Path,
) -> ReviewPackageArtifact:
    raw_path = Path(item.path).expanduser()
    resolved_path = raw_path if raw_path.is_absolute() else manifest_dir / raw_path
    exists = resolved_path.is_file()
    actual_sha = _sha256_file(resolved_path) if exists else None
    status: ReviewArtifactStatus
    if not exists:
        status = "missing"
    elif item.sha256 and actual_sha != item.sha256:
        status = "hash_mismatch"
    else:
        status = "present"
    return ReviewPackageArtifact(
        kind=item.kind,
        path=str(resolved_path),
        name=raw_path.name,
        required=item.required,
        status=status,
        sha256=actual_sha,
        expected_sha256=item.sha256,
        note=item.note,
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
