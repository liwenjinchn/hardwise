"""Bounded public-fixture performance probe; no network or product acceptance gate."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
import time

CASES = ("l78_regulator", "mixed_controller_power_stage", "motor_sensor_controller")


def _worker(args):
    started = time.perf_counter()
    from hardwise.workbench.context import build_workbench_context, close_workbench_context
    from hardwise.workbench.view_model import build_workbench_state
    from hardwise.report.workbench_spa_snapshot import render_spa_snapshot

    imports_s = time.perf_counter() - started
    loaded_context = Path(sys.modules[build_workbench_context.__module__].__file__).resolve()
    if not loaded_context.is_relative_to(args.code_root / "src"):
        raise RuntimeError(f"Loaded context outside requested code root: {loaded_context}")
    root = args.inputs_root
    measurements = []
    for index in range(args.rebuilds + 1):
        context = None
        try:
            started = time.perf_counter()
            context = build_workbench_context(
                netlist_path=root / f"tests/fixtures/allegro/{args.worker}.net",
                bom_path=root / f"tests/fixtures/allegro/{args.worker}_bom.csv",
                profiles=root / "data/datasheet_profiles",
            )
            built = time.perf_counter()
            state = build_workbench_state(context, datasheet_search_enabled=False)
            projected = time.perf_counter()
            html = render_spa_snapshot(context)
            rendered = time.perf_counter()
            signature = {
                "components": len(context.design.components),
                "report_bearing": len(context.index.validated_rows),
                "component_results": context.index.totals,
                "emitted_checks": context.index.assessment_coverage.generated_checks,
                "tasks": len(state.review_tasks),
            }
            measurements.append(
                dict(
                    iteration=index,
                    phase="first_build" if index == 0 else "in_process_rebuild",
                    build_s=built - started,
                    projection_s=projected - built,
                    snapshot_s=rendered - projected,
                    total_s=rendered - started,
                    snapshot_bytes=len(html.encode()),
                    signature=signature,
                    process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                    * (1 if sys.platform == "darwin" else 1024),
                )
            )
        finally:
            if context is not None:
                close_workbench_context(context)
            gc.collect()
    if any(item["signature"] != measurements[0]["signature"] for item in measurements):
        raise RuntimeError("Repeated builds produced different workload/result counts")
    return dict(imports_s=imports_s, loaded_context=str(loaded_context), measurements=measurements)


def _input_hashes(root):
    paths = [
        root / f"tests/fixtures/allegro/{case}{suffix}"
        for case in CASES
        for suffix in (".net", "_bom.csv")
    ]
    paths += sorted((root / "data/datasheet_profiles").glob("*.json"))
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths
    }


def _distribution(values):
    return (
        dict(
            count=len(values),
            minimum=min(values),
            median=statistics.median(values),
            maximum=max(values),
        )
        if values
        else None
    )


def _hardware_value(name):
    if sys.platform != "darwin":
        return None
    result = subprocess.run(["sysctl", "-n", name], capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def _run(args):
    root = args.inputs_root
    original_inputs = _input_hashes(root)
    results = []
    for case in CASES:
        launches = []
        for launch in range(args.processes):
            env = dict(os.environ, PYTHONPATH=str(args.code_root / "src"))
            started = time.perf_counter()
            process = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--worker",
                    case,
                    "--inputs-root",
                    str(root),
                    "--code-root",
                    str(args.code_root),
                    "--rebuilds",
                    str(args.rebuilds),
                ],
                cwd=args.code_root,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            elapsed = time.perf_counter() - started
            item = dict(launch=launch, process_wall_s=elapsed, exit_code=process.returncode)
            if process.returncode:
                item["error"] = process.stderr[-4000:]
            else:
                item["data"] = json.loads(process.stdout)
            launches.append(item)
        successful = [run["data"] for run in launches if "data" in run]
        first = [run["measurements"][0]["total_s"] for run in successful]
        warm = [m["total_s"] for run in successful for m in run["measurements"][1:]]
        signatures = [m["signature"] for run in successful for m in run["measurements"]]
        if signatures and any(signature != signatures[0] for signature in signatures):
            raise RuntimeError(f"{case}: fresh processes produced different workload counts")
        results.append(
            dict(
                case=case,
                launches=launches,
                failed_processes=len(launches) - len(successful),
                first_build_s=_distribution(first),
                rebuild_s=_distribution(warm),
            )
        )
    if _input_hashes(root) != original_inputs:
        raise RuntimeError("Benchmark inputs changed during measurement; discard this run")
    report = dict(
        schema_version="hardwise.public_performance_probe.v1",
        code_revision=args.revision,
        captured_at=datetime.now(timezone.utc).isoformat(),
        machine=dict(
            system=platform.system(),
            release=platform.release(),
            machine=platform.machine(),
            logical_cpus=os.cpu_count(),
            cpu=_hardware_value("machdep.cpu.brand_string"),
            physical_memory_bytes=_hardware_value("hw.memsize"),
            python=platform.python_version(),
            executable=sys.executable,
        ),
        input_hashes=original_inputs,
        cases=results,
        boundaries=[
            "Public/synthetic fixed fixtures; no live model, network, vector search or real EDA run.",
            "First build means fresh Python process; filesystem/OS caches were not flushed.",
            "Rebuilds reconstruct context then project and render; they are not cached HTTP reads.",
            "Process wall includes imports, all rebuilds and cleanup; phase totals exclude cleanup.",
            "RSS is process lifetime high-water mark, not per-build memory or a leak measurement.",
            "Small local sample; no arbitrary large-board latency or Windows acceptance claim.",
        ],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return any(case["failed_processes"] for case in results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--inputs-root", type=Path)
    parser.add_argument("--revision", default="unverified_working_tree")
    parser.add_argument("--processes", type=int, default=3, choices=range(1, 11))
    parser.add_argument("--rebuilds", type=int, default=5, choices=range(0, 21))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", choices=CASES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.code_root = args.code_root.resolve()
    args.inputs_root = (args.inputs_root or args.code_root).resolve()
    if args.worker:
        print(json.dumps(_worker(args)))
        return 0
    if args.output is None:
        parser.error("--output is required")
    return int(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
