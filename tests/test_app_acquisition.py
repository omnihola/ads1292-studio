import inspect

from ads1292_studio.app import App


def test_start_updates_acquisition_summary_when_recording_csv() -> None:
    source = inspect.getsource(App.start)

    assert "write_acquisition_json" in source
    assert "acquisition_var.set(format_acquisition_summary" in source
