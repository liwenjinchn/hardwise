"""Validate a pinned public source bundle; this is not product release approval."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import runpy
import subprocess
import sys
from uuid import uuid4


def verify_files(root, manifest):
    for name, expected in manifest["files"].items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Manifest contains a non-relative source path")
        path = root.joinpath(*relative.parts)
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            raise ValueError(f"Missing or unsupported source file: {name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Source hash mismatch: {name}")
    return len(manifest["files"])


def candidate_baseline(snapshot):
    outcomes = {o.candidate_id: o.result for o in snapshot.outcomes}
    rows = sorted(
        (c.candidate_id, c.applicability, outcomes.get(c.candidate_id)) for c in snapshot.candidates
    )
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    return dict(
        catalog_version=snapshot.catalog.version,
        counts=snapshot.counts(),
        identity_state_sha256=hashlib.sha256(payload.encode()).hexdigest(),
    )


def probe(root, result, prefix):
    # Configuration isolation applies to this check process and its child only.
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "DATASHEETS_API_KEY"):
        os.environ.pop(name, None)
    sys.path.insert(0, str(root / "src"))
    from hardwise.workbench.context import build_workbench_context, close_workbench_context
    from hardwise.workbench.view_model import build_workbench_state
    from hardwise.report.workbench_spa_snapshot import render_spa_snapshot

    module = Path(sys.modules[build_workbench_context.__module__].__file__).resolve()
    if not module.is_relative_to(root / "src"):
        raise ValueError("Backend was imported from outside the extracted bundle")
    result["loaded_context"] = str(module)
    expected = json.loads((root / "PUBLIC-BASELINE.json").read_text(encoding="utf-8"))
    netlist = root / "tests/fixtures/allegro/mixed_controller_power_stage.net"
    bom = root / "tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"
    profiles = root / "data/datasheet_profiles"
    context = build_workbench_context(netlist_path=netlist, bom_path=bom, profiles=profiles)
    try:
        state = build_workbench_state(context, datasheet_search_enabled=False)
        observed = dict(
            component_summary=state.summary.model_dump(mode="json"),
            assessment_coverage=state.assessment_coverage.model_dump(mode="json"),
            candidate_coverage=candidate_baseline(context.index.candidate_coverage),
        )
        if state.candidate_coverage.counts.model_dump() != observed["candidate_coverage"]["counts"]:
            raise ValueError("Candidate summary differs from its recorded snapshot")
        if observed != expected["observed_software_baseline"]:
            raise ValueError(
                "Public-fixture counts/coverage differ from the pinned software baseline"
            )
        html = render_spa_snapshot(context)
        html_path = prefix.with_suffix(".html")
        html_path.write_text(html, encoding="utf-8")
        result.update(
            public_baseline=observed,
            white_report=str(html_path),
            white_report_sha256=hashlib.sha256(html.encode()).hexdigest(),
        )
    finally:
        close_workbench_context(context)
    env = dict(os.environ, PYTHONPATH=str(root / "src"), PYTHONUTF8="1")
    command = [
        sys.executable,
        "-c",
        "from hardwise.cli import app; app()",
        "serve-workbench",
        str(netlist),
        str(bom),
        "--profiles",
        str(profiles),
        "--no-auto-datasheet-candidates",
        "--dry-run",
    ]
    completed = subprocess.run(
        command, cwd=root, env=env, capture_output=True, encoding="utf-8", timeout=60, check=False
    )
    result["real_no_key_cli"] = dict(
        exit_code=completed.returncode, output=completed.stdout, stderr=completed.stderr
    )
    if completed.returncode or "mode=real" not in completed.stdout:
        raise ValueError("Real-mode no-key CLI startup check failed")
    helper = runpy.run_path(str(root / "BUNDLE-REVIEW.py"))
    result["public_review_workflow"] = helper["probe"](root, prefix)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--hash-only", action="store_true")
    parser.add_argument("--require-windows", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    output = (
        root
        / "reports"
        / (
            "bundle-check-"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            + "-"
            + uuid4().hex[:8]
        )
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    result = dict(
        schema_version="hardwise.source_bundle_check.v1",
        source_commit=None,
        checked_at=datetime.now(timezone.utc).isoformat(),
        platform=platform.platform(),
        python=platform.python_version(),
        hash_only=args.hash_only,
        passed=False,
        windows_software_probe_passed=False,
        actual_cadence_export_verified=None,
        human_profile_approval=None,
        product_release_accepted=False,
    )
    try:
        manifest = json.loads((root / "BUNDLE-MANIFEST.json").read_text(encoding="utf-8"))
        result["source_commit"] = manifest["source_commit"]
        result["verified_files"] = verify_files(root, manifest)
        if args.require_windows and platform.system() != "Windows":
            raise ValueError("This check requires native Windows; this host is not Windows")
        if not args.hash_only:
            probe(root, result, output)
        result["passed"] = True
        result["windows_software_probe_passed"] = (
            platform.system() == "Windows" and not args.hash_only
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    report = output.with_suffix(".json")
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            dict(
                report=str(report),
                passed=result["passed"],
                windows_software_probe_passed=result["windows_software_probe_passed"],
                product_release_accepted=False,
            ),
            ensure_ascii=False,
        )
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
