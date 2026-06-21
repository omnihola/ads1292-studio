from __future__ import annotations

import struct


def _png_dimensions(path) -> tuple[int, int]:
    with open(path, "rb") as handle:
        header = handle.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("asset is not a PNG")
    return struct.unpack(">II", header[16:24])


def test_app_icon_asset_is_high_resolution_png() -> None:
    from ads1292_studio.app_icon import app_icon_path

    path = app_icon_path()
    width, height = _png_dimensions(path)

    assert path.name == "app-icon-1024.png"
    assert width >= 1024
    assert height >= 1024


def test_app_icon_has_transparent_corners_without_white_square_border() -> None:
    from PIL import Image

    from ads1292_studio.app_icon import app_icon_path

    image = Image.open(app_icon_path()).convert("RGBA")
    width, height = image.size
    corner_pixels = (
        image.getpixel((0, 0)),
        image.getpixel((width - 1, 0)),
        image.getpixel((0, height - 1)),
        image.getpixel((width - 1, height - 1)),
    )

    assert all(pixel[3] == 0 for pixel in corner_pixels)

    dock_gray = (96, 104, 104, 255)
    composite = Image.new("RGBA", image.size, dock_gray)
    composite.alpha_composite(image)
    composited_corners = (
        composite.getpixel((0, 0)),
        composite.getpixel((width - 1, 0)),
        composite.getpixel((0, height - 1)),
        composite.getpixel((width - 1, height - 1)),
    )
    assert all(pixel == dock_gray for pixel in composited_corners)


def test_app_initialization_applies_window_icon() -> None:
    import inspect

    from ads1292_studio.app import App

    source = inspect.getsource(App.__init__)

    assert "apply_app_icon(self)" in source
