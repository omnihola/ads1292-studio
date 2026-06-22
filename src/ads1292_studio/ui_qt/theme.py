"""Compile design tokens into a Qt QSS stylesheet.

``build_qss`` is a pure function (no Qt import) so it is cheap to unit-test.
``apply_theme`` is the thin runtime hook that sets the stylesheet on a running
``QApplication``.
"""
from __future__ import annotations

from typing import Any

from ads1292_studio.ui_qt.tokens import design_tokens


def build_qss(tokens: dict[str, Any] | None = None) -> str:
    """Return the full application QSS string built from ``tokens``."""
    t = tokens if tokens is not None else design_tokens()
    radius = t["radius"]
    radius_sm = t["radius_sm"]
    return f"""
/* ---- base ---- */
QWidget {{
    background: {t['surface']};
    color: {t['ink']};
    font-size: {t['font_body']}px;
}}
QMainWindow, #CentralRoot {{ background: {t['surface']}; }}

/* ---- cards / panels ---- */
QFrame#Card {{
    background: {t['panel']};
    border: 1px solid {t['border']};
    border-radius: {radius}px;
}}
QFrame#Toolbar, QFrame#DisplayToolbar {{
    background: {t['panel_alt']};
    border: none;
    border-bottom: 1px solid {t['border']};
}}
QFrame#Header {{ background: {t['panel']}; border-bottom: 1px solid {t['border']}; }}
QFrame#StatusBar {{ background: {t['panel']}; border-top: 1px solid {t['border']}; }}

/* ---- labels ---- */
QLabel#Title {{ font-size: {t['font_title']}px; font-weight: 650; color: {t['ink']}; }}
QLabel#Subtitle {{ color: {t['ink_muted']}; }}
QLabel#CardHead, QLabel#GroupHead {{
    color: {t['ink_faint']};
    font-size: {t['font_label']}px;
    font-weight: 700;
}}
QLabel#Muted {{ color: {t['ink_muted']}; }}
QLabel#Faint {{ color: {t['ink_faint']}; }}

/* ---- buttons ---- */
QPushButton {{
    background: {t['panel']};
    color: {t['ink']};
    border: 1px solid {t['border_strong']};
    border-radius: {radius_sm}px;
    padding: 6px 14px;
    font-weight: 600;
}}
QPushButton:hover {{ border-color: {t['accent']}; color: {t['accent']}; }}
QPushButton:checked {{ background: {t['accent']}; color: #FFFFFF; border-color: {t['accent']}; }}
QPushButton:checked:hover {{ background: {t['accent_press']}; color: #FFFFFF; border-color: {t['accent_press']}; }}
QPushButton:disabled {{ color: {t['ink_faint']}; border-color: {t['border']}; background: {t['panel']}; }}
QPushButton#Primary {{ background: {t['accent']}; color: #FFFFFF; border-color: {t['accent']}; }}
QPushButton#Primary:hover {{ background: {t['accent_press']}; border-color: {t['accent_press']}; color: #FFFFFF; }}
QPushButton#Primary:disabled {{ background: {t['panel']}; color: {t['ink_faint']}; border-color: {t['border']}; }}
QPushButton#Go {{ background: {t['ok']}; color: #FFFFFF; border-color: {t['ok']}; }}
QPushButton#Go:hover {{ background: {t['ok']}; color: #FFFFFF; }}
QPushButton#Go:disabled {{ background: {t['panel']}; color: {t['ink_faint']}; border-color: {t['border']}; }}
QPushButton#Danger {{ background: {t['bad_soft']}; color: {t['bad']}; border-color: {t['bad']}; }}
QPushButton#Danger:disabled {{ background: {t['panel']}; color: {t['ink_faint']}; border-color: {t['border']}; }}

/* ---- inputs ---- */
QComboBox, QLineEdit {{
    background: #FFFFFF;
    color: {t['ink']};
    border: 1px solid {t['border_strong']};
    border-radius: {radius_sm}px;
    padding: 4px 9px;
    min-height: 22px;
}}
QComboBox:focus, QLineEdit:focus {{ border-color: {t['accent']}; }}
QComboBox::drop-down {{ border: none; width: 18px; }}

/* ---- checkbox ---- */
QCheckBox {{ color: {t['ink']}; spacing: 9px; padding: 2px 2px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {t['border_strong']}; background: #FFFFFF; }}
QCheckBox::indicator:checked {{ background: {t['accent']}; border-color: {t['accent']}; }}

/* ---- tabs ---- */
QTabWidget::pane {{ border: none; border-top: 1px solid {t['border']}; }}
QTabBar::tab {{
    background: transparent;
    color: {t['ink_muted']};
    padding: 8px 15px;
    font-weight: 600;
    border: none;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{ color: {t['accent']}; border-bottom: 2px solid {t['accent']}; }}
QTabBar::tab:hover {{ color: {t['accent']}; }}

/* ---- scrollbars ---- */
QScrollArea {{ border: none; background: {t['surface']}; }}
QScrollBar:vertical {{ background: {t['panel_alt']}; width: 11px; margin: 2px; border-radius: 6px; }}
QScrollBar::handle:vertical {{ background: {t['border_strong']}; min-height: 30px; border-radius: 5px; }}
QScrollBar::handle:vertical:hover {{ background: {t['ink_faint']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
""".strip()


def apply_theme(app: Any, mode: str = "light") -> None:
    """Apply the compiled QSS to a running ``QApplication``."""
    app.setStyleSheet(build_qss(design_tokens(mode)))
