"""Edit verified profile copies; never overwrite the user's original sources."""

import hashlib
from pathlib import Path
import shutil
import tempfile

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.profile_review import digest
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.decision_fingerprints import review_project_key
from hardwise.workbench.managed_projects import _relative


def profile_files(context):
    root = Path(context.candidate_report.profiles_dir).absolute()
    profiles = {}
    for source in context.input_manifest.files:
        path = Path(source.path)
        if path.parent != root or path.suffix != ".json":
            continue
        data = path.read_bytes()
        if (
            str(path.resolve()) != source.resolved_path
            or hashlib.sha256(data).hexdigest() != source.sha256
        ):
            raise ValueError("Profile source changed; reload before editing")
        profiles[path.name] = (path, DatasheetProfile.model_validate_json(data))
    return profiles


def profiles_revision(profiles):
    return digest(
        {name: profile.model_dump(mode="json") for name, (_, profile) in profiles.items()}
    )


def stage_excerpt(store, current, name, updated):
    previous, descriptor = store.prepare(current)
    manifest = store.inputs.load(previous)
    directory = Path(tempfile.mkdtemp(prefix="hardwise-excerpt-edit-"))
    candidate = None
    try:
        for entry in manifest["entries"]:
            path = directory / _relative(descriptor["sources"][entry["path"]])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((store.inputs.root / previous / entry["member"]).read_bytes())
        arguments = {
            k: directory / _relative(v) if v else None for k, v in descriptor["arguments"].items()
        }
        # name is selected from the captured profile inventory, never a client path.
        target = arguments["profiles"] / name
        if not target.is_file():
            raise ValueError("Selected profile missing from captured input")
        updated.save(target)
        candidate = build_workbench_context(**arguments)
        candidate.managed_project_key = review_project_key(current)
        candidate.managed_project_id = current.managed_project_id
        return candidate, directory, store.prepare(candidate), previous
    except Exception:
        if candidate is not None:
            close_workbench_context(candidate)
        shutil.rmtree(directory)
        raise
