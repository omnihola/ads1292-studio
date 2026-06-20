from __future__ import annotations

from ads1292_studio import plot_theme


def test_apply_seaborn_plot_theme_is_idempotent(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def record_set_theme(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(plot_theme, "_SEABORN_THEME_APPLIED", False, raising=False)
    monkeypatch.setattr(plot_theme.sns, "set_theme", record_set_theme)

    plot_theme.apply_seaborn_plot_theme()
    plot_theme.apply_seaborn_plot_theme()

    assert len(calls) == 1
    assert calls[0]["style"] == "whitegrid"
    assert calls[0]["context"] == "notebook"
    assert calls[0]["palette"] == "colorblind"
