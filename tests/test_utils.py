import socket
from pathlib import Path
from types import SimpleNamespace

import psutil

from utils import functions
from utils.constants import CHUNK_SIZE, DOWNLOAD_DIR


def test_get_local_ip_returns_loopback_when_socket_connect_fails(monkeypatch):
    class FakeSocket:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def connect(self, *args, **kwargs):
            raise OSError("network unavailable")

    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: FakeSocket())

    assert functions.get_local_ip() == "127.0.0.1"


def test_get_broadcast_addresses_filters_non_up_interfaces_and_invalid_addresses(monkeypatch):
    interface_stats = {
        "lo": SimpleNamespace(isup=False),
        "eth0": SimpleNamespace(isup=True),
    }
    interface_addrs = {
        "lo": [
            SimpleNamespace(
                family=socket.AF_INET,
                broadcast="127.0.0.1",
                address="127.0.0.1",
            )
        ],
        "eth0": [
            SimpleNamespace(
                family=socket.AF_INET,
                broadcast="192.168.1.255",
                address="192.168.1.10",
            ),
            SimpleNamespace(
                family=socket.AF_INET,
                broadcast=None,
                address="10.0.0.2",
            ),
            SimpleNamespace(
                family=socket.AF_INET,
                broadcast="127.0.0.1",
                address="127.0.0.1",
            ),
        ],
    }

    monkeypatch.setattr(psutil, "net_if_stats", lambda: interface_stats)
    monkeypatch.setattr(psutil, "net_if_addrs", lambda: interface_addrs)

    assert functions.get_broadcast_addresses() == ["192.168.1.255"]

    monkeypatch.setattr(psutil, "net_if_addrs", lambda: {})
    assert functions.get_broadcast_addresses() == ["255.255.255.255"]


def test_get_all_local_ips_uses_hostname_lookup(monkeypatch):
    monkeypatch.setattr(socket, "gethostname", lambda: "devbox")
    monkeypatch.setattr(
        socket,
        "gethostbyname_ex",
        lambda hostname: ("devbox", [], ["10.0.0.5", "10.0.0.6"]),
    )

    assert functions.get_all_local_ips() == ["10.0.0.5", "10.0.0.6"]


def test_get_all_local_ips_falls_back_to_local_ip(monkeypatch):
    monkeypatch.setattr(socket, "gethostname", lambda: "devbox")
    monkeypatch.setattr(socket, "gethostbyname_ex", lambda hostname: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(functions, "get_local_ip", lambda: "127.0.0.1")

    assert functions.get_all_local_ips() == ["127.0.0.1"]


def test_download_dir_and_chunk_size_constants_are_expected():
    assert DOWNLOAD_DIR == Path.home() / "Downloads" / "LocalShare"
    assert CHUNK_SIZE == 256 * 1024
