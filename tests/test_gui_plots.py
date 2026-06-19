from matplotlib.figure import Figure

from ads1292_studio.gui_plots import draw_pqrst_review
from ads1292_studio.models import PqrstReview


class FakeCanvas:
    def __init__(self) -> None:
        self.draw_idle_calls = 0

    def draw_idle(self) -> None:
        self.draw_idle_calls += 1


def test_draw_pqrst_review_renders_average_beat_and_refreshes_canvas() -> None:
    fig = Figure()
    ax = fig.add_subplot(111)
    canvas = FakeCanvas()
    review = PqrstReview(
        qrs_clear=True,
        p_tentative=True,
        t_tentative=False,
        beats_used=3,
        average_beat=(0.0, 1.0, 0.0),
        time_ms=(-10.0, 0.0, 10.0),
    )

    draw_pqrst_review(ax, canvas, review)

    assert canvas.draw_idle_calls == 1
    assert "PQRST review: QRS=True" in ax.get_title()
    assert len(ax.lines) == 2
    assert ax.get_xlabel() == "Time relative to R peak (ms)"
