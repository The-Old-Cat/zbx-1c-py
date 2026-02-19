"""
Чтение информации о фоновых заданиях

Получение заданий из connection list (rac connection list):
- BackgroundJob — фоновые задания пользователей
- SystemBackgroundJob — системные фоновые задания
- JobScheduler — планировщик регламентных заданий
"""

from typing import List, Dict, Optional
from loguru import logger

from ...core.config import Settings
from ...utils.rac_client import RACClient
from ...utils.converters import parse_rac_output


class JobReader:
    """Читатель информации о фоновых заданиях"""

    def __init__(self, settings: Settings):
        """
        Инициализация читателя

        Args:
            settings: Настройки приложения
        """
        self.settings = settings
        self.rac = RACClient(settings)

    def get_jobs(self, cluster_id: str, infobase: Optional[str] = None) -> List[Dict]:
        """
        Получение списка фоновых заданий через connection list

        Args:
            cluster_id: ID кластера
            infobase: Опциональное имя информационной базы

        Returns:
            Список фоновых заданий
        """
        logger.debug(f"Getting jobs for cluster {cluster_id}")

        # Формируем команду: rac.exe connection list --cluster=cluster_id host:port
        cmd = [
            str(self.settings.rac_path),
            "connection",
            "list",
            f"--cluster={cluster_id}",
            f"{self.settings.rac_host}:{self.settings.rac_port}",
        ]

        # Добавляем аутентификацию если есть
        if self.settings.user_name:
            cmd.append(f"--cluster-user={self.settings.user_name}")
        if self.settings.user_pass:
            cmd.append(f"--cluster-pwd={self.settings.user_pass}")

        result = self.rac.execute(cmd)

        if not result or result["returncode"] != 0 or not result["stdout"]:
            logger.debug(f"Connection list returned empty or error: {result}")
            return []

        connections = parse_rac_output(result["stdout"])
        jobs = []

        for conn in connections:
            app = conn.get("application", "")

            # Фильтруем только фоновые задания
            if app in ["BackgroundJob", "SystemBackgroundJob", "JobScheduler"]:
                # Фильтрация по информационной базе
                if infobase and conn.get("infobase") != infobase:
                    continue

                jobs.append({
                    "job-id": conn.get("connection", ""),
                    "infobase": conn.get("infobase", ""),
                    "user-name": app,  # Используем application как имя
                    "started-at": conn.get("connected-at", ""),
                    "status": "running",
                    "app-id": app,
                    "host": conn.get("host", ""),
                    "process": conn.get("process", ""),
                })

        logger.debug(f"Found {len(jobs)} jobs from connections")
        return jobs
