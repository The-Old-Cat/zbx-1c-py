"""
Файл инъекции зависимостей для zbx_1c API.
"""

from typing import Dict, Any
from fastapi import HTTPException, status
from pydantic import BaseModel


# Модели данных для валидации
class ClusterRequest(BaseModel):
    cluster_id: str


class ClusterResponse(BaseModel):
    cluster_id: str
    status: str
    data: Dict[str, Any] = {}


# Зависимости для аутентификации (заглушка)
def get_current_user():
    # Здесь может быть реализация аутентификации
    return {"username": "admin"}


# Зависимости для настроек
def get_settings():
    from zbx_1c.core.config import settings

    return settings


# Зависимости для проверки существования кластера
def validate_cluster_id(cluster_id: str) -> str:
    from zbx_1c.core.config import settings
    from zbx_1c.monitoring.cluster.manager import ClusterManager

    manager = ClusterManager(settings)
    clusters = manager.discover_clusters()
    cluster_ids = [str(c.get("id", "")) for c in clusters]
    if cluster_id not in cluster_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Cluster with ID {cluster_id} not found"
        )
    return cluster_id


# Зависимость для проверки доступности RAS
def check_ras_availability():
    from zbx_1c.utils.net import check_port
    from zbx_1c.core.config import settings

    is_available = check_port(settings.rac_host, settings.rac_port, settings.rac_timeout)
    if not is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="RAS service is not available"
        )
    return {"available": is_available, "host": settings.rac_host, "port": settings.rac_port}
