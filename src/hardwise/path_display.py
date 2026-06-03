"""Display helpers for paths in portable text artifacts."""

from __future__ import annotations

from pathlib import Path


def display_path(path: Path | str | None) -> str | None:
    """Render paths with POSIX separators for CLI/report text, not filesystem I/O."""

    if path is None:
        return None
    if isinstance(path, Path):
        return path.as_posix()
    return path.replace("\\", "/")
