"""CLI команды для мониторинга техжурнала 1С"""

import click
from loguru import logger

from ..core.config import Settings
from ..core.logging import setup_logging
from ..monitoring.techjournal import MetricsCollector, ZabbixSender


def load_settings(config_path: str) -> Settings:
    """Загрузка настроек из указанного файла"""
    from pydantic_settings import SettingsConfigDict

    class TempSettings(Settings):
        model_config = SettingsConfigDict(
            env_file=config_path,
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="ignore",
        )

    return TempSettings()


@click.group()
def techjournal_cli():
    """Мониторинг техжурнала 1С"""
    setup_logging()
    pass


@techjournal_cli.command("collect")
@click.option("--config", "-c", help="Path to config file", default=".env")
@click.option(
    "--period",
    "-p",
    "period_minutes",
    help="Period in minutes",
    default=5,
    type=int,
)
@click.option("--json-output", is_flag=True, help="Output in JSON format")
def collect_metrics(config: str, period_minutes: int, json_output: bool):
    """
    Сбор метрик из техжурнала 1С

    Считывает логи из директорий core, perf, locks, sql, zabbix
    и собирает статистику по событиям за указанный период.
    """
    try:
        settings = load_settings(config)

        # Получаем путь к логам техжурнала
        log_base = getattr(settings, "techjournal_log_base", None)

        if not log_base:
            # Пытаемся определить из LOG_PATH
            log_base = getattr(settings, "log_path", "./logs")
            if isinstance(log_base, str):
                from pathlib import Path

                log_base = str(Path(log_base).parent / "1c_techjournal")

        collector = MetricsCollector(log_base)

        if json_output:
            metrics = collector.collect(period_minutes=period_minutes)
            import json

            click.echo(json.dumps(metrics.to_dict(), indent=2, ensure_ascii=False))
        else:
            summary = collector.get_summary(period_minutes=period_minutes)
            click.echo(summary)

    except Exception as e:
        logger.error(f"Failed to collect metrics: {e}")
        click.echo(f"Error: {e}", err=True)
        click.exit(1)


@techjournal_cli.command("send")
@click.option("--config", "-c", help="Path to config file", default=".env")
@click.option(
    "--period",
    "-p",
    "period_minutes",
    help="Period in minutes",
    default=5,
    type=int,
)
@click.option("--host", "-h", "zabbix_host", help="Zabbix host name")
@click.option("--dry-run", is_flag=True, help="Show metrics without sending")
def send_to_zabbix(config: str, period_minutes: int, zabbix_host: str, dry_run: bool):
    """
    Отправка метрик в Zabbix

    Собирает метрики из техжурнала и отправляет их в Zabbix
    через zabbix_sender или Zabbix API.
    """
    try:
        settings = load_settings(config)

        # Получаем путь к логам
        log_base = getattr(settings, "techjournal_log_base", None)
        if not log_base:
            from pathlib import Path

            log_base = getattr(settings, "log_path", "./logs")
            if isinstance(log_base, str):
                log_base = str(Path(log_base).parent / "1c_techjournal")

        # Собираем метрики
        collector = MetricsCollector(log_base)
        metrics = collector.collect_for_zabbix(period_minutes=period_minutes, host=zabbix_host)

        if dry_run:
            click.echo("=== DRY RUN: Метрики не отправляются ===")
            click.echo(f"Хост: {zabbix_host or socket.gethostname()}")
            click.echo(f"Период: {period_minutes} мин")
            click.echo(f"Всего метрик: {len(metrics)}")
            click.echo()
            for key, value in metrics:
                click.echo(f"  {key}: {value}")
            return

        # Отправляем в Zabbix
        zabbix_server = getattr(settings, "zabbix_server", "127.0.0.1")
        zabbix_port = getattr(settings, "zabbix_port", 10051)
        zabbix_sender_path = getattr(settings, "zabbix_sender_path", None)
        use_api = getattr(settings, "zabbix_use_api", False)
        api_url = getattr(settings, "zabbix_api_url", None)
        api_token = getattr(settings, "zabbix_api_token", None)

        sender = ZabbixSender(
            zabbix_server=zabbix_server,
            zabbix_port=zabbix_port,
            zabbix_host=zabbix_host,
            zabbix_sender_path=zabbix_sender_path,
            use_api=use_api,
            api_url=api_url,
            api_token=api_token,
        )

        result = sender.send(metrics, host=zabbix_host)

        if result.success:
            click.echo(f"✓ Успешно отправлено {result.sent_count} метрик")
            if result.message:
                click.echo(f"  {result.message}")
        else:
            click.echo(f"✗ Ошибка отправки: {result.message}", err=True)
            click.exit(1)

    except Exception as e:
        logger.error(f"Failed to send to Zabbix: {e}")
        click.echo(f"Error: {e}", err=True)
        click.exit(1)


@techjournal_cli.command("summary")
@click.option("--config", "-c", help="Path to config file", default=".env")
@click.option(
    "--period",
    "-p",
    "period_minutes",
    help="Period in minutes",
    default=5,
    type=int,
)
def show_summary(config: str, period_minutes: int):
    """
    Показать сводку по техжурналу

    Выводит текстовую сводку по событиям за указанный период.
    """
    try:
        settings = load_settings(config)

        log_base = getattr(settings, "techjournal_log_base", None)
        if not log_base:
            from pathlib import Path

            log_base = getattr(settings, "log_path", "./logs")
            if isinstance(log_base, str):
                log_base = str(Path(log_base).parent / "1c_techjournal")

        collector = MetricsCollector(log_base)
        summary = collector.get_summary(period_minutes=period_minutes)
        click.echo(summary)

    except Exception as e:
        logger.error(f"Failed to get summary: {e}")
        click.echo(f"Error: {e}", err=True)
        click.exit(1)


@techjournal_cli.command("check")
@click.option("--config", "-c", help="Path to config file", default=".env")
def check_logs(config: str):
    """
    Проверка доступности логов техжурнала

    Проверяет существование директорий с логами и их содержимое.
    """
    try:
        settings = load_settings(config)

        log_base = getattr(settings, "techjournal_log_base", None)
        if not log_base:
            from pathlib import Path

            log_base = getattr(settings, "log_path", "./logs")
            if isinstance(log_base, str):
                log_base = str(Path(log_base).parent / "1c_techjournal")

        from pathlib import Path

        log_path = Path(log_base)
        subdirs = ["core", "perf", "locks", "sql", "zabbix"]

        click.echo("=" * 60)
        click.echo("ПРОВЕРКА ТЕХЖУРНАЛА 1С")
        click.echo("=" * 60)
        click.echo(f"Базовый путь: {log_path}")
        click.echo()

        if not log_path.exists():
            click.echo(f"✗ Директория не существует: {log_path}")
            click.echo()
            click.echo("Убедитесь, что техжурнал 1С настроен и пишет логи в эту директорию.")
            click.exit(1)

        click.echo(f"✓ Директория существует: {log_path}")
        click.echo()

        for subdir in subdirs:
            dir_path = log_path / subdir
            if dir_path.exists():
                log_files = list(dir_path.glob("*.log"))
                click.echo(f"✓ {subdir:12s} - {len(log_files)} файлов логов")
                if log_files:
                    latest = max(log_files, key=lambda f: f.stat().st_mtime)
                    size_mb = latest.stat().st_size / 1024 / 1024
                    click.echo(f"    └─ Последний: {latest.name} ({size_mb:.2f} MB)")
            else:
                click.echo(f"✗ {subdir:12s} - не найдено")

        click.echo("=" * 60)

    except Exception as e:
        logger.error(f"Failed to check logs: {e}")
        click.echo(f"Error: {e}", err=True)
        click.exit(1)


# Импорт для socket
import socket
