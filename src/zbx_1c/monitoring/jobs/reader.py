"""
Чтение информации о фоновых заданиях
"""

from typing import List, Dict, Optional
from loguru import logger

from ...core.config import Settings
from ...utils.rac_client import RACClient
from ...utils.converters import parse_jobs


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
        Получение списка фоновых заданий

        Args:
            cluster_id: ID кластера
            infobase: Опциональное имя информационной базы

        Returns:
            Список фоновых заданий
        """
        logger.debug(f"Getting jobs for cluster {cluster_id}")

        # Формируем команду: rac.exe job list --cluster=cluster_id host:port
        # Примечание: команда 'job list' доступна только в новых версиях 1С (8.3.24+)
        cmd = [
            str(self.settings.rac_path),
            "job",
            "list",
            f"--cluster={cluster_id}",
            f"{self.settings.rac_host}:{self.settings.rac_port}",
        ]
        result = self.rac.execute(cmd)

        if not result or result["returncode"] != 0 or not result["stdout"]:
            # 'job list' не поддерживается в этой версии 1С
            logger.debug("'job list' command not supported by this 1C version")
            return []

        jobs_data = parse_jobs(result["stdout"])
        jobs = []

        for data in jobs_data:
            try:
                # Фильтрация по информационной базе
                if infobase and data.get("infobase") != infobase:
                    continue

                jobs.append(data)

            except Exception as e:
                logger.warning(f"Failed to parse job: {e}")

        logger.debug(f"Found {len(jobs)} jobs")
        return jobs
