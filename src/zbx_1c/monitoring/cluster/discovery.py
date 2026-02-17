"""
Обнаружение кластеров 1С
"""

from typing import List
from loguru import logger

from ...core.config import Settings
from ...core.models import ClusterInfo
from ...utils.rac_client import RACClient
from ...utils.converters import parse_clusters


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
            cluster = ClusterInfo.from_dict(data)
            clusters.append(cluster)
            logger.debug(f"Found cluster: {cluster.name} ({cluster.id})")
        except Exception as e:
            logger.warning(f"Failed to parse cluster data: {e}, data: {data}")

    logger.info(f"Discovered {len(clusters)} clusters")
    return clusters
