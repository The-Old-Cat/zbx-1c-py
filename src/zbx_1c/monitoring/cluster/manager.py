"""
Менеджер для работы с кластерами 1С
Работает точно так же как в run_direct.py
"""

from typing import List, Dict, Optional
from loguru import logger

from ...core.config import Settings
from ...utils.rac_client import RACClient
from ...utils.converters import (
    parse_clusters,
    parse_infobases,
    parse_sessions,
    parse_jobs,
)


class ClusterManager:
    """Менеджер для работы с кластерами 1С"""

    def __init__(self, settings: Settings):
        """
        Инициализация менеджера

        Args:
            settings: Настройки приложения
        """
        self.settings = settings
        self.rac = RACClient(settings)
        self._clusters_cache: Optional[List[Dict]] = None

    def discover_clusters(self, use_cache: bool = True) -> List[Dict]:
        """
        Обнаружение кластеров - точная копия discover_clusters из run_direct.py

        Args:
            use_cache: Использовать кэш

        Returns:
            Список кластеров (в формате dict)
        """
        if use_cache and self._clusters_cache is not None:
            return self._clusters_cache

        # Формируем команду: rac.exe cluster list host:port
        cmd = [
            str(self.settings.rac_path),
            "cluster",
            "list",
            f"{self.settings.rac_host}:{self.settings.rac_port}",
        ]

        result = self.rac.execute(cmd)

        if not result or result["returncode"] != 0 or not result["stdout"]:
            logger.error("Не удалось получить список кластеров")
            return []

        # Парсим вывод
        clusters_data = parse_clusters(result["stdout"])
        clusters = []

        for data in clusters_data:
            try:
                cluster = {
                    "id": data.get("cluster") or data.get("id"),
                    "name": data.get("name", "unknown"),
                    "host": data.get("host", self.settings.rac_host),
                    "port": data.get("port", self.settings.rac_port),
                    "status": "unknown",
                }

                if cluster["id"]:
                    clusters.append(cluster)
                    logger.debug(f"Найден кластер: {cluster['name']} ({cluster['id']})")
            except Exception as e:
                logger.error(f"Ошибка парсинга кластера: {e}")

        self._clusters_cache = clusters
        return clusters

    def get_infobases(self, cluster_id: str) -> List[Dict]:
        """
        Получение информационных баз - точная копия get_infobases из run_direct.py

        Args:
            cluster_id: ID кластера

        Returns:
            Список информационных баз
        """
        cmd = [
            str(self.settings.rac_path),
            "infobase",
            "summary",
            "list",
            f"--cluster={cluster_id}",
        ]

        # Добавляем аутентификацию если есть
        if self.settings.user_name:
            cmd.append(f"--cluster-user={self.settings.user_name}")
        if self.settings.user_pass:
            cmd.append(f"--cluster-pwd={self.settings.user_pass}")

        cmd.append(f"{self.settings.rac_host}:{self.settings.rac_port}")

        result = self.rac.execute(cmd)
        if result and result["returncode"] == 0 and result["stdout"]:
            return parse_infobases(result["stdout"])

        return []

    def get_sessions(self, cluster_id: str) -> List[Dict]:
        """
        Получение сессий - точная копия get_sessions из run_direct.py

        Args:
            cluster_id: ID кластера

        Returns:
            Список сессий
        """
        cmd = [
            str(self.settings.rac_path),
            "session",
            "list",
            f"--cluster={cluster_id}",
        ]

        # Добавляем аутентификацию если есть
        if self.settings.user_name:
            cmd.append(f"--cluster-user={self.settings.user_name}")
        if self.settings.user_pass:
            cmd.append(f"--cluster-pwd={self.settings.user_pass}")

        cmd.append(f"{self.settings.rac_host}:{self.settings.rac_port}")

        result = self.rac.execute(cmd)
        if result and result["returncode"] == 0 and result["stdout"]:
            return parse_sessions(result["stdout"])

        return []

    def get_jobs(self, cluster_id: str) -> List[Dict]:
        """
        Получение фоновых заданий - точная копия get_jobs из run_direct.py

        Args:
            cluster_id: ID кластера

        Returns:
            Список фоновых заданий
        """
        cmd = [
            str(self.settings.rac_path),
            "job",
            "list",
            f"--cluster={cluster_id}",
        ]

        # Добавляем аутентификацию если есть
        if self.settings.user_name:
            cmd.append(f"--cluster-user={self.settings.user_name}")
        if self.settings.user_pass:
            cmd.append(f"--cluster-pwd={self.settings.user_pass}")

        cmd.append(f"{self.settings.rac_host}:{self.settings.rac_port}")

        result = self.rac.execute(cmd)
        if result and result["returncode"] == 0 and result["stdout"]:
            return parse_jobs(result["stdout"])

        # Если job list не поддерживается, возвращаем пустой список
        return []

    def get_cluster_metrics(self, cluster_id: str) -> Optional[Dict]:
        """
        Получение метрик кластера

        Args:
            cluster_id: ID кластера

        Returns:
            Метрики кластера в формате dict
        """
        # Получаем информацию о кластере
        clusters = self.discover_clusters()
        cluster = None
        for c in clusters:
            if c["id"] == cluster_id:
                cluster = c
                break

        if not cluster:
            logger.error(f"Кластер {cluster_id} не найден")
            return None

        # Получаем сессии и задания
        sessions = self.get_sessions(cluster_id)
        jobs = self.get_jobs(cluster_id)

        # Подсчет метрик
        total_sessions = len(sessions)
        active_sessions = sum(
            1 for s in sessions if s.get("session-id") and s.get("hibernate") == "no"
        )

        total_jobs = len(jobs)
        active_jobs = sum(1 for j in jobs if j.get("status") == "running")

        return {
            "cluster": {
                "id": cluster["id"],
                "name": cluster["name"],
                "status": cluster["status"],
            },
            "metrics": {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_jobs": total_jobs,
                "active_jobs": active_jobs,
            },
        }
