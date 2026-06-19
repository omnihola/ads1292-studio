from __future__ import annotations

from dataclasses import dataclass


DISPLAY_WINDOW_CHOICES = (4.0, 8.0, 12.0, 16.0)
DISPLAY_GAIN_CHOICES = (0.5, 1.0, 2.0, 5.0)
SWEEP_SPEED_CHOICES = (25, 50)


@dataclass(frozen=True)
class EcgDisplaySettings:
    time_window_seconds: float = 8.0
    gain: float = 1.0
    sweep_speed_mm_s: int = 25

    def normalized(self) -> "EcgDisplaySettings":
        return EcgDisplaySettings(
            time_window_seconds=nearest_choice(self.time_window_seconds, DISPLAY_WINDOW_CHOICES),
            gain=nearest_choice(self.gain, DISPLAY_GAIN_CHOICES),
            sweep_speed_mm_s=int(nearest_choice(float(self.sweep_speed_mm_s), tuple(float(v) for v in SWEEP_SPEED_CHOICES))),
        )


@dataclass(frozen=True)
class SoftwareFilterSettings:
    highpass_enabled: bool = False
    notch_enabled: bool = False
    lowpass_enabled: bool = False
    bandpass_enabled: bool = False
    highpass_hz: float = 0.5
    notch_hz: float = 60.0
    lowpass_hz: float = 40.0


def nearest_choice(value: float, choices: tuple[float, ...]) -> float:
    return min(choices, key=lambda choice: abs(choice - value))


def display_window_labels() -> tuple[str, ...]:
    return tuple(f"{value:g} s" for value in DISPLAY_WINDOW_CHOICES)


def display_gain_labels() -> tuple[str, ...]:
    return tuple(f"{value:g}x" for value in DISPLAY_GAIN_CHOICES)


def sweep_speed_labels() -> tuple[str, ...]:
    return tuple(f"{value} mm/s" for value in SWEEP_SPEED_CHOICES)


def parse_display_window(label: str) -> float:
    return nearest_choice(_leading_float(label, 8.0), DISPLAY_WINDOW_CHOICES)


def parse_display_gain(label: str) -> float:
    return nearest_choice(_leading_float(label, 1.0), DISPLAY_GAIN_CHOICES)


def parse_sweep_speed(label: str) -> int:
    return int(nearest_choice(_leading_float(label, 25.0), tuple(float(value) for value in SWEEP_SPEED_CHOICES)))


def ecg_paper_grid_spec(settings: EcgDisplaySettings) -> dict[str, float | str]:
    normalized = settings.normalized()
    major_x_seconds = 0.2 if normalized.sweep_speed_mm_s == 25 else 0.1
    minor_x_seconds = major_x_seconds / 5.0
    return {
        "major_x_seconds": major_x_seconds,
        "minor_x_seconds": minor_x_seconds,
        "major_color": "#F3A6A6",
        "minor_color": "#F9D5D5",
        "major_linewidth": 0.65,
        "minor_linewidth": 0.35,
        "major_alpha": 0.58,
        "minor_alpha": 0.45,
    }


def display_mode_label(settings: EcgDisplaySettings, filters: SoftwareFilterSettings) -> str:
    normalized = settings.normalized()
    active_filters: list[str] = []
    if filters.bandpass_enabled:
        active_filters.append("bandpass")
    else:
        if filters.highpass_enabled:
            active_filters.append("HP")
        if filters.notch_enabled:
            active_filters.append("notch")
        if filters.lowpass_enabled:
            active_filters.append("LP")
    filter_text = "raw" if not active_filters else "+".join(active_filters)
    return f"{filter_text} | {normalized.gain:g}x | {normalized.time_window_seconds:g}s | {normalized.sweep_speed_mm_s} mm/s"


def _leading_float(label: str, default: float) -> float:
    token = label.strip().split(maxsplit=1)[0].rstrip("x")
    try:
        return float(token)
    except ValueError:
        return default
