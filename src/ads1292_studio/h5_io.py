"""Canonical HDF5 recording container — the single source of truth.

One ``.h5`` per recording holds the raw sample arrays as datasets plus the full
metadata bundle (the same structure as the legacy JSON) as one JSON blob, with
per-array SHA-256 hashes for integrity. CSV/XLSX/JSON are derived on demand
from this file (see ``h5_export``); the live CSV journal is kept separately for
crash safety during acquisition.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from ads1292_studio.calibration import Calibration
from ads1292_studio.events import EventMarker
from ads1292_studio.metadata import SessionMetadata
from ads1292_studio.models import Recording, StreamSample
from ads1292_studio.protocol import TestProtocol
from ads1292_studio.quality_gate import QualityGate
from ads1292_studio.recording_bundle import (
    AcquisitionProvenance,
    RecordingProcessingSettings,
    build_recording_bundle,
)

H5_SCHEMA = "ads1292-h5/1"


def recording_h5_path(csv_path: Path | str) -> Path:
    return Path(csv_path).with_suffix(".h5")


def is_recording_h5_path(path: Path | str) -> bool:
    return Path(path).suffix.lower() == ".h5"


def write_recording_h5(
    csv_path: Path | str,
    *,
    samples: tuple[StreamSample, ...] | list[StreamSample],
    sample_rate_hz: float,
    metadata: SessionMetadata,
    events: tuple[EventMarker, ...] | list[EventMarker],
    calibration: Calibration,
    acquisition: AcquisitionProvenance,
    protocol: TestProtocol,
    quality_gate: QualityGate,
    processing: RecordingProcessingSettings,
    created_at: str = "",
    extra_attrs: dict[str, float] | None = None,
) -> Path:
    """Write the canonical .h5 container next to the CSV journal.

    ``extra_attrs`` is an extensible map of scalar provenance values written as
    top-level HDF5 attributes (e.g. measured effective_sample_rate_hz).
    """
    import h5py  # local import keeps h5py optional until actually used

    samples = tuple(samples)
    bundle = build_recording_bundle(
        csv_path=csv_path,
        metadata=metadata,
        events=tuple(events),
        calibration=calibration,
        acquisition=acquisition,
        protocol=protocol,
        quality_gate=quality_gate,
        processing=processing,
        sample_rate_hz=sample_rate_hz,
        created_at=created_at,
    )

    arrays = _sample_arrays(samples)
    output = recording_h5_path(csv_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(output, "w") as f:
        f.attrs["schema"] = H5_SCHEMA
        f.attrs["created_at"] = created_at
        f.attrs["sample_rate_hz"] = float(sample_rate_hz)
        f.attrs["csv_name"] = Path(csv_path).name
        f.attrs["sample_count"] = len(samples)
        # convenience: surface the live calibration scale as a top-level attr
        live_cal = (bundle.get("acquisition") or {}).get("live_calibration") or {}
        live_scale = live_cal.get("mean_uv_per_count")
        if live_scale is not None:
            f.attrs["live_uv_per_count"] = float(live_scale)
        for key, value in (extra_attrs or {}).items():
            if value is not None:
                f.attrs[key] = float(value)
        group = f.create_group("samples")
        for name, array in arrays.items():
            group.create_dataset(name, data=array, compression="gzip", shuffle=True)
        # full metadata bundle as a single JSON blob (reuses existing readers)
        f.create_dataset("bundle_json", data=json.dumps(bundle))
        integrity = f.create_group("integrity")
        for name, array in arrays.items():
            integrity.attrs[f"sha256_{name}"] = hashlib.sha256(array.tobytes()).hexdigest()
    return output


def read_recording_h5(path: Path | str) -> tuple[Recording, dict[str, Any]]:
    """Return the reconstructed Recording and the metadata bundle dict."""
    import h5py

    with h5py.File(Path(path), "r") as f:
        schema = _as_text(f.attrs.get("schema", ""))
        if schema != H5_SCHEMA:
            raise ValueError(
                f"unrecognized HDF5 schema {schema!r} (expected {H5_SCHEMA!r}) in {Path(path).name}"
            )
        if "samples" not in f or "bundle_json" not in f:
            raise ValueError(f"HDF5 file is missing required groups: {Path(path).name}")
        group = f["samples"]
        required = ("timestamp", "ch1", "ch2", "status_byte", "board_heart_rate", "board_respiration_rate")
        missing = [name for name in required if name not in group]
        if missing:
            raise ValueError(f"HDF5 samples group missing datasets {missing}: {Path(path).name}")
        timestamp = group["timestamp"][:]
        ch1 = group["ch1"][:]
        ch2 = group["ch2"][:]
        status = group["status_byte"][:]
        bhr = group["board_heart_rate"][:]
        brr = group["board_respiration_rate"][:]
        sample_rate_hz = float(f.attrs["sample_rate_hz"])
        bundle = json.loads(_as_text(f["bundle_json"][()]))

    h5_path = Path(path)
    samples = tuple(
        StreamSample(
            timestamp=float(timestamp[i]),
            ch1=int(ch1[i]),
            ch2=int(ch2[i]),
            board_heart_rate=int(bhr[i]),
            board_respiration_rate=int(brr[i]),
            status_byte=int(status[i]),
            sample_index=i,
        )
        for i in range(len(timestamp))
    )
    return Recording(path=h5_path, samples=samples, sample_rate_hz=sample_rate_hz), bundle


def _sample_arrays(samples: tuple[StreamSample, ...]) -> dict[str, np.ndarray]:
    return {
        "timestamp": np.array([s.timestamp for s in samples], dtype=np.float64),
        "ch1": np.array([s.ch1 for s in samples], dtype=np.int32),
        "ch2": np.array([s.ch2 for s in samples], dtype=np.int32),
        "status_byte": np.array([s.status_byte for s in samples], dtype=np.uint16),
        "board_heart_rate": np.array([s.board_heart_rate for s in samples], dtype=np.int16),
        "board_respiration_rate": np.array([s.board_respiration_rate for s in samples], dtype=np.int16),
    }


def _as_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)
