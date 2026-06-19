from __future__ import annotations

from ads1292_studio import matplotlib_runtime


def test_configure_matplotlib_cache_preserves_existing_writable_dir(monkeypatch, tmp_path) -> None:
    configured = tmp_path / "configured"
    configured.mkdir()
    monkeypatch.setenv("MPLCONFIGDIR", str(configured))

    cache_path = matplotlib_runtime.configure_matplotlib_cache()

    assert cache_path == configured
    assert cache_path.exists()


def test_configure_matplotlib_cache_replaces_unwritable_existing_dir(monkeypatch, tmp_path) -> None:
    bad_path = tmp_path / "not-a-directory"
    bad_path.write_text("blocked")
    monkeypatch.setenv("MPLCONFIGDIR", str(bad_path))
    monkeypatch.setattr(matplotlib_runtime.tempfile, "gettempdir", lambda: str(tmp_path))

    cache_path = matplotlib_runtime.configure_matplotlib_cache()

    assert cache_path == tmp_path / matplotlib_runtime.MATPLOTLIB_CACHE_DIR_NAME
    assert cache_path.exists()
    assert cache_path.is_dir()
