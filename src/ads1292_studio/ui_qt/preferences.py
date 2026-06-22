"""Persisted user preferences for the Qt app (port, save formats, display).

Pure data + (de)serialization here; QSettings storage lives in main_window so
this module stays trivially testable without touching global Qt state.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields


@dataclass(frozen=True)
class Preferences:
    port: str = ""
    mode: str = "Live Monitor"
    save_csv: bool = True
    save_h5: bool = True
    save_xlsx: bool = False
    window: str = "8 s"
    gain: str = "1x"
    speed: str = "25 mm/s"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Preferences":
        defaults = cls()
        kwargs = {}
        for f in fields(cls):
            if f.name not in data:
                continue
            value = data[f.name]
            if isinstance(getattr(defaults, f.name), bool):
                kwargs[f.name] = _to_bool(value)
            else:
                kwargs[f.name] = str(value)
        return cls(**kwargs)


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in ("1", "true", "yes", "on")
