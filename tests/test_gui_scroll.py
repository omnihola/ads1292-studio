import inspect
from types import SimpleNamespace

from ads1292_studio.app import ScrollableFrame, _mousewheel_units


def test_scrollable_frame_uses_canvas_scrollbar_and_mousewheel() -> None:
    source = inspect.getsource(ScrollableFrame)

    assert "tk.Canvas" in source
    assert "ttk.Scrollbar" in source
    assert "create_window" in source
    assert "yscrollcommand" in source
    assert "scrollregion" in source
    assert "<MouseWheel>" in source


def test_mousewheel_units_handles_small_macos_deltas() -> None:
    assert _mousewheel_units(SimpleNamespace(delta=1, num=None)) == -1
    assert _mousewheel_units(SimpleNamespace(delta=-1, num=None)) == 1
    assert _mousewheel_units(SimpleNamespace(delta=120, num=None)) == -1
    assert _mousewheel_units(SimpleNamespace(delta=-120, num=None)) == 1
    assert _mousewheel_units(SimpleNamespace(delta=0, num=4)) == -1
    assert _mousewheel_units(SimpleNamespace(delta=0, num=5)) == 1
