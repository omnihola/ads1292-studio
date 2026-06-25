"""Guards the frozen fixtures against drift from the pinned Python oracle.

This is the P-1 acceptance test. It does NOT implement a C++ reader; it proves
the stored goldens are a faithful, reproducible capture of the current oracle.
A future C++/Catch2 reader will consume the same JSON envelopes (see
docs/superpowers/specs/2026-06-24-p1-golden-fixtures-design.md, "C++ reader
interface note").
"""
from pathlib import Path
import json

import numpy as np
import pytest

from scripts.validate_golden_fixtures import validate_root

ROOT = Path(__file__).resolve().parent / "fixtures" / "golden"


def test_committed_fixtures_pass_validation():
    assert validate_root(ROOT) == []


def test_device_stream_fixture_reproduces():
    from ads1292_studio.device import parse_stream_payload
    fx = json.loads((ROOT / "device_parser" / "stream_payload_nominal.json").read_text())
    payload = bytes.fromhex(fx["input"]["payload_hex"])
    samples = parse_stream_payload(payload, fx["input"]["start_timestamp"],
                                   fx["input"]["sample_rate_hz"], fx["input"]["start_index"])
    assert [s.ch1 for s in samples] == [row["ch1"] for row in fx["output"]["samples"]]


def test_dsp_filtfilt_fixture_reproduces_within_tolerance():
    from ads1292_studio.signal_processing import bandpass
    fx = json.loads((ROOT / "dsp" / "filtfilt_bandpass_long.json").read_text())
    recomputed = bandpass(fx["input"]["signal"], fx["input"]["sample_rate_hz"])
    expected = np.asarray(fx["output"]["filtered"], dtype=float)
    assert np.allclose(recomputed, expected, atol=fx["tolerance"]["value"])
