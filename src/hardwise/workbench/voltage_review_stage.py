"""Build immutable edited input copies without overwriting reviewer sources."""

from pathlib import Path
import shutil
import tempfile
from uuid import uuid4

from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.decision_fingerprints import review_project_key
from hardwise.workbench.managed_projects import _relative


def stage_voltage_review(store, current, review):
    """Retain original source snapshot and build a fully captured new context."""
    previous_snapshot, descriptor = store.prepare(current)
    manifest = store.inputs.load(previous_snapshot)
    directory = Path(tempfile.mkdtemp(prefix="hardwise-voltage-edit-"))
    candidate = None
    try:
        for entry in manifest["entries"]:
            path = directory / _relative(descriptor["sources"][entry["path"]])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((store.inputs.root / previous_snapshot / entry["member"]).read_bytes())
        arguments = {
            key: directory / _relative(value) if value else None
            for key, value in descriptor["arguments"].items()
        }
        arguments["profiles"].mkdir(parents=True, exist_ok=True)
        ledger_path = directory / (".voltage-review-" + uuid4().hex + ".json")
        ledger_path.write_text(review.model_dump_json(), encoding="utf-8")
        arguments["voltage_facts"] = ledger_path
        candidate = build_workbench_context(**arguments)
        candidate.managed_project_key = review_project_key(current)
        candidate.managed_project_id = current.managed_project_id
        prepared = store.prepare(candidate)
        return candidate, directory, prepared, previous_snapshot
    except Exception:
        if candidate is not None:
            close_workbench_context(candidate)
        shutil.rmtree(directory)
        raise
