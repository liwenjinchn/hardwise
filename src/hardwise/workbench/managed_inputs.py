"""Immutable, verified observed-input snapshots beside a reviewer journal."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
from uuid import uuid4

from hardwise.input_provenance import InputReadManifest, InputChangedError

_VERSION = "hardwise.managed_inputs.v1"
_ID = re.compile(r"[0-9a-f]{32}")


class ManagedInputs:
    """Publish sources before a future journal transaction references a snapshot.

    This primitive owns bytes, not project identity or active-version selection.
    An unreferenced snapshot cannot become an active review by itself.
    """

    def __init__(self, journal: Path):
        self.root = journal.resolve().with_name(journal.name + ".inputs")

    def capture(self, observed: InputReadManifest) -> str:
        if not observed.files:
            raise ValueError("Cannot save an empty input snapshot")
        self.root.mkdir(parents=True, exist_ok=True)
        snapshot = uuid4().hex
        staging = self.root / (".staging-" + snapshot)
        staging.mkdir()
        try:
            (staging / "files").mkdir()
            entries = []
            for index, source in enumerate(observed.files):
                path = Path(source.path)
                # Verify the same logical path still resolves to the parsed source.
                if str(path.resolve()) != source.resolved_path:
                    raise InputChangedError(f"Source target changed before save: {source.path}")
                data = path.read_bytes()
                if len(data) != source.size_bytes or _sha(data) != source.sha256:
                    raise InputChangedError(f"Source bytes changed before save: {source.path}")
                member = f"files/{index:06d}.bin"
                _write(staging / member, data)
                entries.append(dict(member=member, **source.model_dump(mode="json")))
            manifest = dict(
                schema_version=_VERSION,
                snapshot_id=snapshot,
                observed=observed.model_dump(mode="json"),
                entries=entries,
            )
            _write(
                staging / "manifest.json",
                (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
            )
            self._validate(staging, snapshot)
            staging.rename(self.root / snapshot)
            return snapshot
        finally:
            if staging.exists():
                shutil.rmtree(staging)

    def load(self, snapshot: str) -> dict:
        """Validate stored bytes before a caller constructs a candidate context."""
        if not _ID.fullmatch(snapshot):
            raise ValueError("Invalid managed input snapshot identifier")
        directory = self.root / snapshot
        if directory.is_symlink():
            raise ValueError("Managed input snapshot cannot be a symlink")
        return self._validate(directory, snapshot)

    @staticmethod
    def _validate(directory: Path, snapshot: str) -> dict:
        manifest_path = directory / "manifest.json"
        if manifest_path.is_symlink():
            raise ValueError("Managed input manifest cannot be a symlink")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("Invalid managed input manifest")
        if manifest.get("schema_version") != _VERSION or manifest.get("snapshot_id") != snapshot:
            raise ValueError("Unsupported or mismatched managed input manifest")
        observed = InputReadManifest.model_validate(manifest.get("observed"))
        entries = manifest.get("entries")
        if not isinstance(entries, list) or not entries or len(entries) != len(observed.files):
            raise ValueError("Incomplete managed input snapshot")
        allowed = {"manifest.json"}
        for index, (entry, source) in enumerate(zip(entries, observed.files, strict=True)):
            if not isinstance(entry, dict):
                raise ValueError("Invalid managed source entry")
            member = entry.get("member")
            if member != f"files/{index:06d}.bin":
                raise ValueError("Invalid managed input member")
            if {k: v for k, v in entry.items() if k != "member"} != source.model_dump(mode="json"):
                raise ValueError("Managed source metadata differs from observed input")
            path = directory.joinpath(*PurePosixPath(member).parts)
            if path.parent.is_symlink() or path.is_symlink():
                raise ValueError("Managed source cannot be a symlink")
            data = path.read_bytes()
            if len(data) != source.size_bytes or _sha(data) != source.sha256:
                raise ValueError(f"Managed source hash mismatch: {member}")
            allowed.add(member)
        paths = list(directory.rglob("*"))
        if any(path.is_symlink() for path in paths):
            raise ValueError("Managed snapshot cannot contain symlinks")
        present = {str(p.relative_to(directory).as_posix()) for p in paths if p.is_file()}
        if present != allowed:
            raise ValueError("Unexpected files in managed input snapshot")
        return manifest


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, data: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
