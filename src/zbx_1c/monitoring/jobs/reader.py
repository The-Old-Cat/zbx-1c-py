"""
Чтение информации о фоновых заданиях

Получение заданий из session list (rac session list):
- BackgroundJob — фоновые задания пользователей
- SystemBackgroundJob — системные фоновые задания
- JobScheduler — планировщик регламентных заданий

Использование session list позволяет получить поле hibernate для определения активности.
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
        Получение списка фоновых заданий через session list

        Args:
            cluster_id: ID кластера
            infobase: Опциональное имя информационной базы

        Returns:
            Список фоновых заданий
        """
        logger.debug(f"Getting jobs for cluster {cluster_id}")

        # Формируем команду: rac.exe session list --cluster=cluster_id host:port
        cmd = [
            str(self.settings.rac_path),
            "session",
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
            logger.debug(f"Session list returned empty or error: {result}")
            return []

        sessions = parse_rac_output(result["stdout"])
        jobs = []

        for session in sessions:
            app_id = session.get("app-id", "")

            # Фильтруем только фоновые задания
            if app_id in ["BackgroundJob", "SystemBackgroundJob", "JobScheduler"]:
                # Фильтрация по информационной базе
                if infobase and session.get("infobase") != infobase:
                    continue

                # Определение активности по hibernate
                hibernate = session.get("hibernate", "no")
                status = "running" if hibernate == "no" else "idle"

                jobs.append({
                    "job-id": session.get("session", ""),
                    "session-id": session.get("session-id", ""),
                    "infobase": session.get("infobase", ""),
                    "user-name": session.get("user-name", ""),
                    "started-at": session.get("started-at", ""),
                    "last-active-at": session.get("last-active-at", ""),
                    "status": status,
                    "app-id": app_id,
                    "hibernate": hibernate,
                    "host": session.get("host", ""),
                    "process": session.get("process", ""),
                })

        logger.debug(f"Found {len(jobs)} jobs from sessions")
        return jobs
