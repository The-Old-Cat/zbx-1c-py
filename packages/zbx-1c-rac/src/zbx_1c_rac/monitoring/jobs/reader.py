"""Чтение фоновых заданий 1С"""

from typing import Any, Dict, List, Optional

from ...core.config import RacConfig
from ...utils.rac_client import execute_rac_command


class JobReader:
    """
    Чтение фоновых заданий кластера 1С.

    Args:
        config: Конфигурация RAC.
    """

    def __init__(self, config: Optional[RacConfig] = None):
        self.config = config or RacConfig()

    def get_jobs(self, cluster_id: str) -> List[Dict[str, Any]]:
        """
        Получить список фоновых заданий.

        Args:
            cluster_id: UUID кластера.

        Returns:
            Список заданий.
        """
        # Пробуем команду 'job list' (1С 8.3.24+)
        # Синтаксис: rac job list host:port/cluster (без аутентификации)
        cmd_parts = [
            "job",
            "list",
            f"{self.config.rac_host}:{self.config.rac_port}/{cluster_id}",
        ]

        result = execute_rac_command(
            self.config.rac_path,
            cmd_parts,
            self.config.rac_timeout,
        )

        # Если job list не сработала, используем connection list
        if not result or result["returncode"] != 0 or not result["stdout"]:
            # Синтаксис 1С 8.3.27+: rac connection list --cluster-user=... --cluster-pwd=... --cluster=UUID host:port
            cmd_parts = [
                "connection",
                "list",
            ]

            # Параметры аутентификации должны идти ПЕРЕД --cluster
            if self.config.user_name:
                cmd_parts.append(f"--cluster-user={self.config.user_name}")
            if self.config.user_pass:
                cmd_parts.append(f"--cluster-pwd={self.config.user_pass}")

            cmd_parts.append(f"--cluster={cluster_id}")
            cmd_parts.append(f"{self.config.rac_host}:{self.config.rac_port}")

            result = execute_rac_command(
                self.config.rac_path,
                cmd_parts,
                self.config.rac_timeout,
            )

            if not result or result["returncode"] != 0 or not result["stdout"]:
                return []

            from ...utils.converters import parse_rac_output

            connections = parse_rac_output(result["stdout"])

            # Фильтруем только фоновые задания
            jobs = []
            for conn in connections:
                app = conn.get("application", "")
                if "JobScheduler" in app or "SystemBackgroundJob" in app or "BackgroundJob" in app:
                    # Преобразуем формат connection в формат job
                    job = {
                        "job-id": conn.get("conn-id", ""),
                        "infobase": conn.get("infobase", ""),
                        "started-at": conn.get("connected-at", ""),
                        "status": "running",
                        "description": f"Background job: {app}",
                        "host": conn.get("host", ""),
                        "application": app,
                    }
                    jobs.append(job)

            return jobs

        from ...utils.converters import parse_rac_output
        return parse_rac_output(result["stdout"])

    def get_active_jobs(self, cluster_id: str) -> List[Dict[str, Any]]:
        """
        Получить активные фоновые задания.

        Args:
            cluster_id: UUID кластера.

        Returns:
            Список активных заданий.
        """
        jobs = self.get_jobs(cluster_id)
        active = []

        for job in jobs:
            hibernate = job.get("hibernate", "no").lower()
            status = job.get("status", "")
            app = job.get("application", job.get("app", ""))

            # JobScheduler всегда активен, остальные по hibernate
            if "JobScheduler" in app:
                active.append(job)
            elif "SystemBackgroundJob" in app and status == "running":
                active.append(job)
            elif hibernate == "no" or status == "running":
                active.append(job)

        return active

    def get_statistics(self, cluster_id: str) -> Dict[str, Any]:
        """
        Получить статистику по заданиям.

        Args:
            cluster_id: UUID кластера.

        Returns:
            Статистика.
        """
        jobs = self.get_jobs(cluster_id)
        active = self.get_active_jobs(cluster_id)

        # Группировка по статусам
        by_status: Dict[str, int] = {}
        for job in jobs:
            status = job.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1

        # Группировка по ИБ
        by_infobase: Dict[str, int] = {}
        for job in jobs:
            ib = job.get("infobase", "unknown")
            by_infobase[ib] = by_infobase.get(ib, 0) + 1

        return {
            "total": len(jobs),
            "active": len(active),
            "by_status": by_status,
            "by_infobase": by_infobase,
        }
