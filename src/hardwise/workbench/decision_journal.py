"""Transactional local reviewer journal; electrical assessments are never rewritten."""

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3


class ReviewConflictError(ValueError):
    """The caller no longer owns the current reviewed run/revision."""


class DecisionJournal:
    """One versioned SQLite file can retain multiple source-anchored projects."""

    def __init__(self, path: Path):
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            tables = {
                r[0]
                for r in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            }
            expected = {"review_state", "review_events", "review_runs", "review_heads"}
            if version not in (0, 1) or (tables and tables != expected):
                raise ValueError(
                    "unsupported review journal; preserve the file and select another path"
                )
            db.execute(
                "CREATE TABLE IF NOT EXISTS review_state(project TEXT, stable_key TEXT, data TEXT NOT NULL, PRIMARY KEY(project,stable_key))"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS review_events(id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT, run_id TEXT, data TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS review_runs(run_id TEXT PRIMARY KEY, project TEXT, data TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS review_heads(project TEXT PRIMARY KEY, revision INTEGER NOT NULL)"
            )
            db.execute("PRAGMA user_version=1")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA synchronous=FULL")
        try:
            with db:
                yield db
        finally:
            db.close()

    def load(self, project: str) -> tuple[dict[str, dict], int]:
        with self.connect() as db:
            db.execute("BEGIN")
            revision = db.execute(
                "SELECT revision FROM review_heads WHERE project=?", (project,)
            ).fetchone()
            items = {
                key: json.loads(data)
                for key, data in db.execute(
                    "SELECT stable_key,data FROM review_state WHERE project=?", (project,)
                )
            }
            return items, revision[0] if revision else 0

    def save(
        self,
        project: str,
        run_id: str,
        items: dict[str, dict],
        events: list[dict],
        run: dict | None = None,
        expected_revision: int = 0,
    ):
        """State, history and a run snapshot commit together or roll back together."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT revision FROM review_heads WHERE project=?", (project,)
            ).fetchone()
            if (row[0] if row else 0) != expected_revision:
                raise ReviewConflictError(
                    "review journal changed in another process; restart before saving"
                )
            db.execute("DELETE FROM review_state WHERE project=?", (project,))
            db.executemany(
                "INSERT INTO review_state VALUES(?,?,?)",
                [(project, k, json.dumps(v, ensure_ascii=False)) for k, v in items.items()],
            )
            db.executemany(
                "INSERT INTO review_events(project,run_id,data) VALUES(?,?,?)",
                [(project, run_id, json.dumps(e, ensure_ascii=False)) for e in events],
            )
            if run is not None:
                db.execute(
                    "INSERT INTO review_runs VALUES(?,?,?)",
                    (run_id, project, json.dumps(run, ensure_ascii=False)),
                )
            db.execute(
                "INSERT INTO review_heads VALUES(?,?) ON CONFLICT(project) DO UPDATE SET revision=excluded.revision",
                (project, expected_revision + 1),
            )
        return expected_revision + 1

    def history(self, project: str, limit: int = 100, offset: int = 0) -> list[dict]:
        with self.connect() as db:
            return [
                dict(id=seq, run_id=run_id, **json.loads(data))
                for seq, run_id, data in db.execute(
                    "SELECT id,run_id,data FROM review_events WHERE project=? ORDER BY id DESC LIMIT ? OFFSET ?",
                    (project, limit, offset),
                )
            ]

    def history_count(self, project: str) -> int:
        with self.connect() as db:
            return db.execute(
                "SELECT count(*) FROM review_events WHERE project=?", (project,)
            ).fetchone()[0]
