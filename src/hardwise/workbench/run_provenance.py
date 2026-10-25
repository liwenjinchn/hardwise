"""Run evidence: captured input hashes, loaded profile models and emitted rule versions."""

from collections import Counter
from importlib.metadata import PackageNotFoundError, version
import hashlib
import json
import math
import platform
from typing import Any, Literal

from pydantic import BaseModel
from hardwise.input_provenance import InputReadManifest


class ProfileModelSnapshot(BaseModel):
    sha256: str
    part_number: str
    review_status: str
    values: dict[str, Any]


class EmittedRuleVersion(BaseModel):
    scope: Literal["pin", "component", "net"]
    name: str
    version: str
    emitted_count: int


class RunProvenance(BaseModel):
    schema_version: Literal["hardwise.run_provenance.v1"] = "hardwise.run_provenance.v1"
    raw_inputs_archived: Literal[False] = False
    review_dependency_contract: str | None = None
    input_capture_status: Literal["captured", "unavailable"]
    inputs: InputReadManifest | None
    package_version: str
    python_version: str
    implementation_identity_assurance: Literal["declared_rule_versions"] = "declared_rule_versions"
    profile_snapshot_encoding: Literal["json_with_nonfinite_float_tags"] = (
        "json_with_nonfinite_float_tags"
    )
    profiles: list[ProfileModelSnapshot]
    profile_bindings: dict[str, str]
    rule_versions: list[EmittedRuleVersion]
    emitted_records: int


class RunProvenanceResponse(BaseModel):
    project_id: str
    run_id: str
    created_at: str | None
    status: Literal["recorded", "not_recorded"]
    reason: str
    provenance: RunProvenance | None


def _snapshot(value):
    if isinstance(value, float) and not math.isfinite(value):
        return {"hardwise_nonfinite_float": repr(value)}
    if isinstance(value, dict):
        return {key: _snapshot(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_snapshot(item) for item in value]
    return value


def build_run_provenance(context) -> RunProvenance:
    snapshots, bindings = {}, {}
    for refdes, profile in sorted(context.validation_targets.items()):
        values = _snapshot(profile.model_dump(mode="json"))
        serialized = json.dumps(
            values, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        sha = hashlib.sha256(serialized.encode()).hexdigest()
        bindings[refdes] = sha
        snapshots[sha] = ProfileModelSnapshot(
            sha256=sha,
            part_number=profile.part_number,
            review_status=profile.review_status,
            values=values,
        )
    rules = Counter()
    for row in context.index.validated_rows:
        for pin in row.validation.pin_results:
            rules[("pin", pin.category, pin.rule_version)] += 1
        for check in row.validation.component_checks:
            rules[("component", check.check, check.rule_version)] += 1
    for check in context.index.net_checks:
        rules[("net", check.check, check.rule_version)] += 1
    try:
        package_version = version("hardwise")
    except PackageNotFoundError:
        package_version = "uninstalled_source_tree"
    from hardwise.workbench.decision_fingerprints import REVIEW_DEPENDENCY_CONTRACT

    return RunProvenance(
        review_dependency_contract=REVIEW_DEPENDENCY_CONTRACT,
        input_capture_status="captured" if context.input_manifest is not None else "unavailable",
        inputs=context.input_manifest,
        package_version=package_version,
        python_version=platform.python_version(),
        profiles=[snapshots[key] for key in sorted(snapshots)],
        profile_bindings=bindings,
        rule_versions=[
            EmittedRuleVersion(
                scope=scope, name=name, version=producer_version, emitted_count=count
            )
            for (scope, name, producer_version), count in sorted(rules.items())
        ],
        emitted_records=sum(rules.values()),
    )


def load_run_provenance(journal, memory_runs, project, run_id):
    data = journal.run_data(project, run_id) if journal else memory_runs.get(run_id)
    if data is None or (not journal and data["project"] != project):
        raise KeyError(run_id)
    payload = data.get("provenance")
    return dict(
        project_id=project,
        run_id=run_id,
        created_at=data.get("created_at"),
        status="recorded" if payload is not None else "not_recorded",
        reason="Run provenance recorded; original input files are not archived."
        if payload is not None
        else "This run did not record provenance; no hashes were reconstructed from current files.",
        provenance=payload,
    )
