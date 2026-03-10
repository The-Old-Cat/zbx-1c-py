"""Менеджер кластеров 1С"""

import socket
from typing import Any, Dict, List, Optional

from ...core.config import RacConfig
from ...utils.rac_client import check_ras_availability, discover_clusters, execute_rac_command


class ClusterManager:
    """
    Менеджер для управления кластерами 1С.

    Args:
        config: Конфигурация RAC.
    """

    def __init__(self, config: Optional[RacConfig] = None):
        self.config = config or RacConfig()

    def get_clusters(self) -> List[Dict[str, Any]]:
        """
        Получить список кластеров.

        Returns:
            Список кластеров.
        """
        return discover_clusters(
            self.config.rac_path,
            self.config.rac_host,
            self.config.rac_port,
            self.config.rac_timeout,
        )

    def get_cluster(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить информацию о конкретном кластере.

        Args:
            cluster_id: UUID кластера.

        Returns:
            Информация о кластере или None.
        """
        clusters = self.get_clusters()

        for cluster in clusters:
            if cluster.get("id") == cluster_id:
                return cluster

        return None

    def check_cluster_status(self, cluster_id: str) -> str:
        """
        Проверить статус кластера.

        Args:
            cluster_id: UUID кластера.

        Returns:
            'available', 'unavailable', или 'unknown'.
        """
        cluster = self.get_cluster(cluster_id)

        if not cluster:
            return "unknown"

        host = cluster.get("host", self.config.rac_host)
        port = int(cluster.get("port", self.config.rac_port))

        if check_ras_availability(host, port, self.config.rac_timeout):
            return "available"
        else:
            return "unavailable"

    def get_cluster_metrics(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить метрики кластера для Zabbix.

        Args:
            cluster_id: UUID кластера.

        Returns:
            Метрики кластера.
        """
        from ...monitoring.infobase.monitor import InfobaseMonitor
        from ...monitoring.jobs.reader import JobReader
        from ...monitoring.session.collector import SessionCollector

        cluster = self.get_cluster(cluster_id)
        if not cluster:
            return None

        # Получаем данные
        ib_monitor = InfobaseMonitor(self.config)
        session_collector = SessionCollector(self.config)
        job_reader = JobReader(self.config)

        # Статистика
        ib_stats = ib_monitor.get_statistics(cluster_id)
        session_stats = session_collector.get_statistics(cluster_id)
        job_stats = job_reader.get_statistics(cluster_id)

        # Вычисляем процент заполнения сессий
        session_limit = ib_stats.get("total_session_limit", 0)
        total_sessions = session_stats.get("total", 0)
        session_percent = 0.0
        if session_limit > 0:
            session_percent = round((total_sessions / session_limit) * 100, 2)

        return {
            "cluster": {
                "id": cluster.get("id"),
                "name": cluster.get("name", "unknown"),
                "host": cluster.get("host", self.config.rac_host),
                "port": cluster.get("port", self.config.rac_port),
                "status": cluster.get("status", "unknown"),
            },
            "metrics": {
                "total_sessions": total_sessions,
                "active_sessions": session_stats.get("active", 0),
                "total_jobs": job_stats.get("total", 0),
                "active_jobs": job_stats.get("active", 0),
                "total_infobases": ib_stats.get("total", 0),
                "session_limit": session_limit,
                "session_percent": session_percent,
            },
        }

    def get_all_clusters_metrics(self) -> List[Dict[str, Any]]:
        """
        Получить метрики всех кластеров.

        Returns:
            Список метрик для каждого кластера.
        """
        clusters = self.get_clusters()
        results = []

        for cluster in clusters:
            metrics = self.get_cluster_metrics(cluster["id"])
            if metrics:
                results.append(metrics)

        return results

    def get_server_memory(self) -> Dict[str, Any]:
        """
        Получить память процессов 1С (rphost, rmngr, ragent).

        Returns:
            Информация о памяти процессов.
        """
        import psutil
        import sys

        result = {
            "rphost": {"count": 0, "memory_mb": 0},
            "rmngr": {"count": 0, "memory_mb": 0},
            "ragent": {"count": 0, "memory_mb": 0},
            "total_mb": 0,
        }

        # Имена процессов для разных ОС
        if sys.platform == "win32":
            # Windows
            process_names = {
                "rphost": ["rphost", "1cv8c", "1cv8"],
                "rmngr": ["rmngr", "ragent"],
                "ragent": ["ragent"],
            }
        else:
            # Linux
            process_names = {
                "rphost": ["rphost", "1cv8c", "1cv8"],
                "rmngr": ["rmngr", "ragent"],
                "ragent": ["ragent"],
            }

        for proc in psutil.process_iter(["name", "memory_info"]):
            try:
                proc_name = proc.info["name"].lower()
                memory_mb = proc.info["memory_info"].rss / 1024 / 1024

                for key, names in process_names.items():
                    if any(name in proc_name for name in names):
                        result[key]["count"] += 1
                        result[key]["memory_mb"] += memory_mb
                        result["total_mb"] += memory_mb
                        break

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Округляем значения
        for key in ["rphost", "rmngr", "ragent"]:
            result[key]["memory_mb"] = round(result[key]["memory_mb"], 2)
        result["total_mb"] = round(result["total_mb"], 2)

        return result
