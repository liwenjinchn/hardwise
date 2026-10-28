"""Real-engine CLI/API/report contracts, including untrusted upload boundaries."""

import base64
import hashlib
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys
import threading

from fastapi.testclient import TestClient
import pytest
from typer.testing import CliRunner

from hardwise.cli import app
from hardwise.revision import demo, engine, server
from hardwise.revision.models import ComparisonResult, SourceEvidence
from hardwise.revision.report import render_comparison_html

CONTENTS = (demo.BEFORE_NETLIST, demo.BEFORE_BOM, demo.AFTER_NETLIST, demo.AFTER_BOM)
ROOT = Path(__file__).resolve().parents[2]


def uploads():
    return [
        (role, ("same.net" if role.endswith("netlist") else "same.csv", content.encode()))
        for role, content in zip(server.ROLES, CONTENTS, strict=True)
    ]


@pytest.fixture
def paths(tmp_path):
    result = []
    for role, (name, content) in uploads():
        directory = tmp_path / role
        directory.mkdir()
        path = directory / name
        path.write_bytes(content)
        result.append(path)
    return result


@pytest.fixture
def tracked_temporary_files(monkeypatch, tmp_path):
    import starlette.formparsers

    directories, spools = [], []
    original_directory = server.TemporaryDirectory
    original_spool = starlette.formparsers.SpooledTemporaryFile

    def directory(**kwargs):
        temporary = original_directory(dir=tmp_path, **kwargs)
        directories.append(Path(temporary.name))
        return temporary

    def spool(**kwargs):
        stream = original_spool(**kwargs)
        spools.append(stream)
        return stream

    monkeypatch.setattr(server, "TemporaryDirectory", directory)
    monkeypatch.setattr(demo, "TemporaryDirectory", directory)
    monkeypatch.setattr(starlette.formparsers, "SpooledTemporaryFile", spool)
    yield directories, spools
    assert all(not path.exists() for path in directories)
    assert all(stream.closed for stream in spools)


def invoke(paths, *args):
    return CliRunner().invoke(app, ["compare", *map(str, paths), *map(str, args)])


def test_cli_actual_comparison_and_json(paths, tmp_path):
    output, json_output = tmp_path / "comparison.html", tmp_path / "comparison.json"
    response = invoke(paths, "--output", output, "--json-output", json_output)
    assert response.exit_code == 0, response.output
    expected = engine.compare_files(*paths)
    assert ComparisonResult.model_validate_json(json_output.read_text()) == expected
    assert output.read_text() == render_comparison_html(expected)
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(
        [*server.ROLES, output.name, json_output.name]
    )


@pytest.mark.parametrize("case", ["input", "exists", "parent", "same", "symlink", "hardlink"])
def test_cli_refuses_overwrite_and_invalid_destinations(paths, tmp_path, case):
    output, json_output = tmp_path / "report.html", tmp_path / "report.json"
    if case == "input":
        json_output = paths[0]
    elif case == "exists":
        json_output.write_text("keep me")
    elif case == "parent":
        json_output = tmp_path / "missing" / "report.json"
    elif case == "same":
        json_output = output
    elif case == "symlink":
        json_output.symlink_to(paths[0])
    elif case == "hardlink":
        json_output.hardlink_to(paths[0])
    before = {path: path.read_bytes() for path in paths}
    response = invoke(paths, "--output", output, "--json-output", json_output)
    assert response.exit_code != 0
    assert "error:" in response.output
    assert not output.exists()
    assert all(path.read_bytes() == content for path, content in before.items())
    assert not (tmp_path / "missing").exists()
    if case == "exists":
        assert json_output.read_text() == "keep me"


def test_cli_requires_output_and_rejects_bad_input_without_artifacts(paths, tmp_path):
    assert invoke(paths).exit_code != 0
    output = tmp_path / "report.html"
    paths[2].write_text("not a Telesis file")
    response = invoke(paths, "--output", output)
    assert response.exit_code != 0 and "error:" in response.output
    assert not output.exists()
    paths[2].write_text("")
    assert "为空" in invoke(paths, "--output", output).output
    paths[2] = tmp_path / "unsupported.dsn"
    paths[2].write_text("not supported")
    assert "格式" in invoke(paths, "--output", output).output
    assert not output.exists()


def test_cli_exclusive_write_race_removes_only_its_outputs(paths, tmp_path, monkeypatch):
    output, json_output = tmp_path / "report.html", tmp_path / "report.json"
    original = Path.open

    def racing_open(path, mode="r", *args, **kwargs):
        if path == json_output and mode == "x":
            with original(path, "w") as stream:
                stream.write("created by another writer")
        return original(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", racing_open)
    assert invoke(paths, "--output", output, "--json-output", json_output).exit_code != 0
    assert not output.exists()
    assert json_output.read_text() == "created by another writer"


def test_help_prioritizes_compare_and_serve_binds_loopback(monkeypatch):
    import uvicorn
    import webbrowser

    help_text = CliRunner().invoke(app, ["--help"]).output
    commands = help_text[help_text.index("Commands") :]
    assert commands.index("compare") < commands.index("ask")
    calls, opened = [], []
    monkeypatch.setattr(uvicorn, "run", lambda application, **kwargs: calls.append(kwargs))
    monkeypatch.setattr(webbrowser, "open", opened.append)
    assert CliRunner().invoke(app, ["serve-compare"]).exit_code == 0
    assert calls == [{"host": "127.0.0.1", "port": 18774}] and not opened
    assert CliRunner().invoke(app, ["serve-compare", "--port", "18775", "--open"]).exit_code == 0
    assert calls[-1] == {"host": "127.0.0.1", "port": 18775}
    assert opened == ["http://127.0.0.1:18775/compare"]
    assert CliRunner().invoke(app, ["serve-compare", "--port", "0"]).exit_code != 0


def test_api_same_names_paths_threadpool_and_cleanup(monkeypatch, tracked_temporary_files):
    original = engine.compare_files
    observed = []

    def compare(*paths):
        assert [path.parent.name for path in paths] == list(server.ROLES)
        assert [path.name for path in paths] == ["same.net", "same.csv"] * 2
        assert len(set(paths)) == 4 and all(path.is_file() for path in paths)
        observed.append(threading.current_thread().name)
        return original(*paths)

    monkeypatch.setattr(engine, "compare_files", compare)
    files = uploads()
    files[0] = (files[0][0], ("../../same.net", files[0][1][1]))
    files[2] = (files[2][0], (r"C:\client\same.net", files[2][1][1]))
    application = server.create_compare_app()
    with TestClient(application) as client:
        response = client.post("/api/compare", files=files)
    assert response.status_code == 200, response.text
    result = ComparisonResult.model_validate(response.json())
    assert result.summary.added == result.summary.removed == result.summary.net_renames == 1
    for view, contents in ((result.before, CONTENTS[:2]), (result.after, CONTENTS[2:])):
        assert [source.sha256 for source in view.sources] == [
            hashlib.sha256(content.encode()).hexdigest() for content in contents
        ]
    assert observed and all("worker" in name.lower() for name in observed)
    assert not hasattr(application.state, "workbench_context")
    assert tracked_temporary_files[0]


@pytest.mark.parametrize(
    "case,status",
    [
        ("missing", 400),
        ("duplicate", 400),
        ("extra", 400),
        ("role", 400),
        ("empty", 400),
        ("blank", 400),
        ("format", 400),
        ("invalid", 422),
    ],
)
def test_api_upload_errors(case, status, tracked_temporary_files):
    files = uploads()
    if case == "missing":
        files.pop()
    elif case == "duplicate":
        files[1] = files[0]
    elif case == "extra":
        files.append(("extra", ("extra.net", b"extra")))
    elif case == "role":
        files[0] = ("../../before_netlist", files[0][1])
    else:
        name, content = files[0][1]
        name = "wrong.dsn" if case == "format" else name
        content = {"empty": b"", "blank": b" \n\t", "invalid": b"not a netlist"}.get(case, content)
        files[0] = (files[0][0], (name, content))
    with TestClient(server.create_compare_app()) as client:
        response = client.post("/api/compare", files=files)
    assert response.status_code == status, response.text
    assert response.json()["detail"]


def test_api_size_limit_and_client_paths_rejected(tracked_temporary_files):
    files = uploads()
    files[0] = (files[0][0], ("same.net", b"x" * (server.MAX_FILE_BYTES + 1)))
    with TestClient(server.create_compare_app()) as client:
        response = client.post("/api/compare", files=files)
        assert response.status_code == 413 and "10 MiB" in response.text
        assert (
            client.post("/api/compare", json={"before_netlist": "/tmp/input.net"}).status_code
            == 415
        )
        response = client.post("/api/compare", files=uploads(), data={"path": "/tmp/input.net"})
        assert response.status_code == 400
        assert (
            client.post(
                "/api/compare", files=[("before_netlist", (None, "/tmp/a.net"))]
            ).status_code
            == 400
        )


def test_api_truncated_upload_closes_spools(tracked_temporary_files):
    body = b'--cut\r\nContent-Disposition: form-data; name="before_netlist"; filename="a.net"\r\n\r\ndata'
    with TestClient(server.create_compare_app()) as client:
        response = client.post(
            "/api/compare",
            content=body,
            headers={"content-type": "multipart/form-data; boundary=cut"},
        )
    assert response.status_code == 400
    assert tracked_temporary_files[1]


@pytest.mark.parametrize(
    "error,status", [(ValueError("invalid source"), 422), (RuntimeError("boom"), 500)]
)
def test_engine_failure_cleans_all_inputs(error, status, monkeypatch, tracked_temporary_files):
    def fail(*paths):
        assert all(path.exists() for path in paths)
        raise error

    monkeypatch.setattr(engine, "compare_files", fail)
    with TestClient(server.create_compare_app(), raise_server_exceptions=False) as client:
        assert client.post("/api/compare", files=uploads()).status_code == status
    assert tracked_temporary_files[0]


def test_static_and_reproducible_real_demo(tracked_temporary_files):
    with TestClient(server.create_compare_app()) as client:
        assert client.get("/").content == (server.STATIC_DIR / "index.html").read_bytes()
        assert client.get("/compare").content == client.get("/").content
        for asset in (server.STATIC_DIR / "assets").iterdir():
            if asset.is_file():
                assert client.get("/assets/" + asset.name).content == asset.read_bytes()
        first = client.get("/api/compare/demo")
        assert first.status_code == 200
        assert first.json() == client.get("/api/compare/demo").json()
        assert first.json()["summary"]["attribute_changes"] > 0
        assert first.json()["electrical_verdict"] == "not_evaluated"


class ParsedHTML(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.downloads = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        assert not any(name.startswith("on") for name, _ in attrs)
        attrs = dict(attrs)
        if tag == "a":
            self.downloads.append(attrs["href"])


def test_report_escapes_all_source_text_and_roundtrips_json():
    result = demo.compare_demo_files()
    payload = '</script><script>alert("x")</script><img src=x onerror=alert(1)>'
    evidence = SourceEvidence(file=payload, sha256="a" * 64, locator=payload)
    change = result.changes[0].model_copy(
        update={
            "explanation": payload,
            "refdes": payload,
            "field": payload,
            "before": result.changes[0].before.model_copy(
                update={"values": (payload,), "evidence": (evidence,)}
            ),
        }
    )
    network = result.before.networks[0].model_copy(
        update={"name": payload, "evidence": (evidence,)}
    )
    result = result.model_copy(
        update={
            "comparison_id": payload,
            "changes": (change,),
            "before": result.before.model_copy(update={"networks": (network,)}),
        }
    )
    html = render_comparison_html(result)
    parsed = ParsedHTML(html)
    assert "script" not in parsed.tags and "img" not in parsed.tags
    assert payload not in html and escape(payload) in html
    assert len(parsed.downloads) == 1
    assert parsed.downloads[0].startswith("data:application/json;base64,")
    decoded = base64.b64decode(parsed.downloads[0].split(",", 1)[1])
    assert ComparisonResult.model_validate_json(decoded) == result
    for source in (*result.before.sources, *result.after.sources):
        assert source.sha256 in html
    assert "未知、冲突与比较边界" in html and "电气判定：not_evaluated" in html
    assert "安全" not in html and "全部正确" not in html


def test_report_retains_large_network_endpoints_once_per_side(paths):
    refs = [f"R{number}" for number in range(1, 76)]
    netlist = "$PACKAGES\n ! 'R0603' ! 'RES' ; " + ", ".join(refs)
    netlist += "\n$NETS\n 'GND' ; " + ", ".join(ref + ".1" for ref in refs) + "\n$END\n"
    bom = "RefDes,Value,Footprint\n" + "".join(f"{ref},10k,R0603\n" for ref in refs)
    for path in (paths[0], paths[2]):
        path.write_text(netlist)
    paths[1].write_text(bom)
    paths[3].write_text(bom.replace("R1,10k", "R1,4.7k"))
    result = engine.compare_files(*paths)
    change = result.changes[0]
    assert len(change.related_refdes) == 50 and change.related_count == 74
    html = render_comparison_html(result)
    assert html.count('<details class="network">') == 2
    assert html.count("<td>R75</td><td>1</td>") == 2
    assert "共 74 个" in html


def test_standalone_has_no_ai_store_or_workbench_imports(paths, tmp_path, monkeypatch):
    import os

    code = """
import builtins, sys
original = builtins.__import__
def guarded(name, *args, **kwargs):
    forbidden = ("anthropic", "hardwise.agent", "hardwise.store", "hardwise.workbench", "hardwise.validation")
    if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden):
        raise AssertionError("comparison imported " + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from hardwise.cli import app
from typer.testing import CliRunner
from fastapi.testclient import TestClient
from hardwise.revision.server import create_compare_app
response = CliRunner().invoke(app, ["compare", *sys.argv[1:5], "--output", sys.argv[5]])
assert response.exit_code == 0, (response.output, response.exception)
with TestClient(create_compare_app()) as client:
    response = client.get("/api/compare/demo")
    assert response.status_code == 200, response.text
"""
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), ANTHROPIC_API_KEY="")
    response = subprocess.run(
        [sys.executable, "-c", code, *map(str, paths), str(tmp_path / "report.html")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert response.returncode == 0, response.stdout + response.stderr


def test_old_workbench_state_is_unchanged_by_compare(paths):
    from hardwise.workbench.context import build_workbench_context
    from hardwise.workbench.server import create_workbench_app

    class NoChat:
        datasheet_search_enabled = False

    context = build_workbench_context(
        netlist_path=paths[0],
        bom_path=paths[1],
        profiles=ROOT / "data/datasheet_profiles",
    )
    application = create_workbench_app(context, NoChat())
    with TestClient(application) as client:
        root = client.get("/").content
        state = client.get("/api/workbench/state").json()
        manager = application.state.workbench_context
        assert client.get("/compare").status_code == 200
        assert client.post("/api/compare", files=uploads()).status_code == 200
        assert client.get("/api/compare/demo").status_code == 200
        assert client.get("/").content == root
        assert client.get("/api/workbench/state").json() == state
        assert application.state.workbench_context is manager
