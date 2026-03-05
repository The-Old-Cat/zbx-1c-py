"""
RAC клиент для выполнения команд.
"""

import socket
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .converters import decode_output


def execute_rac_command(
    rac_path: Path,
    cmd_parts: List[str],
    timeout: int = 30,
) -> Optional[Dict[str, Any]]:
    """
    Выполнение команды rac.

    Args:
        rac_path: Путь к исполняемому файлу rac.
        cmd_parts: Аргументы командной строки.
        timeout: Таймаут выполнения в секундах.

    Returns:
        Словарь с returncode, stdout, stderr или None при ошибке.
    """
    try:
        cmd = [str(rac_path)] + cmd_parts
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
        )

        return {
            "returncode": result.returncode,
            "stdout": decode_output(result.stdout),
            "stderr": decode_output(result.stderr),
        }

    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None


def check_ras_availability(host: str, port: int, timeout: int = 30) -> bool:
    """
    Проверка доступности RAS сервиса.

    Args:
        host: Хост RAS.
        port: Порт RAS.
        timeout: Таймаут подключения в секундах.

    Returns:
        True если RAS доступен, иначе False.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def discover_clusters(
    rac_path: Path,
    rac_host: str,
    rac_port: int,
    timeout: int = 30,
) -> List[Dict[str, Any]]:
    """
    Обнаружение кластеров 1С.

    Args:
        rac_path: Путь к rac.
        rac_host: Хост RAS.
        rac_port: Порт RAS.
        timeout: Таймаут выполнения.

    Returns:
        Список обнаруженных кластеров.
    """
    from .converters import parse_rac_output

    cmd_parts = [
        "cluster",
        "list",
        f"{rac_host}:{rac_port}",
    ]

    result = execute_rac_command(rac_path, cmd_parts, timeout)

    if not result or result["returncode"] != 0 or not result["stdout"]:
        return []

    clusters_data = parse_rac_output(result["stdout"])
    clusters = []

    for data in clusters_data:
        try:
            cluster = {
                "id": data.get("cluster"),
                "name": data.get("name", "unknown"),
                "host": data.get("host", rac_host),
                "port": int(data.get("port", rac_port)),
                "status": "unknown",
            }

            if cluster["id"]:
                # Проверяем статус
                if check_ras_availability(cluster["host"], cluster["port"], timeout):
                    cluster["status"] = "available"
                else:
                    cluster["status"] = "unavailable"

                clusters.append(cluster)

        except Exception:
            continue

    return clusters
