"""Saved project catalog exposed to the existing white workbench."""

from pydantic import BaseModel


class SavedProjectView(BaseModel):
    id: str
    project_id: str
    snapshot: str
    name: str


class SavedProjectCatalog(BaseModel):
    projects: list[SavedProjectView]


class RestoredProjectLaunch(BaseModel):
    saved_id: str
    command_posix: str
    command_powershell: str


class ProjectRestoreReceipt(BaseModel):
    restore_id: str
    journal: str
    saved_project_ids: list[str]
    source_unowned_project_ids: list[str]
    launches: list[RestoredProjectLaunch]
