"""Build a pinned Git-source validation capsule with no local environment or reports."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import zipfile

BASELINE_COMMIT = "aeb45f90e6b455e43c6584f1cfcac81874d61e7a"

BASELINE = {
    "component_summary": {
        "components": 25,
        "bom_matched": 25,
        "validated": 22,
        "manual": 3,
        "pass_count": 0,
        "warn_count": 0,
        "error_count": 0,
        "unknown_count": 22,
        "not_applicable_count": 0,
    },
    "assessment_coverage": {
        "rule_set_version": "hardwise.assessment.v1",
        "basis": "emitted_check_records",
        "generated_checks": 167,
        "completed_checks": 52,
        "unknown_checks": 115,
        "not_applicable_checks": 0,
        "legacy_needs_review": 0,
        "needs_review_checks": 91,
        "result_counts": {"PASS": 52, "FAIL": 0, "UNKNOWN": 115, "NOT_APPLICABLE": 0},
        "unsupported_components": 3,
        "full_candidate_count": None,
        "boundary": "只统计已生成的检查记录；尚未建立全板候选检查集合，不代表全板覆盖率。",
    },
}


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default=BASELINE_COMMIT)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    commit = (
        git(root, "rev-parse", "--verify", "--end-of-options", args.ref + "^{commit}")
        .decode()
        .strip()
    )
    if commit != BASELINE_COMMIT:
        raise ValueError("This v1 capsule requires the recorded baseline commit; rebaseline first")
    archive = zipfile.ZipFile(io.BytesIO(git(root, "archive", "--format=zip", commit)))
    files = {item.filename: archive.read(item) for item in archive.infolist() if not item.is_dir()}
    for name in files:
        parts = PurePosixPath(name).parts
        if PurePosixPath(name).is_absolute() or ".." in parts:
            raise ValueError("Git archive contains a non-relative path")
        if any(part in {".git", ".venv", "__pycache__"} for part in parts):
            raise ValueError(f"Non-source tree content is tracked: {name}")
        if (
            PurePosixPath(name).name.startswith(".env")
            and PurePosixPath(name).name != ".env.example"
        ):
            raise ValueError(f"Local environment must not be bundled: {name}")
    files["VALIDATE.py"] = (root / "scripts/validate_source_bundle.py").read_bytes()
    files["BUNDLE-REVIEW.py"] = (root / "scripts/validate_bundle_review.py").read_bytes()
    files["PUBLIC-BASELINE.json"] = (
        json.dumps(
            dict(
                source="Recorded software regression baseline; not independent engineering labels",
                recorded_at_commit=BASELINE_COMMIT,
                observed_software_baseline=BASELINE,
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode()
    guide = f"""# Windows公开复验包

源码固定在 `{commit}`。完整跟踪源码来自 git archive；另附 VALIDATE.py、BUNDLE-REVIEW.py、PUBLIC-BASELINE.json、本说明及清单。未附本机.venv、.env、用户上传文件、生成报告或完整厂商PDF。

## PowerShell执行

先确认uv可用（`uv --version`），进入解压后的根目录。首次安装依赖需要网络；这不是离线依赖安装包。

```powershell
uv sync --locked --extra dev
uv run python VALIDATE.py --require-windows
```

查看 reports 新生成的 JSON 和白色 HTML。源码校验、固定合成样例、白色离线渲染、无key真实模式dry-run，以及公开样例的明确人工状态/保存/离线历史/备份恢复自动流程可在此检查；结果里的 passed 仅指这些软件检查。非Windows运行 --require-windows 必须失败，不能替代目标机证据。报告不含完整环境变量，校验过程不读取.env或调用真实模型。

自动流程中的“人工决定”是合成测试操作，不是人的工程批准；仍需你在Windows实际浏览器走完以下流程并留记录。

随后实际打开工作台：

```powershell
uv run hardwise serve-workbench tests/fixtures/allegro/mixed_controller_power_stage.net tests/fixtures/allegro/mixed_controller_power_stage_bom.csv --review-db reports/windows-public-review.sqlite --no-auto-datasheet-candidates --port 8765
```

浏览器打开 http://127.0.0.1:8765/ 。无API key也可完成基本评审；提问会提示AI不可用。若端口被占用，请明确选择其他本机空闲端口并记录。无需更改执行策略或输入模型密钥。

1. 导入一个公开/合成样例；解释一项UNKNOWN的缺失前提。
2. 在“问题清单”为一项填写真实观察理由，选择接受风险/误报/已解决；记录机器结果没有被人工状态改写。
3. 在“导入”页保存当前项目，记下受管理项目ID。下载项目备份ZIP；仅SQLite日志不足以恢复原输入。
4. 停止服务，使用本包的实际项目ID重开。下行会提示输入页面记录的ID：

```powershell
$savedProjectId = Read-Host "输入页面记录的项目ID"
uv run hardwise serve-workbench --review-db reports/windows-public-review.sqlite --open-project $savedProjectId --no-auto-datasheet-candidates --port 8765
```

5. 核对原理由、历史和机器结果；导出离线报告。关闭服务并断网打开报告，查看历史、缺失原文及对应运行清单。
6. 在“导入”页上传备份ZIP恢复到新目录，按页面给出的PowerShell命令启动独立副本，核对原项目保持原样。
7. 使用真实Cadence导出的公开/合成输入重复导入/复查，记录实际EDA版本、菜单/命令、文件组及失败定位。


## 人工记录（保持空白直到真实观察）

- Windows版本/机器、uv/Python版本：
- 安装命令退出码、用时、失败环节：
- 白色页面打开与导入/处理未知/保存/重启/导出实际结果：
- 同一固定来源重启后的原理由是否保留：
- 离线HTML关闭服务后是否可读，缺失原文是否能辨认：
- Capture/OrCAD/Allegro版本与真实导出菜单/命令：
- 公开或合成EDA设计来源、完整文件组、编码、层级/引脚/BOM列情况：
- 从EDA实际导出到导入的结果及失败定位：

当前仓库自带样例为公开/合成回归输入，不证明某个真实Cadence版本已走通。仅使用公开或合成数据，不提供公司内部资料。JSON保留 actual_cadence_export_verified、human_profile_approval 为未取得，product_release_accepted 为false。人工档案审批、独立标签、真实EDA流程及两轮同行试用仍需各自证据。本版本源码包含受管理项目保存/打开与完整备份恢复，复验包ZIP本身是源码工具包，不是你已有项目的备份。外链PDF不会自动随报告或项目包再分发。源码完整性hash不是工程正确性认证。
"""
    files["START-HERE.md"] = guide.encode()
    manifest = dict(
        schema_version="hardwise.source_validation_bundle.v1",
        source_commit=commit,
        created_at=datetime.now(timezone.utc).isoformat(),
        supplemental_files=[
            "VALIDATE.py",
            "BUNDLE-REVIEW.py",
            "PUBLIC-BASELINE.json",
            "START-HERE.md",
        ],
        files={
            name: hashlib.sha256(content).hexdigest() for name, content in sorted(files.items())
        },
        scope="Public Git-source validation capsule; not a project archive or release approval",
    )
    files["BUNDLE-MANIFEST.json"] = (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    prefix = "hardwise-check-" + commit[:12] + "/"
    with zipfile.ZipFile(args.output, "x", compression=zipfile.ZIP_DEFLATED) as output:
        for name, content in sorted(files.items()):
            output.writestr(prefix + name, content)
    print(
        json.dumps(
            dict(
                archive=str(args.output),
                source_commit=commit,
                files=len(files),
                bytes=args.output.stat().st_size,
                sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(),
            ),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
