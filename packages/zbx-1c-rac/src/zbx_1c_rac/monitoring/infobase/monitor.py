"""Мониторинг информационных баз 1С"""

from typing import Any, Dict, List, Optional

from ...core.config import RacConfig
from ...utils.rac_client import execute_rac_command


class InfobaseMonitor:
    """
    Мониторинг информационных баз кластера 1С.

    Args:
        config: Конфигурация RAC.
    """

    def __init__(self, config: Optional[RacConfig] = None):
        self.config = config or RacConfig()

    def get_infobases(self, cluster_id: str) -> List[Dict[str, Any]]:
        """
        Получить список информационных баз.

        Args:
            cluster_id: UUID кластера.

        Returns:
            Список ИБ.
        """
        # Синтаксис 1С 8.3.27+: rac infobase summary list --cluster-user=... --cluster-pwd=... --cluster=UUID host:port
        cmd_parts = [
            "infobase",
            "summary",
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

        return parse_rac_output(result["stdout"])

    def get_infobase_details(
        self,
        cluster_id: str,
        infobase_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Получить детальную информацию об ИБ.

        Args:
            cluster_id: UUID кластера.
            infobase_id: UUID информационной базы.

        Returns:
            Информация об ИБ или None.
        """
        infobases = self.get_infobases(cluster_id)

        for ib in infobases:
            if ib.get("infobase") == infobase_id or ib.get("name") == infobase_id:
                return ib

        return None

    def get_statistics(self, cluster_id: str) -> Dict[str, Any]:
        """
        Получить статистику по информационным базам.

        Args:
            cluster_id: UUID кластера.

        Returns:
            Статистика.
        """
        infobases = self.get_infobases(cluster_id)

        # Подсчёт по типам СУБД
        by_dbms: Dict[str, int] = {}
        for ib in infobases:
            dbms = ib.get("dbms", "unknown")
            by_dbms[dbms] = by_dbms.get(dbms, 0) + 1

        # Считаем суммарный лимит сессий
        total_session_limit = 0
        for ib in infobases:
            try:
                limit = int(ib.get("max-connections", 0))
                total_session_limit += limit
            except (ValueError, TypeError):
                pass

        return {
            "total": len(infobases),
            "by_dbms": by_dbms,
            "total_session_limit": total_session_limit,
        }
