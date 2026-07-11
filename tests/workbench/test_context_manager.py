import gc
import weakref
from pathlib import Path

import pytest

from hardwise.workbench.context_manager import WorkbenchContextManager


def test_swap_defers_close_until_request_lease_finishes(tmp_path: Path) -> None:
    old = object()
    new = object()
    closed: list[object] = []
    removed: list[Path] = []
    manager = WorkbenchContextManager(  # type: ignore[arg-type]
        old,
        close_context=closed.append,
        remove_dir=removed.append,
    )
    import_dir = tmp_path / "next-import"

    with manager.lease() as snapshot:
        assert snapshot is old
        manager.swap(new, import_dir=import_dir)  # type: ignore[arg-type]
        assert manager.current is old
        assert closed == []

    assert closed == [old]
    assert removed == []
    assert manager.current is new

    manager.shutdown()
    manager.shutdown()
    assert closed == [old, new]
    assert removed == [import_dir]


def test_nested_lease_keeps_the_original_request_snapshot() -> None:
    old = object()
    new = object()
    closed: list[object] = []
    manager = WorkbenchContextManager(old, close_context=closed.append)  # type: ignore[arg-type]

    with manager.lease() as outer:
        manager.swap(new)  # type: ignore[arg-type]
        with manager.lease() as inner:
            assert inner is outer is old
        assert closed == []

    assert closed == [old]
    manager.shutdown()
    assert closed == [old, new]


def test_shutdown_removes_import_dir_when_context_close_fails(tmp_path: Path) -> None:
    removed: list[Path] = []
    manager = WorkbenchContextManager(  # type: ignore[arg-type]
        object(),
        close_context=lambda _context: None,
        remove_dir=removed.append,
    )
    import_dir = tmp_path / "failed-close-import"
    manager.swap(object(), import_dir=import_dir)  # type: ignore[arg-type]
    manager._close_context = lambda _context: (_ for _ in ()).throw(RuntimeError("close failed"))

    with pytest.raises(RuntimeError, match="close failed"):
        manager.shutdown()

    assert removed == [import_dir]


def test_closed_retired_context_is_not_kept_alive() -> None:
    class _Context:
        pass

    old = _Context()
    reference = weakref.ref(old)
    manager = WorkbenchContextManager(  # type: ignore[arg-type]
        old,
        close_context=lambda _context: None,
    )

    manager.swap(_Context())  # type: ignore[arg-type]
    del old
    gc.collect()

    assert reference() is None
    assert manager._retired == []
    manager.shutdown()


def test_shutdown_waits_for_active_lease_before_closing() -> None:
    context = object()
    closed: list[object] = []
    manager = WorkbenchContextManager(  # type: ignore[arg-type]
        context,
        close_context=closed.append,
    )

    with manager.lease():
        manager.shutdown()
        assert closed == []

    assert closed == [context]
    with pytest.raises(RuntimeError, match="shut down"):
        with manager.lease():
            pass


def test_swap_keeps_new_context_when_retired_cleanup_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    old = object()
    new = object()

    def close(context: object) -> None:
        if context is old:
            raise RuntimeError("old close failed")

    manager = WorkbenchContextManager(old, close_context=close)  # type: ignore[arg-type]

    with caplog.at_level("ERROR"):
        manager.swap(new)  # type: ignore[arg-type]

    assert manager.current is new
    assert "retired workbench context cleanup failed after swap" in caplog.text
    manager.shutdown()
