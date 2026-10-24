"""Read digests describe actual parser bytes and reject observed intake changes."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import pytest
from hardwise.input_provenance import (
    InputChangedError,
    capture_input_reads,
    hash_input_file,
    read_input_text,
)


def test_raw_hash_precedes_bom_decode_and_preserves_newline_modes(tmp_path):
    path = tmp_path / "input.csv"
    raw = b'\xef\xbb\xbfA,\r\n"x\r\ny"\r\n'
    path.write_bytes(raw)
    with capture_input_reads() as reads:
        assert read_input_text(path, role="bom", encoding="utf-8-sig") == 'A,\n"x\ny"\n'
        assert read_input_text(
            path, role="pin_table", encoding="utf-8-sig", newline=""
        ) == raw.decode("utf-8-sig")
        manifest = reads.finish()
    assert len(manifest.files) == 1
    assert manifest.files[0].roles == ("bom", "pin_table")
    assert manifest.files[0].sha256 == hashlib.sha256(raw).hexdigest()
    assert manifest.files[0].size_bytes == len(raw)


def test_swallowed_repeated_read_change_still_rejects_publication(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text("original")
    with capture_input_reads() as reads:
        read_input_text(path, role="profile")
        path.write_text("changed")
        with pytest.raises(InputChangedError):
            read_input_text(path, role="profile")
        path.write_text("original")
        with pytest.raises(InputChangedError, match="input changed"):
            reads.finish()


def test_late_change_after_only_read_rejects_publication(tmp_path):
    path = tmp_path / "netlist.net"
    path.write_text("before")
    with capture_input_reads() as reads:
        read_input_text(path, role="netlist")
        path.write_text("after")
        with pytest.raises(InputChangedError, match="input changed"):
            reads.finish()


def test_parallel_intakes_do_not_share_file_sets(tmp_path):
    paths = [tmp_path / name for name in ("a.net", "b.net")]
    for path in paths:
        path.write_text(path.name)

    def collect(path):
        with capture_input_reads() as reads:
            read_input_text(path, role="netlist")
            return reads.finish()

    with ThreadPoolExecutor(max_workers=2) as pool:
        manifests = list(pool.map(collect, paths))
    assert [m.files[0].path for m in manifests] == [str(p) for p in paths]
    assert all(len(m.files) == 1 for m in manifests)


def test_streamed_artifact_digest_is_tracked_without_archiving_contents(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_bytes(b"public synthetic notes")
    with capture_input_reads() as reads:
        digest = hash_input_file(path, role="review_artifact_digest")
        manifest = reads.finish()
    assert digest == hashlib.sha256(path.read_bytes()).hexdigest()
    assert manifest.files[0].sha256 == digest
    assert "public synthetic notes" not in manifest.model_dump_json()


def test_same_bytes_at_a_retargeted_symlink_do_not_hide_source_changes(tmp_path):
    first, second, link = [tmp_path / name for name in ("first", "second", "link")]
    first.write_text("same bytes")
    second.write_text("same bytes")
    link.symlink_to(first)
    with capture_input_reads() as reads:
        read_input_text(link, role="netlist")
        link.unlink()
        link.symlink_to(second)
        with pytest.raises(InputChangedError, match="input changed"):
            reads.finish()


def test_failed_capture_does_not_leak_into_later_readers(tmp_path):
    path = tmp_path / "input"
    path.write_text("public")
    with pytest.raises(RuntimeError):
        with capture_input_reads():
            read_input_text(path, role="failed")
            raise RuntimeError("synthetic parser error")
    read_input_text(path, role="outside")
    with capture_input_reads() as reads:
        read_input_text(path, role="new")
        assert reads.finish().files[0].roles == ("new",)


@pytest.mark.parametrize("reader", [read_input_text, hash_input_file])
def test_swallowed_missing_reread_stays_failed_after_original_bytes_restored(tmp_path, reader):
    path = tmp_path / "profile.json"
    path.write_text("original")
    with capture_input_reads() as reads:
        reader(path, role="profile")
        path.unlink()
        with pytest.raises(OSError):
            reader(path, role="profile")
        path.write_text("original")
        with pytest.raises(InputChangedError, match="became unavailable"):
            reads.finish()
