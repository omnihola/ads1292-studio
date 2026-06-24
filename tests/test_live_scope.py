"""The pyqtgraph real-time scope: API parity with the matplotlib live panel."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _scope(qapp):
    from ads1292_studio.ui_qt.live_scope import LiveScope

    return LiveScope()


def test_update_traces_sets_data(qapp) -> None:
    scope = _scope(qapp)
    scope.update_traces([0.0, 1.0, 2.0], [10.0, 20.0, 30.0], [0.0, 1.0, 2.0], [1.0, 2.0, 3.0])
    assert list(scope.ecg_y()) == [10.0, 20.0, 30.0]
    assert list(scope.ecg_x()) == [0.0, 1.0, 2.0]


def test_calibration_scales_and_relabels(qapp) -> None:
    scope = _scope(qapp)
    scope.set_calibration(2.0)
    assert scope._uv_per_count == 2.0
    scope.update_traces([0.0, 1.0], [10.0, 20.0], [0.0, 1.0], [5.0, 5.0])
    assert list(scope.ecg_y()) == [20.0, 40.0]  # scaled to µV
    assert "µV" in scope.p_ecg.getAxis("left").labelText
    scope.set_calibration(None)
    assert "counts" in scope.p_ecg.getAxis("left").labelText


def test_autoscale_toggle_tracks_flag(qapp) -> None:
    scope = _scope(qapp)
    assert scope._autoscale_enabled is True
    scope.set_autoscale(False)
    assert scope._autoscale_enabled is False
    scope.set_autoscale(True)
    assert scope._autoscale_enabled is True


def test_autoscale_uses_explicit_ranges_not_pyqtgraph_autorange(qapp) -> None:
    scope = _scope(qapp)
    scope.set_autoscale(False)
    scope.set_autoscale(True)

    assert scope.p_ecg.vb.state["autoRange"][1] is False
    assert scope.p_resp.vb.state["autoRange"][1] is False


def test_autoscale_off_first_data_frame_initializes_visible_y_range(qapp) -> None:
    scope = _scope(qapp)
    scope.set_autoscale(False)

    scope.update_traces([0.0, 1.0], [779750.0, 780240.0], [0.0, 1.0], [8388588.0, 8388611.0])

    ecg_ymin, ecg_ymax = scope.p_ecg.vb.viewRange()[1]
    resp_ymin, resp_ymax = scope.p_resp.vb.viewRange()[1]
    assert ecg_ymin < 779750.0 < ecg_ymax
    assert ecg_ymin < 780240.0 < ecg_ymax
    assert resp_ymin < 8388588.0 < resp_ymax
    assert resp_ymin < 8388611.0 < resp_ymax


def test_event_markers_and_pending_are_added_and_cleared(qapp) -> None:
    from ads1292_studio.events import EventMarker, event_from_interval

    scope = _scope(qapp)
    markers = [
        EventMarker(timestamp_seconds=1.0, label="p"),
        event_from_interval(start_seconds=2.0, end_seconds=3.0, label="r"),
    ]
    scope.set_event_markers(markers, pending_range_start=4.0)
    assert len(scope._event_items) == 3  # point + range + pending
    scope.set_event_markers([], pending_range_start=None)
    assert len(scope._event_items) == 0


def test_sweep_speed_sets_tick_spacing_without_error(qapp) -> None:
    scope = _scope(qapp)
    scope.set_sweep_speed(25)
    scope.set_sweep_speed(50)  # must not raise
