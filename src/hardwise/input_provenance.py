"""Hash bytes actually consumed by registered intake readers, scoped to one build."""

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict


class InputChangedError(ValueError):
    """A source changed while a deterministic context was being built."""


class InputFileDigest(BaseModel):
    model_config = ConfigDict(frozen=True)
    path: str
    resolved_path: str
    roles: tuple[str, ...]
    size_bytes: int
    sha256: str


class InputReadManifest(BaseModel):
    model_config = ConfigDict(frozen=True)
    schema_version: Literal["hardwise.input_reads.v1"] = "hardwise.input_reads.v1"
    assurance: Literal["observed_readset_verified"] = "observed_readset_verified"
    started_at: str
    verified_at: str
    readset_sha256: str
    files: tuple[InputFileDigest, ...]


_active: ContextVar["InputReadCollector | None"] = ContextVar("hardwise_input_reads", default=None)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _file_hash(path: Path) -> tuple[int, str]:
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return size, digest.hexdigest()


class InputReadCollector:
    def __init__(self):
        self.started_at = _now()
        self.files: dict[str, InputFileDigest] = {}
        self.versions: dict[str, str] = {}
        self.failure: str | None = None

    def failed_read(self, path: Path):
        # Optional first-time misses are allowed; a previously consumed source
        # disappearing must not be hidden by a tolerant catalog reader.
        logical = str(path.absolute())
        if logical in self.files:
            self.failure = f"input became unavailable during intake: {logical}"

    def record(self, path: Path, resolved: Path, role: str, size: int, sha: str):
        logical = str(path.absolute())
        target = str(resolved)
        previous = self.files.get(logical)
        if (target in self.versions and self.versions[target] != sha) or (
            previous and (previous.sha256 != sha or previous.resolved_path != target)
        ):
            self.failure = f"input changed during intake: {logical}"
            raise InputChangedError(self.failure)
        roles = sorted(set(previous.roles if previous else ()) | {role})
        self.files[logical] = InputFileDigest(
            path=logical, resolved_path=target, roles=tuple(roles), size_bytes=size, sha256=sha
        )
        self.versions[target] = sha

    def finish(self) -> InputReadManifest:
        if self.failure:
            raise InputChangedError(self.failure)
        if not self.files:
            raise InputChangedError("no registered input reads were captured")
        for item in self.files.values():
            try:
                resolved = Path(item.path).resolve()
                size, sha = _file_hash(resolved)
            except OSError as exc:
                raise InputChangedError(
                    f"input became unavailable during intake: {item.path}"
                ) from exc
            if str(resolved) != item.resolved_path or size != item.size_bytes or sha != item.sha256:
                raise InputChangedError(f"input changed during intake: {item.path}")
        files = tuple(self.files[key] for key in sorted(self.files))
        serialized = json.dumps(
            [f.model_dump(mode="json") for f in files], sort_keys=True, separators=(",", ":")
        )
        return InputReadManifest(
            started_at=self.started_at,
            verified_at=_now(),
            files=files,
            readset_sha256=hashlib.sha256(serialized.encode()).hexdigest(),
        )


@contextmanager
def capture_input_reads():
    collector = InputReadCollector()
    token = _active.set(collector)
    try:
        yield collector
    finally:
        _active.reset(token)


def read_input_bytes(path: Path, *, role: str) -> bytes:
    collector = _active.get()
    try:
        resolved = path.resolve() if collector else path
        data = resolved.read_bytes()
    except OSError:
        if collector:
            collector.failed_read(path)
        raise
    if collector:
        collector.record(path, resolved, role, len(data), hashlib.sha256(data).hexdigest())
    return data


def read_input_text(
    path: Path, *, role: str, encoding="utf-8", errors="strict", newline=None
) -> str:
    if _active.get() is None:
        with path.open(encoding=encoding, errors=errors, newline=newline) as stream:
            return stream.read()
    data = read_input_bytes(path, role=role)
    with io.TextIOWrapper(
        io.BytesIO(data), encoding=encoding, errors=errors, newline=newline
    ) as stream:
        return stream.read()


def hash_input_file(path: Path, *, role: str) -> str:
    collector = _active.get()
    try:
        resolved = path.resolve() if collector else path
        size, sha = _file_hash(resolved)
    except OSError:
        if collector:
            collector.failed_read(path)
        raise
    if collector:
        collector.record(path, resolved, role, size, sha)
    return sha
