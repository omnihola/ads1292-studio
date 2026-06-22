"""User preferences: pure dataclass round-trip + sanitization."""
from __future__ import annotations

from ads1292_studio.ui_qt.preferences import Preferences


def test_round_trips_through_dict() -> None:
    prefs = Preferences(
        port="/dev/cu.usbmodem", mode="Raw Record",
        save_csv=True, save_h5=False, save_xlsx=True,
        window="12 s", gain="2x", speed="50 mm/s",
    )
    assert Preferences.from_dict(prefs.to_dict()) == prefs


def test_from_dict_ignores_unknown_and_fills_defaults() -> None:
    prefs = Preferences.from_dict({"port": "/dev/x", "bogus": 1})
    assert prefs.port == "/dev/x"
    # defaults preserved for missing keys
    assert prefs.save_csv is True
    assert prefs.save_h5 is True
    assert prefs.save_xlsx is False
    assert prefs.window == "8 s"


def test_from_dict_coerces_types() -> None:
    prefs = Preferences.from_dict({"save_csv": 0, "save_xlsx": 1, "gain": 1})
    assert prefs.save_csv is False
    assert prefs.save_xlsx is True
    assert prefs.gain == "1"


def test_empty_dict_is_all_defaults() -> None:
    assert Preferences.from_dict({}) == Preferences()
