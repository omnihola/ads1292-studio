"""Tests for the ADS1292R lead-off electrode decoder.

Bit layout is verified against SLAU384A p.27 ("Lead Off Status" table) and the
ADS1292R LOFF_STAT register:

    bit0 IN1P_OFF -> LA   bit1 IN1N_OFF -> RA
    bit2 IN2P_OFF -> LL   bit3 IN2N_OFF -> RA   bit4 RLD_STAT -> RL (drive)
"""
from __future__ import annotations

from ads1292_studio.lead_off import (
    electrodes_off,
    is_lead_off,
    summarize_lead_off,
)


def test_all_connected_reports_no_electrodes_off() -> None:
    assert electrodes_off(0x00) == ()
    assert is_lead_off(0x00) is False


def test_no_electrode_bench_capture_reports_all_sense_electrodes_off() -> None:
    # 0x0F = all four input lead-off bits set (nothing connected)
    assert electrodes_off(0x0F) == ("RA", "LA", "LL")
    assert is_lead_off(0x0F) is True


def test_la_off_maps_to_in1p_bit0() -> None:
    assert electrodes_off(0x01) == ("LA",)


def test_ll_off_maps_to_in2p_bit2() -> None:
    assert electrodes_off(0x04) == ("LL",)


def test_ra_off_detected_via_either_negative_input() -> None:
    # RA drives both IN1N (bit1) and IN2N (bit3); either indicates RA off
    assert electrodes_off(0x02) == ("RA",)
    assert electrodes_off(0x08) == ("RA",)
    assert electrodes_off(0x0A) == ("RA",)


def test_rld_bit_is_not_a_sense_electrode() -> None:
    # bit4 (RLD_STAT) must not register as a contact-electrode lead-off
    assert electrodes_off(0x10) == ()
    assert is_lead_off(0x10) is False


def test_electrode_order_is_clinical_ra_la_ll() -> None:
    assert electrodes_off(0x07) == ("RA", "LA", "LL")


def test_summarize_lead_off_counts_per_electrode_and_percent() -> None:
    # 4 samples: clean, LA off, RA off, clean
    summary = summarize_lead_off([0x00, 0x01, 0x02, 0x00])
    assert summary.total_samples == 4
    assert summary.any_off_samples == 2
    assert summary.electrode_bad_samples["LA"] == 1
    assert summary.electrode_bad_samples["RA"] == 1
    assert summary.electrode_bad_samples["LL"] == 0
    assert summary.electrode_off_percent["LA"] == 25.0
    assert summary.electrode_off_percent["RA"] == 25.0


def test_summarize_lead_off_handles_empty_input() -> None:
    summary = summarize_lead_off([])
    assert summary.total_samples == 0
    assert summary.any_off_samples == 0
    assert summary.electrode_bad_samples == {"RA": 0, "LA": 0, "LL": 0}
    assert summary.electrode_off_percent == {"RA": 0.0, "LA": 0.0, "LL": 0.0}
