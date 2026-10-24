"""Browser backup download and isolated restore; never replace the active journal."""

from pathlib import Path
import shlex
import shutil
import sqlite3
import tempfile
from uuid import uuid4
import zipfile

from fastapi import File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from hardwise.workbench.project_backup import (
    backup_projects,
    restore_projects,
    MAX_TOTAL,
    MAX_MANIFEST,
    MAX_FILES,
)
from hardwise.workbench.managed_project_contracts import (
    ProjectRestoreReceipt,
    RestoredProjectLaunch,
)

# Account for ZIP headers in addition to the expanded payload/manifest bounds.
MAX_UPLOAD = MAX_TOTAL + MAX_MANIFEST + MAX_FILES * 1024


def _receipt(result, identifier):
    launches = []
    for saved_id in result["saved_project_ids"]:
        args = [
            "uv",
            "run",
            "hardwise",
            "serve-workbench",
            "--review-db",
            result["journal"],
            "--open-project",
            saved_id,
            "--no-auto-datasheet-candidates",
        ]
        launches.append(
            RestoredProjectLaunch(
                saved_id=saved_id,
                command_posix=shlex.join(args),
                command_powershell="& "
                + " ".join("'" + arg.replace("'", "''") + "'" for arg in args),
            )
        )
    return ProjectRestoreReceipt(restore_id=identifier, launches=launches, **result)


def register_project_archive_routes(app, *, require_store, require_current, manager, lock):
    @app.post("/api/workbench/projects/backup")
    def download_backup(expected_run_id: str = Query(..., min_length=1)):
        store = require_store()
        directory = Path(tempfile.mkdtemp(prefix="hardwise-browser-backup-"))
        try:
            with lock, manager.lease() as context:
                require_current(context, expected_run_id)
                archive = directory / "hardwise-projects.zip"
                result = backup_projects(store.journal.path, archive)
            return FileResponse(
                archive,
                media_type="application/zip",
                filename="hardwise-projects.zip",
                headers={
                    "X-Hardwise-Backup-Unowned-Projects": str(
                        len(result["source_unowned_project_ids"])
                    ),
                    "X-Hardwise-Backup-Saved-Projects": str(len(result["saved_project_ids"])),
                },
                background=BackgroundTask(shutil.rmtree, directory),
            )
        except HTTPException:
            shutil.rmtree(directory)
            raise
        except (OSError, ValueError, sqlite3.Error, zipfile.BadZipFile) as exc:
            shutil.rmtree(directory)
            raise HTTPException(422, f"Backup could not be created: {exc}") from exc

    @app.post("/api/workbench/projects/restore", response_model=ProjectRestoreReceipt)
    def upload_restore(
        archive: UploadFile = File(...), expected_run_id: str = Query(..., min_length=1)
    ):
        store = require_store()
        with lock, manager.lease() as context:
            require_current(context, expected_run_id)
            try:
                with tempfile.TemporaryDirectory(prefix="hardwise-restore-upload-") as tmp:
                    uploaded = Path(tmp) / "uploaded.zip"
                    size = 0
                    with uploaded.open("xb") as stream:
                        while block := archive.file.read(1024 * 1024):
                            size += len(block)
                            if size > MAX_UPLOAD:
                                raise HTTPException(413, "Backup upload exceeds supported size")
                            stream.write(block)
                    identifier = uuid4().hex
                    root = store.journal.path.with_name(store.journal.path.name + ".restored")
                    result = restore_projects(uploaded, root / identifier)
                    try:
                        receipt = _receipt(result, identifier)
                        # Keep instructions after the browser notification closes.
                        (Path(result["journal"]).parent / "restore-info.json").write_text(
                            receipt.model_dump_json(indent=2), encoding="utf-8"
                        )
                    except Exception:
                        shutil.rmtree(root / identifier)
                        raise
                    return receipt
            except HTTPException:
                raise
            except (OSError, ValueError, KeyError, sqlite3.Error, zipfile.BadZipFile) as exc:
                raise HTTPException(422, f"Backup could not be restored: {exc}") from exc
