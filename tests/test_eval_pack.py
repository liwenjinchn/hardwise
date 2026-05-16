from pathlib import Path

import yaml

from hardwise.eval_pack import load_manifest, run_eval


def test_load_eval_manifest() -> None:
    manifest = load_manifest(Path("eval/manifest.yaml"))
    assert manifest.name == "hardwise-eval-pack-v0"
    assert manifest.rules == ["R001", "R002", "R003"]
    assert manifest.repos
    assert manifest.upstream["trust_boundary"].startswith("public regression oracle")


def test_run_eval_against_local_project(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "name": "test-eval",
                "rules": ["R001", "R002", "R003"],
                "repos": [
                    {
                        "name": "local/pic_programmer",
                        "url": "https://example.invalid/local/pic_programmer",
                        "commit": "0" * 40,
                        "project_dirs": ["."],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    projects_root = tmp_path / "projects"
    checkout = projects_root / "local__pic_programmer"
    checkout.parent.mkdir(parents=True)
    checkout.symlink_to(Path.cwd() / "data/projects/pic_programmer", target_is_directory=True)

    outputs = run_eval(
        manifest_path=manifest_path,
        projects_root=projects_root,
        output_dir=tmp_path / "reports",
    )

    assert outputs.summary.projects_total == 1
    assert outputs.summary.projects_passed == 1
    assert outputs.summary.findings_by_rule["R002"] == 7
    assert "R003" in outputs.summary.findings_by_rule
    assert outputs.summary.unverified_refdes_wrapped == 0
    assert outputs.summary_path.exists()
    assert outputs.html_path.exists()
