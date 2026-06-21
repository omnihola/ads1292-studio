"""Design tokens for the Qt front-end (light-first, dark-ready).

Single source of truth for color, radius, spacing, and type. ``theme.py``
compiles these into a QSS stylesheet; the live plot derives matplotlib colors
from the same values so chrome and plots stay in sync.

Seeded from the existing :data:`ads1292_studio.plot_theme.APP_VISUAL_TOKENS`
where the two overlap, so the Qt app inherits the established palette.
"""
from __future__ import annotations

from ads1292_studio.plot_theme import APP_VISUAL_TOKENS


# Light theme. A future "dark" map can replace this block only; widget code and
# theme.py do not change because they read tokens by key.
_LIGHT_TOKENS: dict[str, object] = {
    # surfaces
    "surface": "#EEF2F7",
    "panel": APP_VISUAL_TOKENS.get("panel", "#FFFFFF"),
    "panel_alt": "#F5F8FC",
    "border": "#DCE3EC",
    "border_strong": "#C6D0DC",
    # ink
    "ink": "#1B2533",
    "ink_muted": "#5A6677",
    "ink_faint": "#8A95A4",
    # accent + brand
    "accent": "#1E88A8",
    "accent_press": "#166076",
    "accent_soft": "#E2F1F6",
    "indigo": "#4C5DD4",
    # semantic
    "ok": "#2E9E6B",
    "ok_soft": "#E3F4EC",
    "warn": "#C8881E",
    "warn_soft": "#FBF0DA",
    "bad": "#D24B4B",
    "bad_soft": "#FBE7E7",
    # plot traces
    "ecg": "#1E88A8",
    "resp": "#4C5DD4",
    # geometry (px)
    "radius": 10,
    "radius_sm": 7,
    # spacing scale (px, 4px grid)
    "space_xs": 4,
    "space_sm": 6,
    "space_md": 10,
    "space_lg": 14,
    # type scale (pt/px)
    "font_label": 11,
    "font_body": 13,
    "font_title": 17,
}

_THEMES: dict[str, dict[str, object]] = {"light": _LIGHT_TOKENS}


def design_tokens(mode: str = "light") -> dict[str, object]:
    """Return a fresh copy of the design tokens for ``mode`` (default light)."""
    base = _THEMES.get(mode, _LIGHT_TOKENS)
    return dict(base)
