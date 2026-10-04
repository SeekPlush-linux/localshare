import socket
import psutil


def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def get_broadcast_addresses():
    addresses = set()
    interface_stats = psutil.net_if_stats()
    for interface, interface_addresses in psutil.net_if_addrs().items():
        if interface in interface_stats and not interface_stats[interface].isup:
            continue
        for address in interface_addresses:
            if (
                address.family == socket.AF_INET
                and address.broadcast
                and not address.address.startswith("127.")
            ):
                addresses.add(address.broadcast)
    return sorted(addresses) or ["255.255.255.255"]


def get_all_local_ips():
    try:
        hostname = socket.gethostname()
        _, _, ip_addresses = socket.gethostbyname_ex(hostname)
        return ip_addresses
    except Exception:
        return [get_local_ip()]
