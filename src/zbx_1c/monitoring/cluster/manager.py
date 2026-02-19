"""
Менеджер для работы с кластерами 1С
Работает точно так же как в run_direct.py
"""

import socket
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
                    "status": check_cluster_status(
                        data.get("host", self.settings.rac_host),
                        int(data.get("port", self.settings.rac_port)),
                        timeout=self.settings.rac_timeout,
                    ),
                }

                if cluster["id"]:
                    clusters.append(cluster)
                    logger.debug(
                        f"Найден кластер: {cluster['name']} ({cluster['id']}) [status: {cluster['status']}]"
                    )
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
        Получение фоновых заданий через connection list

        В версиях 1С до 8.3.24 нет команды 'job list',
        поэтому получаем задания из connection list:
        - BackgroundJob — фоновые задания пользователей
        - SystemBackgroundJob — системные фоновые задания
        - JobScheduler — планировщик регламентных заданий

        Args:
            cluster_id: ID кластера

        Returns:
            Список фоновых заданий
        """
        # Используем JobReader с получением из connection list
        from ...monitoring.jobs.reader import JobReader

        reader = JobReader(self.settings)
        return reader.get_jobs(cluster_id)

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

        if sessions is None:
            sessions = []

        # Подсчет метрик
        total_sessions = len(sessions)

        # Используем строгую проверку активности сессий
        # Критерии активности (все обязательные):
        # 1. hibernate == 'no' (не в спящем режиме)
        # 2. last-active-at свежее 5 минут
        # 3. calls-last-5min >= 1 (хотя бы 1 вызов за 5 мин)
        # 4. bytes-last-5min >= 1024 (хотя бы 1KB трафика за 5 мин)
        from ...monitoring.session.filters import is_session_active

        active_sessions = sum(
            1
            for s in sessions
            if is_session_active(
                s,
                threshold_minutes=5,
                check_activity=True,
                min_calls=1,
                check_traffic=True,
                min_bytes=1024,
            )
        )

        total_jobs = len(jobs)
        active_jobs = sum(1 for j in jobs if j.get("status") == "running")

        # Получаем лимиты сессий на уровне Информационных Баз (max-connections)
        from ...monitoring.infobase.analyzer import get_total_infobase_session_limit

        session_limit = get_total_infobase_session_limit(cluster_id)

        # Рассчитываем процент заполнения (только если лимит установлен)
        session_percent = 0.0
        if session_limit > 0:
            session_percent = round((total_sessions / session_limit) * 100, 2)

        # TODO: Добавить мониторинг рабочих серверов
        working_servers_count = 1
        total_servers_count = 1

        return {
            "cluster": {
                "id": cluster["id"],
                "name": cluster["name"],
                "status": cluster["status"],  # Статус для отправки в Zabbix
            },
            "metrics": {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,  # strict: hibernate + last-active + calls + traffic
                "total_jobs": total_jobs,
                "active_jobs": active_jobs,
                "session_limit": session_limit,
                "session_percent": session_percent,
                "working_servers": working_servers_count,
                "total_servers": total_servers_count,
            },
        }
