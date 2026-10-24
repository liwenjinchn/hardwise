"""Owned inputs survive source loss and never publish an incomplete snapshot."""

import json
from pathlib import Path
import shutil
from unittest.mock import patch

import pytest

from hardwise.input_provenance import capture_input_reads, read_input_bytes, InputChangedError
from hardwise.workbench.managed_inputs import ManagedInputs


def observed(paths):
    with capture_input_reads() as collector:
        for index, path in enumerate(paths):
            read_input_bytes(path, role=f"public-source-{index}")
        return collector.finish()


def test_owned_bytes_survive_deleted_sources_and_sidecar_move(tmp_path):
    first = tmp_path / "original/a/config.json"
    second = tmp_path / "original/b/config.json"
    for path, data in [(first, b'{"facts": []}'), (second, b'{"hints": []}')]:
        path.parent.mkdir(parents=True)
        path.write_bytes(data)
    manifest = observed([first, second])
    store = ManagedInputs(tmp_path / "old/review.sqlite")
    snapshot = store.capture(manifest)
    shutil.rmtree(tmp_path / "original")
    moved = ManagedInputs(tmp_path / "moved/review.sqlite")
    moved.root.parent.mkdir()
    shutil.move(store.root, moved.root)
    loaded = moved.load(snapshot)
    assert [e["path"] for e in loaded["entries"]] == [f.path for f in manifest.files]
    assert [(moved.root / snapshot / e["member"]).read_bytes() for e in loaded["entries"]] == [
        b'{"facts": []}',
        b'{"hints": []}',
    ]


@pytest.mark.parametrize("change", ["changed", "deleted", "retargeted"])
def test_source_changed_since_parse_is_not_saved(tmp_path, change):
    source = tmp_path / "source"
    source.write_bytes(b"parsed public source")
    manifest = observed([source])
    if change == "changed":
        source.write_bytes(b"different source")
    elif change == "deleted":
        source.unlink()
    else:
        source.unlink()
        other = tmp_path / "other"
        other.write_bytes(b"parsed public source")
        source.symlink_to(other)
    store = ManagedInputs(tmp_path / "review.sqlite")
    with pytest.raises((InputChangedError, FileNotFoundError)):
        store.capture(manifest)
    assert list(store.root.iterdir()) == []


def test_failed_publication_leaves_prior_snapshot_intact(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"public")
    manifest = observed([source])
    store = ManagedInputs(tmp_path / "review.sqlite")
    good = store.capture(manifest)
    with patch.object(Path, "rename", side_effect=OSError("simulated publish failure")):
        with pytest.raises(OSError, match="publish failure"):
            store.capture(manifest)
    assert store.load(good)["snapshot_id"] == good
    assert [p.name for p in store.root.iterdir()] == [good]


@pytest.mark.parametrize("damage", ["bytes", "missing", "extra", "version", "member", "metadata"])
def test_damaged_owned_snapshot_is_rejected(tmp_path, damage):
    source = tmp_path / "source"
    source.write_bytes(b"public")
    store = ManagedInputs(tmp_path / "review.sqlite")
    snapshot = store.capture(observed([source]))
    folder = store.root / snapshot
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    member = folder / manifest["entries"][0]["member"]
    if damage == "bytes":
        member.write_bytes(b"changed")
    elif damage == "missing":
        member.unlink()
    elif damage == "extra":
        (folder / "unexpected").write_bytes(b"extra")
    else:
        if damage == "version":
            manifest["schema_version"] = "future"
        elif damage == "member":
            manifest["entries"][0]["member"] = "../../source"
        else:
            manifest["entries"][0]["path"] = "invented"
        manifest_path.write_text(json.dumps(manifest))
    with pytest.raises((ValueError, FileNotFoundError)):
        store.load(snapshot)


@pytest.mark.parametrize("snapshot", ["../escape", "", "abc", "/tmp/external"])
def test_invalid_snapshot_id_is_rejected(tmp_path, snapshot):
    with pytest.raises(ValueError, match="identifier"):
        ManagedInputs(tmp_path / "review.sqlite").load(snapshot)


@pytest.mark.parametrize("payload", [[], {}, {"schema_version": "hardwise.managed_inputs.v1"}])
def test_malformed_manifest_is_controlled_error(tmp_path, payload):
    source = tmp_path / "source"
    source.write_bytes(b"public")
    store = ManagedInputs(tmp_path / "review.sqlite")
    snapshot = store.capture(observed([source]))
    (store.root / snapshot / "manifest.json").write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        store.load(snapshot)
