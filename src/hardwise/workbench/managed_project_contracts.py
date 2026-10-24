"""Saved project catalog exposed to the existing white workbench."""

from pydantic import BaseModel


class SavedProjectView(BaseModel):
    id: str
    project_id: str
    snapshot: str
    name: str


class SavedProjectCatalog(BaseModel):
    projects: list[SavedProjectView]
