"""Managed source references in the reviewer journal, without rewriting history."""

import json
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from uuid import uuid4
from typing import Literal

from pydantic import BaseModel, ConfigDict

from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.decision_fingerprints import review_project_key
from hardwise.workbench.decision_journal import DecisionJournal, ReviewConflictError
from hardwise.workbench.managed_inputs import ManagedInputs


class SavedArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    netlist_path: str
    bom_path: str
    profiles: str
    document_index: str | None = None
    pin_table: str | None = None
    risk_hints_json: str | None = None
    review_package_manifest: str | None = None
    voltage_facts: str | None = None


class SavedDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["hardwise.managed_project.v1", "hardwise.managed_project.v2"]
    arguments: SavedArguments
    sources: dict[str, str]
    name: str = "已保存项目"
    retained_snapshots: list[str] = []


class ManagedProjectMissing(KeyError):
    pass


def _arguments(context):
    return dict(
        netlist_path=context.netlist_source,
        bom_path=context.bom.source_file,
        profiles=Path(context.candidate_report.profiles_dir),
        document_index=(
            context.document_report.document_index_file if context.document_report else None
        ),
        pin_table=context.pin_table_path,
        risk_hints_json=(
            Path(context.risk_hints.source_path) if context.risk_hints.source_path else None
        ),
        review_package_manifest=(
            Path(context.review_package.source_path) if context.review_package.source_path else None
        ),
        voltage_facts=context.voltage_facts_path,
    )


def _relative(path):
    value = PurePosixPath(path)
    if value.is_absolute() or not value.parts or ".." in value.parts or "\\" in path or ":" in path:
        raise ValueError("Invalid saved project relative path")
    return Path(*value.parts)


class ManagedProjects:
    def __init__(self, journal: Path):
        self.journal = DecisionJournal(journal)
        self.inputs = ManagedInputs(journal)

    def list(self):
        with self.journal.connect() as db:
            return [
                dict(
                    id=i, project_id=p, snapshot=s, name=SavedDescriptor.model_validate_json(d).name
                )
                for i, p, s, d in db.execute(
                    "SELECT id,project,snapshot,descriptor FROM managed_projects ORDER BY id"
                )
            ]

    def save(self, context, expected_run_id: str):
        if context.input_manifest is None:
            raise ValueError("Source read manifest is required")
        project = review_project_key(context)
        args = _arguments(context)
        paths = [Path(f.path) for f in context.input_manifest.files]
        paths.extend(Path(p).absolute() for p in args.values() if p is not None)
        base = Path(os.path.commonpath([str(p.parent) for p in paths]))
        descriptor = dict(
            schema_version="hardwise.managed_project.v2",
            name=context.project_name,
            arguments={
                k: str(Path(v).absolute().relative_to(base).as_posix()) if v else None
                for k, v in args.items()
            },
            sources={
                f.path: str(Path(f.path).relative_to(base).as_posix())
                for f in context.input_manifest.files
            },
        )
        snapshot = self.inputs.capture(context.input_manifest)
        # A stale writer may leave an unreferenced immutable snapshot, never an active one.
        with self.journal.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT run_id FROM review_runs WHERE project=? ORDER BY rowid DESC LIMIT 1",
                (project,),
            ).fetchone()
            if not row or row[0] != expected_run_id:
                raise ReviewConflictError("Review run changed before project save")
            row = db.execute(
                "SELECT id,snapshot,descriptor FROM managed_projects WHERE project=?", (project,)
            ).fetchone()
            identifier = row[0] if row else uuid4().hex
            if row:
                previous = SavedDescriptor.model_validate_json(row[2])
                descriptor["retained_snapshots"] = list(
                    dict.fromkeys([*previous.retained_snapshots, row[1]])
                )
            db.execute(
                "INSERT INTO managed_projects VALUES(?,?,?,?) ON CONFLICT(project) DO UPDATE SET snapshot=excluded.snapshot,descriptor=excluded.descriptor",
                (identifier, project, snapshot, json.dumps(descriptor, ensure_ascii=False)),
            )
        context.managed_project_id = identifier
        context.managed_project_key = project
        return dict(id=identifier, project_id=project, snapshot=snapshot, name=context.project_name)

    def open(self, identifier: str):
        with self.journal.connect() as db:
            row = db.execute(
                "SELECT project,snapshot,descriptor FROM managed_projects WHERE id=?", (identifier,)
            ).fetchone()
        if row is None:
            raise ManagedProjectMissing(identifier)
        project, snapshot, raw = row
        descriptor = SavedDescriptor.model_validate_json(raw).model_dump()
        manifest = self.inputs.load(snapshot)
        sources = descriptor["sources"]
        if set(sources) != {entry["path"] for entry in manifest["entries"]}:
            raise ValueError("Saved sources differ from snapshot")
        targets = [_relative(value) for value in sources.values()]
        if len(set(targets)) != len(targets):
            raise ValueError("Saved sources collide")
        arguments = {k: _relative(v) if v else None for k, v in descriptor["arguments"].items()}
        directory = Path(tempfile.mkdtemp(prefix="hardwise-managed-open-"))
        context = None
        try:
            for entry in manifest["entries"]:
                target = directory / _relative(sources[entry["path"]])
                target.parent.mkdir(parents=True, exist_ok=True)
                data = (self.inputs.root / snapshot / entry["member"]).read_bytes()
                if (
                    len(data) != entry["size_bytes"]
                    or hashlib.sha256(data).hexdigest() != entry["sha256"]
                ):
                    raise ValueError("Managed source changed while opening")
                target.write_bytes(data)
            # Profiles may be empty. They are a directory, never a fallback to today's catalog.
            (directory / arguments["profiles"]).mkdir(parents=True, exist_ok=True)
            context = build_workbench_context(
                **{k: directory / v if v else None for k, v in arguments.items()}
            )
            context.managed_project_key = project
            context.managed_project_id = identifier
            return context, directory
        except Exception:
            if context is not None:
                close_workbench_context(context)
            shutil.rmtree(directory)
            raise
