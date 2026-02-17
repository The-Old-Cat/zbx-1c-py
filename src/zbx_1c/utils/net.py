import socket
import re
from typing import Tuple
from urllib.parse import urlparse


def check_port(host: str, port: int, timeout: float = 5.0) -> bool:
    """
    Проверка доступности порта
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def parse_ras_address(address: str) -> Tuple[str, int]:
    """
    Парсинг адреса RAS
    Форматы:
    - host:port
    - host
    - http://host:port
    """
    if "://" in address:
        parsed = urlparse(address)
        host = parsed.hostname or "localhost"
        port = parsed.port or 1545
        return host, port

    if ":" in address:
        host, port_str = address.split(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            port = 1545
        return host, port

    return address, 1545


def is_valid_hostname(hostname: str) -> bool:
    """Проверка корректности имени хоста"""
    if len(hostname) > 255:
        return False

    if hostname[-1] == ".":
        hostname = hostname[:-1]

    allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))
