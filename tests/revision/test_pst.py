"""Native synthetic PST comparison: original files, not a converted Telesis oracle."""

import hashlib
from pathlib import Path
import shutil

from fastapi.testclient import TestClient
import pytest
from typer.testing import CliRunner

from hardwise.cli import app
from hardwise.revision.engine import compare_files
from hardwise.revision.report import render_comparison_html
from hardwise.revision import server

FIXTURE = Path(__file__).parents[1] / "fixtures/allegro/pst"
BOM = "Reference,Value,Footprint\nC1,0.1uF 25V,C0402\nR1,10K,R0402\nU1,TBD210419,TSSOP8\n"


@pytest.fixture
def pair(tmp_path):
    paths = []
    for side in ("before", "after"):
        directory = tmp_path / side
        shutil.copytree(FIXTURE, directory)
        bom = tmp_path / (side + ".csv")
        bom.write_text(BOM)
        paths.extend((directory, bom))
    return paths


def upload_files(pair):
    return [
        (
            role,
            (
                role.split("_", 1)[1] + ".dat"
                if not role.endswith("bom")
                else pair[1 if role.startswith("before") else 3].name,
                (
                    pair[0 if role.startswith("before") else 2] / (role.split("_", 1)[1] + ".dat")
                ).read_bytes()
                if not role.endswith("bom")
                else pair[1 if role.startswith("before") else 3].read_bytes(),
            ),
        )
        for role in server.PST_ROLES
    ]


def test_pst_identical_keeps_all_four_raw_file_digests(pair):
    result = compare_files(*pair)
    assert result.input_format == "pst_csv_v1"
    assert result.status == "no_observed_difference"
    assert result.summary.unchanged_components == 3
    assert len(result.before.sources) == 4
    for source in result.before.sources:
        path = pair[1] if source.role == "bom" else pair[0] / source.file
        assert source.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result.electrical_verdict == "not_evaluated"


def test_native_pst_value_and_package_changes_locate_chip_file(pair):
    chip = pair[2] / "pstchip.dat"
    chip.write_text(
        chip.read_text()
        .replace("VALUE='10K'", "VALUE='4.7K'")
        .replace("JEDEC_TYPE='R0402'", "JEDEC_TYPE='R0603'")
    )
    result = compare_files(*pair)
    value = next(c for c in result.changes if c.field == "netlist.property.VALUE")
    assert (value.refdes, value.before.values, value.after.values) == ("R1", ("10K",), ("4.7K",))
    assert all(e.file == "pstchip.dat" for e in value.after.evidence)
    assert all("primitive=" in e.locator for e in value.after.evidence)
    package = next(c for c in result.changes if c.field == "netlist.package")
    assert package.after.values == ("R0603",)
    assert package.after.evidence[0].sha256 == hashlib.sha256(chip.read_bytes()).hexdigest()
    html = render_comparison_html(result)
    assert "pstxnet.dat" in html and "pstxprt.dat" in html and "pstchip.dat" in html
    assert "4.7K" in html


def test_pst_pure_rename_once_and_same_name_endpoint_changes(pair):
    net = pair[2] / "pstxnet.dat"
    original = net.read_text()
    net.write_text(original.replace("'CTRL'", "'ENABLE'"))
    result = compare_files(*pair)
    assert result.summary.net_renames == 1
    assert result.summary.connection_changes == 0
    change = result.changes[0]
    assert change.after.evidence[0].file == "pstxnet.dat"
    assert "NET_NAME" in change.after.evidence[0].locator
    net.write_text(original.replace("NODE_NAME\tR1 2", "NODE_NAME\tR1 3"))
    result = compare_files(*pair)
    assert result.summary.connection_changes > 0
    assert result.summary.net_renames == 0


@pytest.mark.parametrize("name", ["pstxnet.dat", "pstxprt.dat", "pstchip.dat"])
def test_missing_pst_role_rejected_not_reported_as_deletions(pair, name):
    (pair[2] / name).unlink()
    with pytest.raises(ValueError, match=name):
        compare_files(*pair)


def test_pst_missing_property_not_inferred_from_primitive(pair):
    for directory in (pair[0], pair[2]):
        chip = directory / "pstchip.dat"
        chip.write_text(chip.read_text().replace("    VALUE='10K';\n", ""))
    result = compare_files(*pair)
    assert result.status == "needs_review"
    assert any(i.code == "pst_attribute_missing" and i.refdes == "R1" for i in result.issues)
    assert result.summary.unchanged_components == 2


@pytest.mark.parametrize("name", ["pstxnet.dat", "pstxprt.dat", "pstchip.dat"])
def test_pst_strict_utf8_and_optional_bom_hash_raw_bytes(pair, name):
    path = pair[2] / name
    content = path.read_bytes()
    path.write_bytes(b"\xef\xbb\xbf" + content)
    result = compare_files(*pair)
    assert not result.changes and not result.issues
    assert (
        next(s for s in result.after.sources if s.file == name).sha256
        == hashlib.sha256(path.read_bytes()).hexdigest()
    )
    path.write_bytes(content + b"\xff")
    with pytest.raises(UnicodeDecodeError):
        compare_files(*pair)


def test_pst_cli_directory_and_api_equal_python(pair, tmp_path):
    expected = compare_files(*pair)
    output, data = tmp_path / "report.html", tmp_path / "report.json"
    response = CliRunner().invoke(
        app, ["compare", *map(str, pair), "--output", str(output), "--json-output", str(data)]
    )
    assert response.exit_code == 0, response.output
    assert expected.model_validate_json(data.read_text()) == expected
    assert "pst_csv_v1" in output.read_text()
    with TestClient(server.create_compare_app()) as client:
        response = client.post("/api/compare/pst", files=upload_files(pair))
    assert response.status_code == 200, response.text
    assert response.json() == expected.model_dump(mode="json")


@pytest.mark.parametrize("case", ["missing", "duplicate", "wrong_name", "extra", "text_field"])
def test_pst_api_requires_exact_eight_roles(pair, case):
    files = upload_files(pair)
    data = None
    if case == "missing":
        files.pop(2)
    elif case == "duplicate":
        files[-1] = files[0]
    elif case == "wrong_name":
        files[0] = (files[0][0], ("pstxprt.dat", files[0][1][1]))
    elif case == "extra":
        files.append(("anything", ("x.dat", b"x")))
    else:
        data = {"path": "/private/source"}
    with TestClient(server.create_compare_app()) as client:
        response = client.post("/api/compare/pst", files=files, data=data)
    assert response.status_code == 400


def test_pst_rejects_duplicate_parts_unknown_nodes_and_mixed_format(pair, tmp_path):
    part = pair[2] / "pstxprt.dat"
    original = part.read_text()
    part.write_text(original + "\nPART_NAME\n R1 'GW_RESISTOR_R0402_10K':\n")
    with pytest.raises(ValueError, match="duplicate"):
        compare_files(*pair)
    part.write_text(original)
    net = pair[2] / "pstxnet.dat"
    content = net.read_text()
    net.write_text(content.replace("NODE_NAME\tU1 8", "NODE_NAME\tU999 8"))
    with pytest.raises(ValueError):
        compare_files(*pair)
    net.write_text(content)
    from hardwise.revision.demo import BEFORE_NETLIST

    telesis = tmp_path / "telesis.net"
    telesis.write_text(BEFORE_NETLIST)
    with pytest.raises(ValueError, match="相同的网表格式"):
        compare_files(pair[0], pair[1], telesis, pair[3])


def test_pst_api_applies_per_file_limit_and_cleans_spools(pair, monkeypatch):
    import starlette.formparsers

    spools = []
    original = starlette.formparsers.SpooledTemporaryFile

    def spool(**kwargs):
        stream = original(**kwargs)
        spools.append(stream)
        return stream

    monkeypatch.setattr(starlette.formparsers, "SpooledTemporaryFile", spool)
    monkeypatch.setattr(server, "MAX_FILE_BYTES", 16)
    with TestClient(server.create_compare_app()) as client:
        response = client.post("/api/compare/pst", files=upload_files(pair))
    assert response.status_code == 413
    assert spools and all(stream.closed for stream in spools)
