"""
Модуль для работы с кластерами 1С
"""

from zbx_1c.monitoring.cluster.manager import ClusterManager
from zbx_1c.monitoring.cluster.discovery import discover_clusters

__all__ = ["ClusterManager", "discover_clusters"]
