"""Tests for the PySide6 design-token + QSS theme system (pure, no Qt runtime)."""
from __future__ import annotations

import re

from ads1292_studio.ui_qt.tokens import design_tokens
from ads1292_studio.ui_qt.theme import build_qss


REQUIRED_COLOR_KEYS = (
    "surface", "panel", "panel_alt", "border", "border_strong",
    "ink", "ink_muted", "ink_faint",
    "accent", "accent_press", "accent_soft", "indigo",
    "ok", "ok_soft", "warn", "warn_soft", "bad", "bad_soft",
    "ecg", "resp",
)
REQUIRED_SIZE_KEYS = ("radius", "radius_sm")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def test_design_tokens_has_all_required_keys() -> None:
    tokens = design_tokens()
    for key in REQUIRED_COLOR_KEYS + REQUIRED_SIZE_KEYS:
        assert key in tokens, f"missing token: {key}"


def test_design_tokens_colors_are_hex() -> None:
    tokens = design_tokens()
    for key in REQUIRED_COLOR_KEYS:
        assert HEX.match(str(tokens[key])), f"{key}={tokens[key]} is not a #RRGGBB color"


def test_design_tokens_sizes_are_ints() -> None:
    tokens = design_tokens()
    for key in REQUIRED_SIZE_KEYS:
        assert isinstance(tokens[key], int)


def test_design_tokens_returns_a_copy() -> None:
    a = design_tokens()
    a["accent"] = "#000000"
    b = design_tokens()
    assert b["accent"] != "#000000", "design_tokens() must return a fresh copy"


def test_light_is_the_default_and_seeds_match_app_visual_tokens() -> None:
    # Light-first: the Qt surface/panel/accent should align with the existing app seed.
    from ads1292_studio.plot_theme import APP_VISUAL_TOKENS
    tokens = design_tokens()
    assert tokens["panel"] == APP_VISUAL_TOKENS["panel"]


def test_build_qss_is_a_nonempty_string() -> None:
    qss = build_qss()
    assert isinstance(qss, str) and len(qss) > 200


def test_build_qss_references_core_widgets_and_accent() -> None:
    qss = build_qss()
    tokens = design_tokens()
    for needle in ("QWidget", "QPushButton", "QComboBox", "QLineEdit", "QScrollBar"):
        assert needle in qss, f"QSS missing rule for {needle}"
    assert tokens["accent"].upper() in qss.upper(), "accent color not used in QSS"


def test_build_qss_is_deterministic() -> None:
    assert build_qss() == build_qss()


def test_build_qss_accepts_custom_tokens() -> None:
    custom = design_tokens()
    custom["accent"] = "#123456"
    qss = build_qss(custom)
    assert "#123456".upper() in qss.upper()
