"""Decode ADS1292R lead-off status into electrode-level contact information.

The ADS1292RECG-FE firmware reports a per-conversion status byte whose low five
bits mirror the ADS1292R ``LOFF_STAT`` register::

    bit0 IN1P_OFF   bit1 IN1N_OFF   bit2 IN2P_OFF   bit3 IN2N_OFF   bit4 RLD_STAT

Board electrode wiring (SLAU384A p.27, "Lead Off Status" table)::

    LA -> IN1P            (bit0)
    RA -> IN1N and IN2N   (bit1 or bit3)   # shared negative reference
    LL -> IN2P            (bit2)
    RL -> RLD drive       (bit4, not a sense electrode)

The no-electrode bench capture (status 0x0F = all four input bits set) confirms
the low nibble holds the four input lead-off flags. The LA/LL distinction
depends on the intra-nibble bit order; confirm with a single-electrode-off bench
test if precise per-electrode attribution is critical.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

# LOFF_STAT bit masks (low nibble = sense-electrode lead-off flags).
IN1P_OFF = 0x01
IN1N_OFF = 0x02
IN2P_OFF = 0x04
IN2N_OFF = 0x08
RLD_STAT = 0x10
LEAD_OFF_MASK = 0x0F

# Clinical display order. RA is the shared negative reference (IN1N and IN2N).
ELECTRODE_ORDER = ("RA", "LA", "LL")
ELECTRODE_BITS = {
    "RA": IN1N_OFF | IN2N_OFF,
    "LA": IN1P_OFF,
    "LL": IN2P_OFF,
}


def electrodes_off(status_byte: int) -> tuple[str, ...]:
    """Return the electrodes flagged as off, in clinical order (RA, LA, LL)."""
    bits = int(status_byte) & LEAD_OFF_MASK
    return tuple(name for name in ELECTRODE_ORDER if bits & ELECTRODE_BITS[name])


def is_lead_off(status_byte: int) -> bool:
    """True when any sense electrode (not RLD) is flagged off."""
    return bool(int(status_byte) & LEAD_OFF_MASK)


@dataclass(frozen=True)
class LeadOffSummary:
    """Per-electrode lead-off statistics over a run of status bytes."""

    total_samples: int
    any_off_samples: int
    electrode_bad_samples: dict[str, int]
    electrode_off_percent: dict[str, float]


def summarize_lead_off(status_bytes: Iterable[int]) -> LeadOffSummary:
    """Aggregate per-electrode off counts and percentages across samples."""
    bad = {name: 0 for name in ELECTRODE_ORDER}
    total = 0
    any_off = 0
    for raw in status_bytes:
        total += 1
        offs = electrodes_off(raw)
        if offs:
            any_off += 1
        for name in offs:
            bad[name] += 1
    if total == 0:
        percent = {name: 0.0 for name in ELECTRODE_ORDER}
    else:
        percent = {name: 100.0 * bad[name] / total for name in ELECTRODE_ORDER}
    return LeadOffSummary(
        total_samples=total,
        any_off_samples=any_off,
        electrode_bad_samples=bad,
        electrode_off_percent=percent,
    )
