"""Consistent journal + referenced immutable source backup, with fresh-target restore."""

import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import stat
import tempfile
from typing import Literal
import zipfile

from pydantic import BaseModel, ConfigDict, Field

from hardwise.workbench.context import close_workbench_context
from hardwise.workbench.managed_inputs import ManagedInputs
from hardwise.workbench.managed_projects import ManagedProjects, SavedDescriptor

JOURNAL = "journal.sqlite"
MARKER = ".hardwise-restore-incomplete"
# Bound untrusted extraction before allocating decompressed members.
MAX_FILES = 50000
MAX_TOTAL = 1024 * 1024 * 1024
MAX_MANIFEST = 16 * 1024 * 1024


class Member(BaseModel):
    model_config = ConfigDict(extra="forbid")
    size: int = Field(ge=0, le=MAX_TOTAL)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class BackupManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["hardwise.project_backup.v1"] = "hardwise.project_backup.v1"
    scope: Literal["saved_projects_and_journal_history"] = "saved_projects_and_journal_history"
    files: dict[str, Member]
    saved_project_ids: list[str]
    source_unowned_project_ids: list[str]


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _catalog(journal):
    with sqlite3.connect(f"{journal.as_uri()}?mode=ro", uri=True) as db:
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Invalid backup journal")
        if db.execute("PRAGMA user_version").fetchone()[0] != 2:
            raise ValueError("Backup requires a saved-project journal v2")
        objects = set(
            db.execute("SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")
        )
        expected = {
            ("table", name)
            for name in (
                "review_state",
                "review_events",
                "review_runs",
                "review_heads",
                "managed_projects",
            )
        }
        if objects != expected:
            raise ValueError("Unexpected backup journal schema")
        rows = db.execute(
            "SELECT id,project,snapshot,descriptor FROM managed_projects ORDER BY id"
        ).fetchall()
        all_projects = {p for (p,) in db.execute("SELECT project FROM review_heads")}
    if not rows:
        raise ValueError("Save a project before creating a complete input backup")
    snapshots = set()
    for _, _, head, raw in rows:
        descriptor = SavedDescriptor.model_validate_json(raw)
        snapshots.update([head, *descriptor.retained_snapshots])
    return rows, snapshots, sorted(all_projects - {row[1] for row in rows})


def backup_projects(journal: Path, output: Path):
    journal, output = journal.resolve(), output.absolute()
    if not journal.is_file():
        raise ValueError("Existing review journal is required")
    if output.resolve().is_relative_to(ManagedInputs(journal).root):
        raise ValueError("Backup output must be outside the managed input store")
    if output.exists():
        raise FileExistsError("Backup output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hardwise-backup-") as tmp:
        root = Path(tmp)
        frozen = root / JOURNAL
        # SQLite online backup captures one committed database, not a raw hot-file copy.
        with sqlite3.connect(f"{journal.as_uri()}?mode=ro", uri=True) as source:
            with sqlite3.connect(frozen) as target:
                source.backup(target)
        rows, snapshots, unowned = _catalog(frozen)
        inputs = ManagedInputs(journal)
        destination = ManagedInputs(frozen)
        destination.root.mkdir()
        for snapshot in sorted(snapshots):
            inputs.load(snapshot)
            shutil.copytree(inputs.root / snapshot, destination.root / snapshot, symlinks=True)
            destination.load(snapshot)
        manifest = _manifest(root, rows, unowned)
        archive = root / "backup.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name in manifest.files:
                z.write(root / name, name)
            z.writestr("backup-manifest.json", manifest.model_dump_json(indent=2))
        # Exclusive creation cannot replace a concurrently created output.
        try:
            with output.open("xb") as target, archive.open("rb") as source:
                shutil.copyfileobj(source, target)
                target.flush()
                os.fsync(target.fileno())
        except FileExistsError:
            raise
        except BaseException:
            output.unlink(missing_ok=True)
            raise
    return dict(
        archive=str(output),
        sha256=_digest(output.read_bytes()),
        saved_project_ids=manifest.saved_project_ids,
        source_unowned_project_ids=unowned,
    )


def _manifest(root, rows, unowned):
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlinks are not backup members")
        if path.is_file():
            data = path.read_bytes()
            files[path.relative_to(root).as_posix()] = Member(size=len(data), sha256=_digest(data))
    if len(files) > MAX_FILES or sum(f.size for f in files.values()) > MAX_TOTAL:
        raise ValueError("Backup exceeds supported size")
    return BackupManifest(
        files=files, saved_project_ids=[r[0] for r in rows], source_unowned_project_ids=unowned
    )


def _safe_member(name):
    p = PurePosixPath(name)
    if (
        not p.parts
        or p.is_absolute()
        or ".." in p.parts
        or "\\" in name
        or ":" in name
        or p.as_posix() != name
    ):
        raise ValueError("Invalid backup member path")
    if name != JOURNAL and not name.startswith(JOURNAL + ".inputs/"):
        raise ValueError("Unexpected backup member")
    return p


def _extract(archive, root):
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        if len(infos) > MAX_FILES + 1 or len({name.casefold() for name in names}) != len(names):
            raise ValueError("Duplicate or excessive backup members")
        meta = z.getinfo("backup-manifest.json")
        if meta.file_size > MAX_MANIFEST:
            raise ValueError("Backup manifest is too large")
        manifest = BackupManifest.model_validate_json(z.read(meta))
        if set(names) != {*manifest.files, "backup-manifest.json"}:
            raise ValueError("Backup manifest/member set mismatch")
        if sum(i.file_size for i in infos) > MAX_TOTAL + MAX_MANIFEST:
            raise ValueError("Backup exceeds supported size")
        for info in infos:
            if stat.S_ISLNK(info.external_attr >> 16) or info.flag_bits & 1 or info.is_dir():
                raise ValueError("Unsupported backup member type")
            if info.filename == "backup-manifest.json":
                continue
            member = _safe_member(info.filename)
            expected = manifest.files[info.filename]
            if info.file_size != expected.size:
                raise ValueError("Backup member size mismatch")
            data = z.read(info)
            if _digest(data) != expected.sha256:
                raise ValueError("Backup member hash mismatch")
            target = root.joinpath(*member.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    rows, snapshots, unowned = _catalog(root / JOURNAL)
    if (
        manifest.saved_project_ids != [r[0] for r in rows]
        or manifest.source_unowned_project_ids != unowned
    ):
        raise ValueError("Backup catalog differs from manifest")
    inputs = ManagedInputs(root / JOURNAL)
    if {p.name for p in inputs.root.iterdir()} != snapshots:
        raise ValueError("Referenced source snapshot set mismatch")
    for snapshot in snapshots:
        inputs.load(snapshot)
    # Also prove current sources reconstruct a context, before target publication.
    for identifier, _, _, _ in rows:
        context, directory = ManagedProjects(root / JOURNAL).open(identifier)
        close_workbench_context(context)
        shutil.rmtree(directory)
    return manifest


def restore_projects(archive: Path, destination: Path):
    destination = destination.absolute()
    if any(parent.name.endswith(".inputs") for parent in destination.parents):
        raise ValueError("Restore destination must be outside managed input directories")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Restore destination must be new; existing data is never replaced")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".hardwise-restore-", dir=destination.parent) as tmp:
        root = Path(tmp)
        manifest = _extract(archive, root)
        # Reserve a new destination exclusively. The sentinel blocks all journal
        # opens across an interrupted multi-file publication; the database goes last.
        destination.mkdir()
        try:
            (destination / MARKER).write_text("Restore publication incomplete\n")
            shutil.move(str(root / (JOURNAL + ".inputs")), destination / (JOURNAL + ".inputs"))
            shutil.move(str(root / JOURNAL), destination / JOURNAL)
            (destination / MARKER).unlink()
        except BaseException:
            shutil.rmtree(destination)
            raise
    return dict(
        journal=str(destination / JOURNAL),
        saved_project_ids=manifest.saved_project_ids,
        source_unowned_project_ids=manifest.source_unowned_project_ids,
    )
