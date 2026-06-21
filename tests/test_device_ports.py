from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ads1292_studio import device


def _port(
    *,
    name: str,
    description: str = "",
    hwid: str = "",
    vid: int | None = None,
    pid: int | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        device=name,
        description=description,
        hwid=hwid,
        vid=vid,
        pid=pid,
    )


def test_list_ads_ports_includes_macos_usbmodem_candidate(monkeypatch) -> None:
    monkeypatch.setattr(device, "_macos_usb_candidate_paths", lambda: ())
    monkeypatch.setattr(
        device.list_ports,
        "comports",
        lambda: [
            _port(name="/dev/cu.Bluetooth-Incoming-Port", description="Bluetooth"),
            _port(name="/dev/cu.usbmodem214301", description="USB Serial Device"),
        ],
    )

    ports = device.list_ads_ports()

    assert [port.device for port in ports] == ["/dev/cu.usbmodem214301"]


def test_list_ads_ports_keeps_exact_ti_ads_identity(monkeypatch) -> None:
    monkeypatch.setattr(device, "_macos_usb_candidate_paths", lambda: ())
    monkeypatch.setattr(
        device.list_ports,
        "comports",
        lambda: [
            _port(
                name="/dev/cu.debug",
                description="Debug probe",
                vid=device.VID_TI,
                pid=device.PID_ADS1X9X,
            ),
            _port(name="/dev/cu.usbserial110", description="USB Serial"),
        ],
    )

    ports = device.list_ads_ports()

    assert [port.device for port in ports] == ["/dev/cu.debug", "/dev/cu.usbserial110"]


def test_list_ads_ports_falls_back_to_macos_dev_nodes_when_pyserial_returns_empty(monkeypatch) -> None:
    monkeypatch.setattr(device.list_ports, "comports", lambda: [])
    monkeypatch.setattr(
        device,
        "_macos_usb_candidate_paths",
        lambda: (Path("/dev/cu.usbmodem214301"), Path("/dev/cu.usbserial110")),
    )

    ports = device.list_ads_ports()

    assert [port.device for port in ports] == ["/dev/cu.usbmodem214301", "/dev/cu.usbserial110"]
