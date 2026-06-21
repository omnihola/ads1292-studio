from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any


APP_ICON_RESOURCE = "assets/app-icon-1024.png"


def app_icon_path() -> Path:
    return Path(str(files("ads1292_studio").joinpath(APP_ICON_RESOURCE)))


def apply_app_icon(root: Any) -> bool:
    try:
        import tkinter as tk

        image = tk.PhotoImage(file=str(app_icon_path()))
        root.iconphoto(True, image)
        root._ads1292_app_icon = image
        return True
    except Exception:
        return False
