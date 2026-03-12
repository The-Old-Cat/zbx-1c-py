"""Сбор данных о сессиях 1С"""

from typing import Any, Dict, List, Optional

from ...core.config import RacConfig
from ...utils.rac_client import execute_rac_command


class SessionCollector:
    """
    Сборщик данных о сессиях кластера 1С.

    Args:
        config: Конфигурация RAC.
    """

    def __init__(self, config: Optional[RacConfig] = None):
        self.config = config or RacConfig()

    def get_sessions(self, cluster_id: str) -> List[Dict[str, Any]]:
        """
        Получить список сессий кластера.

        Args:
            cluster_id: UUID кластера.

        Returns:
            Список сессий.
        """
        # Синтаксис 1С 8.3.27+: rac session list --cluster-user=... --cluster-pwd=... --cluster=UUID host:port
        cmd_parts = [
            "session",
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

    def get_active_sessions(
        self,
        cluster_id: str,
        threshold_minutes: int = 5,
        check_activity: bool = True,
        min_calls: int = 1,
        check_traffic: bool = True,
        min_bytes: int = 1024,
    ) -> List[Dict[str, Any]]:
        """
        Получить активные сессии.

        Args:
            cluster_id: UUID кластера.
            threshold_minutes: Порог активности (минуты).
            check_activity: Проверять calls-last-5min.
            min_calls: Мин. количество вызовов.
            check_traffic: Проверять bytes-last-5min.
            min_bytes: Мин. объём трафика.

        Returns:
            Список активных сессий.
        """
        sessions = self.get_sessions(cluster_id)
        active = []

        for session in sessions:
            if self._is_active(
                session,
                threshold_minutes,
                check_activity,
                min_calls,
                check_traffic,
                min_bytes,
            ):
                active.append(session)

        return active

    @staticmethod
    def _is_active(
        session: Dict[str, Any],
        threshold_minutes: int,
        check_activity: bool,
        min_calls: int,
        check_traffic: bool,
        min_bytes: int,
    ) -> bool:
        """
        Проверка сессии на активность.

        Критерии активности:
        1. last-active-at <= threshold_minutes (для Designer)
        2. last-active-at <= 5 мин (для остальных)
        3. hibernate=no + calls >= min_calls + bytes >= min_bytes
        """
        from datetime import datetime, timedelta

        # Получаем время последней активности
        last_active_str = session.get("last-active-at", "")
        hibernate = session.get("hibernate", "no").lower()

        # Парсим время
        try:
            if last_active_str:
                # Формат: 2024-01-15T14:30:00
                last_active = datetime.fromisoformat(last_active_str.replace("Z", "+00:00"))
                now = datetime.now(last_active.tzinfo) if last_active.tzinfo else datetime.now()
                diff = (now - last_active).total_seconds() / 60
            else:
                diff = float("inf")
        except (ValueError, TypeError):
            diff = float("inf")

        # Аппаратный клиент (1CV8C) - более строгий порог
        app = session.get("app", "")
        is_designer = "Designer" in app or "Design" in app
        actual_threshold = threshold_minutes if is_designer else 5

        # Критерий 1: время последней активности
        if diff <= actual_threshold:
            return True

        # Критерий 2: hibernate=no + активность + трафик
        if hibernate == "no":
            activity_ok = True
            traffic_ok = True

            if check_activity:
                calls = int(session.get("calls-last-5min", 0))
                activity_ok = calls >= min_calls

            if check_traffic:
                bytes_val = int(session.get("bytes-last-5min", 0))
                traffic_ok = bytes_val >= min_bytes

            if activity_ok and traffic_ok:
                return True

        return False

    def get_statistics(self, cluster_id: str) -> Dict[str, Any]:
        """
        Получить статистику по сессиям.

        Args:
            cluster_id: UUID кластера.

        Returns:
            Статистика.
        """
        sessions = self.get_sessions(cluster_id)
        active = self.get_active_sessions(cluster_id)

        # Группировка по пользователям
        users: Dict[str, int] = {}
        for session in sessions:
            user = session.get("user", "unknown")
            users[user] = users.get(user, 0) + 1

        # Группировка по ИБ
        infobases: Dict[str, int] = {}
        for session in sessions:
            ib = session.get("infobase", "unknown")
            infobases[ib] = infobases.get(ib, 0) + 1

        return {
            "total": len(sessions),
            "active": len(active),
            "users": users,
            "infobases": infobases,
        }
