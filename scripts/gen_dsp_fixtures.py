from __future__ import annotations

from pathlib import Path

from ads1292_studio import signal_processing as sp
from scripts._fixture_signals import synthetic_ecg
from scripts.fixture_io import dump_fixture, floats

SR = 500.0
ABS_TOL = 1e-6
COEF_TOL = 1e-12


def generate(root: Path) -> list[Path]:
    out = Path(root) / "dsp"
    written: list[Path] = []

    coeff_specs = [
        ("coeffs_bandpass_500hz", sp._bandpass_coefficients(SR, 0.7, 35.0)),
        ("coeffs_highpass_500hz", sp._highpass_coefficients(SR, 0.5)),
        ("coeffs_lowpass_500hz", sp._lowpass_coefficients(SR, 40.0)),
        ("coeffs_notch_60hz_500hz", sp._notch_coefficients(SR, 60.0, 30.0)),
    ]
    for name, (b, a) in coeff_specs:
        written.append(_write(out / f"{name}.json", {
            "schema_version": 1, "category": "dsp_coefficients", "name": name,
            "oracle": {"function": f"ads1292_studio.signal_processing.{name.split('_')[1]}_coefficients"},
            "input": {"sample_rate_hz": SR},
            "output": {"b": floats(b), "a": floats(a)},
            "tolerance": {"kind": "abs", "value": COEF_TOL},
            "notes": "scipy butter(2)/iirnotch transfer-function coefficients",
        }))

    long_signal = synthetic_ecg(2000, SR)
    short_signal = synthetic_ecg(32, SR)        # short window -> filtfilt boundary stress
    tiny_signal = synthetic_ecg(8, SR)          # < 16 -> median-detrend fallback path

    filt_specs = [
        ("filtfilt_bandpass_long", "bandpass", long_signal, sp.bandpass(long_signal, SR)),
        ("filtfilt_bandpass_short_window", "bandpass", short_signal, sp.bandpass(short_signal, SR)),
        ("filtfilt_bandpass_tiny_fallback", "bandpass", tiny_signal, sp.bandpass(tiny_signal, SR)),
        ("filtfilt_notch_long", "notch", long_signal, sp.notch(long_signal, SR)),
        ("filtfilt_highpass_long", "highpass", long_signal, sp.highpass(long_signal, SR)),
        ("filtfilt_lowpass_long", "lowpass", long_signal, sp.lowpass(long_signal, SR)),
    ]
    for name, kind, sig, filtered in filt_specs:
        written.append(_write(out / f"{name}.json", {
            "schema_version": 1, "category": "dsp_filter_output", "name": name,
            "oracle": {"function": f"ads1292_studio.signal_processing.{kind}"},
            "input": {"signal": floats(sig), "sample_rate_hz": SR},
            "output": {"filtered": floats(filtered)},
            "tolerance": {"kind": "abs", "value": ABS_TOL},
            "notes": f"{kind} via scipy.signal.filtfilt; frozen input stored verbatim",
        }))
    return written


def _write(path: Path, payload: dict) -> Path:
    dump_fixture(payload, path)
    return path
