"""CLI для zbx-1c-techlog"""

import socket
import sys
from typing import Optional

import click

from ..core.config import TechlogConfig, get_config
from ..reader.collector import MetricsCollector
from ..zabbix_sender import ZabbixSender


@click.group()
def cli():
    """Zabbix-1C TechJournal Monitoring Tool"""
    pass


@cli.command("collect")
@click.option("--config", "-c", help="Path to config file", default=None)
@click.option(
    "--period",
    "-p",
    "period_minutes",
    help="Period in minutes",
    default=5,
    type=int,
)
@click.option("--json-output", is_flag=True, help="Output in JSON format")
def collect(config: Optional[str], period_minutes: int, json_output: bool):
    """
    Сбор метрик из техжурнала 1С

    Считывает логи из директорий core, perf, locks, sql, zabbix
    и собирает статистику по событиям за указанный период.
    """
    cfg = get_config()

    log_base = cfg.logs_base_path
    collector = MetricsCollector(log_base)

    if json_output:
        metrics = collector.collect(period_minutes=period_minutes)
        import json

        click.echo(json.dumps(metrics.to_dict(), indent=2, ensure_ascii=False))
    else:
        summary = collector.get_summary(period_minutes=period_minutes)
        click.echo(summary)


@cli.command("send")
@click.option("--config", "-c", help="Path to config file", default=None)
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
def send(config: Optional[str], period_minutes: int, zabbix_host: Optional[str], dry_run: bool):
    """
    Отправка метрик в Zabbix

    Собирает метрики из техжурнала и отправляет их в Zabbix
    через zabbix_sender или Zabbix API.
    """
    cfg = get_config()

    # Собираем метрики
    collector = MetricsCollector(cfg.logs_base_path)
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
    sender = ZabbixSender(
        zabbix_server=cfg.zabbix_server,
        zabbix_port=cfg.zabbix_port,
        zabbix_host=zabbix_host,
        zabbix_sender_path=cfg.zabbix_sender_path,
        use_api=cfg.zabbix_use_api,
        api_url=cfg.zabbix_api_url,
        api_token=cfg.zabbix_api_token,
    )

    result = sender.send(metrics, host=zabbix_host)

    if result.success:
        click.echo(f"✓ Успешно отправлено {result.sent_count} метрик")
        if result.message:
            click.echo(f"  {result.message}")
    else:
        click.echo(f"✗ Ошибка отправки: {result.message}", err=True)
        sys.exit(1)


@cli.command("summary")
@click.option("--config", "-c", help="Path to config file", default=None)
@click.option(
    "--period",
    "-p",
    "period_minutes",
    help="Period in minutes",
    default=5,
    type=int,
)
def summary(config: Optional[str], period_minutes: int):
    """
    Показать сводку по техжурналу

    Выводит текстовую сводку по событиям за указанный период.
    """
    cfg = get_config()
    collector = MetricsCollector(cfg.logs_base_path)
    summary_text = collector.get_summary(period_minutes=period_minutes)
    click.echo(summary_text)


@cli.command("check")
@click.option("--config", "-c", help="Path to config file", default=None)
def check_logs(config: Optional[str]):
    """
    Проверка доступности логов техжурнала

    Проверяет существование директорий с логами и их содержимое.
    """
    cfg = get_config()

    log_path = cfg.logs_base_path
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
        sys.exit(1)

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


if __name__ == "__main__":
    cli()
