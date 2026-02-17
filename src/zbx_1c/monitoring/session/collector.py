"""
Сбор информации о сессиях 1С
"""

import sys
import json
import click
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger

from ...core.config import Settings
from ...utils.rac_client import RACClient
from ...utils.converters import parse_sessions
from ...utils.net import check_port


class SessionCollector:
    """Сборщик информации о сессиях"""

    def __init__(self, settings: Settings):
        """
        Инициализация сборщика

        Args:
            settings: Настройки приложения
        """
        self.settings = settings
        self.rac = RACClient(settings)

    def get_sessions(self, cluster_id: str, infobase: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получение списка сессий

        Args:
            cluster_id: ID кластера
            infobase: Опциональное имя информационной базы

        Returns:
            Список сессий
        """
        logger.debug(f"Getting sessions for cluster {cluster_id}")

        # Формируем команду: rac.exe session list --cluster=cluster_id host:port
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

        if not result or result["returncode"] != 0 or not result["stdout"]:
            logger.error("Failed to get sessions")
            return []

        sessions_data = parse_sessions(result["stdout"])
        sessions = []

        for data in sessions_data:
            try:
                # Фильтрация по информационной базе
                if infobase and data.get("infobase") != infobase:
                    continue

                sessions.append(data)

            except Exception as e:
                logger.warning(f"Failed to parse session: {e}")

        logger.debug(f"Found {len(sessions)} sessions")
        return sessions

    def get_active_sessions(
        self, cluster_id: str, threshold_minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Получение только активных сессий

        Args:
            cluster_id: ID кластера
            threshold_minutes: Порог активности в минутах

        Returns:
            Список активных сессий
        """
        all_sessions = self.get_sessions(cluster_id)
        active_sessions = []

        for session in all_sessions:
            if is_session_active(session, threshold_minutes):
                active_sessions.append(session)

        return active_sessions

    def get_sessions_summary(self, cluster_id: str) -> Dict[str, Any]:
        """
        Получение сводной информации о сессиях

        Args:
            cluster_id: ID кластера

        Returns:
            Сводная информация
        """
        sessions = self.get_sessions(cluster_id)

        total = len(sessions)
        active = sum(1 for s in sessions if s.get("hibernate") == "no")
        hibernated = sum(1 for s in sessions if s.get("hibernate") == "yes")

        # Группировка по пользователям
        users = {}
        for s in sessions:
            user = s.get("user-name", "unknown")
            if user not in users:
                users[user] = 0
            users[user] += 1

        # Группировка по приложениям
        apps = {}
        for s in sessions:
            app = s.get("app-id", "unknown")
            if app not in apps:
                apps[app] = 0
            apps[app] += 1

        return {
            "cluster_id": cluster_id,
            "timestamp": datetime.now().isoformat(),
            "total_sessions": total,
            "active_sessions": active,
            "hibernated_sessions": hibernated,
            "unique_users": len(users),
            "users": users,
            "applications": apps,
        }


def is_session_active(session: Dict[str, Any], threshold_minutes: int = 5) -> bool:
    """
    Проверка активности сессии

    Args:
        session: Данные сессии
        threshold_minutes: Порог активности в минутах

    Returns:
        True если сессия активна
    """
    try:
        last_active = session.get("last-active-at")
        if not last_active:
            return False

        from datetime import datetime, timedelta

        # Парсим время последней активности
        last_active_dt = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
        now = datetime.now(last_active_dt.tzinfo) if last_active_dt.tzinfo else datetime.now()

        # Проверяем, что последняя активность была позже чем (сейчас - порог)
        return last_active_dt >= now - timedelta(minutes=threshold_minutes)

    except Exception:
        return False


def check_ras_availability(host: str, port: int, timeout: float = 5.0) -> bool:
    """
    Проверка доступности RAS сервиса

    Args:
        host: Хост RAS
        port: Порт RAS
        timeout: Таймаут в секундах

    Returns:
        True если доступен, иначе False
    """
    logger.debug(f"Checking RAS availability at {host}:{port}")

    if not check_port(host, port, timeout):
        logger.warning(f"RAS port {port} on {host} is not accessible")
        return False

    logger.info(f"RAS is available at {host}:{port}")
    return True


# CLI команды для сессий
@click.group()
def session_cli():
    """CLI для управления сессиями 1С"""
    pass


@session_cli.command("list")
@click.argument("cluster_id")
@click.option("--config", "-c", help="Path to config file", default=".env")
@click.option("--json-output", is_flag=True, help="Output in JSON format")
def list_sessions(cluster_id: str, config: str, json_output: bool):
    """
    Список всех сессий кластера
    """
    try:
        from pydantic_settings import SettingsConfigDict

        class TempSettings(Settings):
            model_config = SettingsConfigDict(
                env_file=config, env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
            )

        settings = TempSettings()
        collector = SessionCollector(settings)
        sessions = collector.get_sessions(cluster_id)

        if json_output:
            click.echo(json.dumps(sessions, indent=2, ensure_ascii=False, default=str))
        else:
            click.echo(f"\n📊 Сессии кластера {cluster_id}:\n")
            for i, session in enumerate(sessions, 1):
                click.echo(f"{i}. Session ID: {session.get('session-id', 'N/A')}")
                click.echo(f"   User: {session.get('user-name', 'N/A')}")
                click.echo(f"   App: {session.get('app-id', 'N/A')}")
                click.echo(f"   Infobase: {session.get('infobase', 'N/A')}")
                click.echo(f"   Host: {session.get('host', 'N/A')}")
                click.echo(f"   Started: {session.get('started-at', 'N/A')}")
                click.echo(f"   Last active: {session.get('last-active-at', 'N/A')}")
                click.echo(f"   Hibernate: {session.get('hibernate', 'N/A')}")
                click.echo()

    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        sys.exit(1)


@session_cli.command("active")
@click.argument("cluster_id")
@click.option("--config", "-c", help="Path to config file", default=".env")
@click.option("--threshold", "-t", default=5, help="Threshold in minutes")
def active_sessions(cluster_id: str, config: str, threshold: int):
    """
    Список активных сессий кластера
    """
    try:
        from pydantic_settings import SettingsConfigDict

        class TempSettings(Settings):
            model_config = SettingsConfigDict(
                env_file=config, env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
            )

        settings = TempSettings()
        collector = SessionCollector(settings)
        sessions = collector.get_active_sessions(cluster_id, threshold)

        click.echo(json.dumps(sessions, indent=2, ensure_ascii=False, default=str))

    except Exception as e:
        logger.error(f"Failed to get active sessions: {e}")
        sys.exit(1)


@session_cli.command("summary")
@click.argument("cluster_id")
@click.option("--config", "-c", help="Path to config file", default=".env")
def sessions_summary(cluster_id: str, config: str):
    """
    Сводная информация о сессиях кластера
    """
    try:
        from pydantic_settings import SettingsConfigDict

        class TempSettings(Settings):
            model_config = SettingsConfigDict(
                env_file=config, env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
            )

        settings = TempSettings()
        collector = SessionCollector(settings)
        summary = collector.get_sessions_summary(cluster_id)

        click.echo(json.dumps(summary, indent=2, ensure_ascii=False, default=str))

    except Exception as e:
        logger.error(f"Failed to get sessions summary: {e}")
        sys.exit(1)


@session_cli.command("count")
@click.argument("cluster_id")
@click.option("--config", "-c", help="Path to config file", default=".env")
def sessions_count(cluster_id: str, config: str):
    """
    Количество сессий кластера (для Zabbix)
    """
    try:
        from pydantic_settings import SettingsConfigDict

        class TempSettings(Settings):
            model_config = SettingsConfigDict(
                env_file=config, env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
            )

        settings = TempSettings()
        collector = SessionCollector(settings)
        sessions = collector.get_sessions(cluster_id)

        total = len(sessions)
        active = sum(1 for s in sessions if s.get("hibernate") == "no")

        result = {
            "cluster_id": cluster_id,
            "total_sessions": total,
            "active_sessions": active,
        }

        click.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    except Exception as e:
        logger.error(f"Failed to count sessions: {e}")
        sys.exit(1)


if __name__ == "__main__":
    session_cli()
