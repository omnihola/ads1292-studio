import inspect
from types import SimpleNamespace

from ads1292_studio.app import App, ScrollableFrame, _mousewheel_units


def test_scrollable_frame_uses_canvas_scrollbar_and_mousewheel() -> None:
    source = inspect.getsource(ScrollableFrame)

    assert "tk.Canvas" in source
    assert "ttk.Scrollbar" in source
    assert "scrollable_frame_spec()" in source
    assert "bg=str(frame_spec[\"canvas_background\"])" in source
    assert "padding=int(frame_spec[\"content_padding\"])" in source
    assert "create_window" in source
    assert "yscrollcommand" in source
    assert "scrollregion" in source
    assert "<MouseWheel>" in source


def test_app_imports_scrollable_frame_instead_of_defining_it_inline() -> None:
    from ads1292_studio.gui_sidebar import build_sidebar

    source = inspect.getsource(App)
    sidebar_source = inspect.getsource(build_sidebar)

    assert "class ScrollableFrame" not in source
    assert "ScrollableFrame(tab" in sidebar_source
    assert "app.sidebar_scrolls: dict[str, ScrollableFrame]" in sidebar_source


def test_scrollable_frame_uses_single_global_mousewheel_dispatcher() -> None:
    source = inspect.getsource(ScrollableFrame)

    assert "_mousewheel_events" in source
    assert "_global_mousewheel_bound" in source
    assert "_global_mousewheel_widget" in source
    assert "_dispatch_mousewheel" in source
    assert "_mousewheel_target" in source
    assert "for sequence in ScrollableFrame._mousewheel_events" in source
    assert "self.canvas.bind_all(sequence, self._dispatch_mousewheel)" in source
    assert "self.canvas.bind(\"<Enter>\"" in source


def test_scrollable_frame_rebinds_mousewheel_when_binding_owner_is_destroyed() -> None:
    source = inspect.getsource(ScrollableFrame)

    assert "_rebind_global_mousewheel" in source
    assert "_unbind_mousewheel_events(self.canvas)" in source
    assert "ScrollableFrame._instances[0]._bind_global_mousewheel()" in source
    assert "ScrollableFrame._global_mousewheel_widget is self.canvas" in source


def test_mousewheel_units_handles_small_macos_deltas() -> None:
    assert _mousewheel_units(SimpleNamespace(delta=1, num=None)) == -1
    assert _mousewheel_units(SimpleNamespace(delta=-1, num=None)) == 1
    assert _mousewheel_units(SimpleNamespace(delta=120, num=None)) == -1
    assert _mousewheel_units(SimpleNamespace(delta=-120, num=None)) == 1
    assert _mousewheel_units(SimpleNamespace(delta=0, num=4)) == -1
    assert _mousewheel_units(SimpleNamespace(delta=0, num=5)) == 1


def test_app_tick_callback_is_cancellable_on_window_destroy() -> None:
    source = inspect.getsource(App)

    assert "self.tick_after_id: str | None = None" in source
    assert "def _schedule_tick" in source
    assert "def _cancel_tick" in source
    assert "self.after_cancel(self.tick_after_id)" in source
    assert "def destroy" in source
    assert "self._cancel_tick()" in source


def test_app_batches_queued_log_messages_to_reduce_text_widget_churn() -> None:
    source = inspect.getsource(App)

    assert "def _append_log_messages" in source
    assert "format_log_entries(messages, stamp)" in source
    assert "self._trim_log_text()" in source
    assert "drain_queue_items(self.logs, MAX_LOG_MESSAGES_PER_TICK)" in source
    assert "self._append_log_messages(log_messages)" in source
