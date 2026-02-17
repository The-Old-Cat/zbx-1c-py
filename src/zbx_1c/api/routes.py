from fastapi import APIRouter, HTTPException, Path, Query
from typing import List, Optional, Dict, Any

from ..core.config import get_settings
from ..monitoring.cluster.manager import ClusterManager
from ..monitoring.session.collector import SessionCollector
from ..monitoring.jobs.reader import JobReader

router = APIRouter()


@router.get("/clusters/discovery", response_model=Dict[str, Any])
async def get_clusters_discovery():
    """
    Получение списка кластеров для Zabbix LLD
    """
    try:
        settings = get_settings()
        manager = ClusterManager(settings)
        clusters = manager.discover_clusters()

        return {"data": clusters}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clusters", response_model=List[Dict[str, Any]])
async def get_clusters():
    """
    Получение списка всех кластеров
    """
    try:
        settings = get_settings()
        manager = ClusterManager(settings)
        return manager.discover_clusters()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clusters/{cluster_id}/metrics", response_model=Dict[str, Any])
async def get_cluster_metrics_endpoint(cluster_id: str = Path(..., description="ID кластера")):
    """
    Получение метрик для конкретного кластера
    """
    try:
        settings = get_settings()
        manager = ClusterManager(settings)
        return manager.get_cluster_metrics(cluster_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clusters/{cluster_id}/sessions")
async def get_cluster_sessions(
    cluster_id: str = Path(..., description="ID кластера"),
    infobase: Optional[str] = Query(None, description="Фильтр по информационной базе"),
):
    """
    Получение списка сессий кластера
    """
    try:
        settings = get_settings()
        collector = SessionCollector(settings)
        sessions = collector.get_sessions(cluster_id, infobase)
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clusters/{cluster_id}/jobs")
async def get_cluster_jobs(
    cluster_id: str = Path(..., description="ID кластера"),
    infobase: Optional[str] = Query(None, description="Фильтр по информационной базе"),
):
    """
    Получение списка фоновых заданий кластера
    """
    try:
        settings = get_settings()
        reader = JobReader(settings)
        jobs = reader.get_jobs(cluster_id, infobase)
        return jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ras/status")
async def get_ras_status():
    """
    Проверка статуса RAS сервиса
    """
    try:
        settings = get_settings()
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(settings.rac_timeout)
        result = sock.connect_ex((settings.rac_host, settings.rac_port))
        sock.close()
        available = result == 0

        return {
            "host": settings.rac_host,
            "port": settings.rac_port,
            "available": available,
            "rac_path": str(settings.rac_path),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
