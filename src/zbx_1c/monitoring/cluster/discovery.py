"""
Обнаружение кластеров 1С
"""

import socket
from typing import List
from loguru import logger

from ...core.config import Settings
from ...core.models import ClusterInfo
from ...utils.rac_client import RACClient
from ...utils.converters import parse_clusters


def check_cluster_status(host: str, port: int, timeout: int = 5) -> str:
    """
    Проверка статуса кластера через подключение к рабочему серверу 1С

    Args:
        host: Хост рабочего сервера
        port: Порт рабочего сервера
        timeout: Таймаут подключения

    Returns:
        Статус кластера: "available", "unavailable" или "unknown"
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            return "available"
        else:
            return "unavailable"
    except Exception as e:
        logger.warning(f"Failed to check cluster status for {host}:{port}: {e}")
        return "unknown"


def discover_clusters(settings: Settings) -> List[ClusterInfo]:
    """
    Обнаружение кластеров 1С через RAS

    Args:
        settings: Настройки приложения

    Returns:
        Список кластеров
    """
    logger.debug(f"Discovering clusters using {settings.rac_path}")

    rac = RACClient(settings)
    # Формируем команду: rac.exe cluster list host:port
    cmd = [
        str(settings.rac_path),
        "cluster",
        "list",
        f"{settings.rac_host}:{settings.rac_port}",
    ]

    result = rac.execute(cmd)
    if not result or result["returncode"] != 0 or not result["stdout"]:
        logger.error("Failed to discover clusters")
        return []

    clusters_data = parse_clusters(result["stdout"])
    clusters = []

    for data in clusters_data:
        try:
            # Получаем базовую информацию
            cluster_dict = {
                "id": data.get("cluster") or data.get("id"),
                "name": data.get("name", "unknown"),
                "host": data.get("host", settings.rac_host),
                "port": int(data.get("port", 1541)),
            }

            # Определяем статус кластера
            status = check_cluster_status(
                cluster_dict["host"], cluster_dict["port"], timeout=settings.rac_timeout
            )
            cluster_dict["status"] = status

            cluster = ClusterInfo.from_dict(cluster_dict)
            clusters.append(cluster)
            logger.debug(f"Found cluster: {cluster.name} ({cluster.id}) [status: {status}]")
        except Exception as e:
            logger.warning(f"Failed to parse cluster data: {e}, data: {data}")

    logger.info(f"Discovered {len(clusters)} clusters")
    return clusters
