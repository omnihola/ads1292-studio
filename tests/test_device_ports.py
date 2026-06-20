from __future__ import annotations

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
