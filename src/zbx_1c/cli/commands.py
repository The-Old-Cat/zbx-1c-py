#!/usr/bin/env python3
"""
CLI команды для интеграции с Zabbix
Работает точно так же как run_direct.py
"""

import os
import sys
import json
import socket
from typing import Optional, List, Dict
from datetime import datetime
import click
from loguru import logger

from ..core.config import Settings
from ..core.logging import setup_logging
from ..utils.converters import parse_rac_output, format_lld_data, decode_output


def safe_output(data, **kwargs):
    """
    Безопасный вывод JSON в консоль с правильной кодировкой для Zabbix Agent.

    Args:
        data: Данные для вывода
        **kwargs: Аргументы для json.dumps
    """
    json_str = json.dumps(data, ensure_ascii=False, **kwargs)
    # Для Windows явно пишем UTF-8 байты в stdout
    if sys.platform == "win32":
        # Пишем напрямую в buffer чтобы избежать перекодировки
        sys.stdout.buffer.write((json_str + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()
    else:
        click.echo(json_str)


def load_settings(config_path: str) -> Settings:
    """Загрузка настроек из указанного файла"""
    from pydantic_settings import SettingsConfigDict

    class TempSettings(Settings):
        model_config = SettingsConfigDict(
            env_file=config_path, env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
        )

    return TempSettings()


def safe_print(text: str):
    """Безопасный вывод в консоль"""
    try:
        click.echo(text)
    except UnicodeEncodeError:
        try:
            click.echo(text.encode("ascii", errors="replace").decode("ascii"))
        except Exception:
            click.echo(str(text).encode("ascii", errors="replace").decode("ascii"))


def execute_rac_command(cmd_parts: List[str], timeout: int = 30) -> Optional[Dict]:
    """Выполнение команды rac"""
    try:
        # Выполняем команду, получаем байты
        result = __import__("subprocess").run(cmd_parts, capture_output=True, timeout=timeout)

        # Декодируем с учетом кодировки
        stdout = decode_output(result.stdout)
        stderr = decode_output(result.stderr)

        return {
            "returncode": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
        }

    except Exception as e:
        logger.error(f"Ошибка выполнения: {e}")
        return None


def check_ras_availability(settings: Settings) -> bool:
    """Проверка доступности RAS"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(settings.rac_timeout)
        result = sock.connect_ex((settings.rac_host, settings.rac_port))
        sock.close()
        return result == 0
    except Exception:
        return False


def discover_clusters(settings: Settings) -> List[Dict]:
    """Обнаружение кластеров"""
    import socket

    def check_status(host: str, port: int) -> str:
        """Проверка статуса кластера"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(settings.rac_timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return "available" if result == 0 else "unavailable"
        except Exception:
            return "unknown"

    cmd_parts = [
        str(settings.rac_path),
        "cluster",
        "list",
        f"{settings.rac_host}:{settings.rac_port}",
    ]

    result = execute_rac_command(cmd_parts)
    if not result or result["returncode"] != 0 or not result["stdout"]:
        return []

    # Парсим вывод
    clusters_data = parse_rac_output(result["stdout"])
    clusters = []

    for data in clusters_data:
        try:
            cluster_host = data.get("host", settings.rac_host)
            cluster_port = int(data.get("port", settings.rac_port))
            cluster = {
                "id": data.get("cluster"),
                "name": data.get("name", "unknown"),
                "host": cluster_host,
                "port": cluster_port,
                "status": check_status(cluster_host, cluster_port),
            }

            if cluster["id"]:
                clusters.append(cluster)
        except Exception as e:
            logger.error(f"Ошибка парсинга кластера: {e}")

    return clusters


def get_infobases(settings: Settings, cluster_id: str) -> List[Dict]:
    """Получение информационных баз"""
    cmd_parts = [
        str(settings.rac_path),
        "infobase",
        "summary",
        "list",
        f"--cluster={cluster_id}",
    ]

    if settings.user_name:
        cmd_parts.append(f"--cluster-user={settings.user_name}")
    if settings.user_pass:
        cmd_parts.append(f"--cluster-pwd={settings.user_pass}")

    cmd_parts.append(f"{settings.rac_host}:{settings.rac_port}")

    result = execute_rac_command(cmd_parts)
    if result and result["returncode"] == 0 and result["stdout"]:
        return parse_rac_output(result["stdout"])

    return []


def get_sessions(settings: Settings, cluster_id: str) -> List[Dict]:
    """Получение сессий"""
    cmd_parts = [
        str(settings.rac_path),
        "session",
        "list",
        f"--cluster={cluster_id}",
    ]

    if settings.user_name:
        cmd_parts.append(f"--cluster-user={settings.user_name}")
    if settings.user_pass:
        cmd_parts.append(f"--cluster-pwd={settings.user_pass}")

    cmd_parts.append(f"{settings.rac_host}:{settings.rac_port}")

    result = execute_rac_command(cmd_parts)
    if result and result["returncode"] == 0 and result["stdout"]:
        return parse_rac_output(result["stdout"])

    return []


def get_jobs(settings: Settings, cluster_id: str) -> List[Dict]:
    """
    Получение фоновых заданий через connection list

    В версиях 1С до 8.3.24 нет команды 'job list',
    поэтому получаем задания из connection list.
    """
    from ..monitoring.jobs.reader import JobReader

    reader = JobReader(settings)
    return reader.get_jobs(cluster_id)


@click.group()
def cli():
    """Zabbix-1C Integration Tool"""
    setup_logging()
    pass


@cli.command("check-ras")
@click.option("--config", "-c", help="Path to config file", default=".env")
def check_ras_cmd(config: str):
    """
    Проверка доступности RAS сервиса
    """
    try:
        settings = load_settings(config)

        is_available = check_ras_availability(settings)

        result = {
            "host": settings.rac_host,
            "port": settings.rac_port,
            "available": is_available,
            "rac_path": str(settings.rac_path),
        }

        safe_output(result, indent=2)

        if not is_available:
            sys.exit(1)

    except Exception as e:
        logger.error(f"RAS check failed: {e}")
        sys.exit(1)


@cli.command("discovery")
@click.option("--config", "-c", help="Path to config file", default=".env")
def discovery(config: str):
    """
    Обнаружение кластеров для Zabbix LLD
    """
    try:
        settings = load_settings(config)
        clusters = discover_clusters(settings)

        result = format_lld_data(clusters)
        safe_output(result, indent=2, default=str)

    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        sys.exit(1)


@cli.command("clusters")
@click.option("--config", "-c", help="Path to config file", default=".env")
@click.option("--json-output", is_flag=True, help="Output in JSON format")
def list_clusters(config: str, json_output: bool):
    """
    Список доступных кластеров
    """
    try:
        settings = load_settings(config)
        clusters = discover_clusters(settings)

        if json_output:
            safe_output(clusters, indent=2, default=str)
        else:
            click.echo("\n📊 Доступные кластеры 1С:\n")
            for i, cluster in enumerate(clusters, 1):
                click.echo(f"{i}. {cluster.get('name', '')}")
                click.echo(f"   ID: {cluster.get('id', '')}")
                click.echo(f"   Host: {cluster.get('host', '')}:{cluster.get('port', '')}")
                click.echo(f"   Status: {cluster.get('status', '')}")
                click.echo()

    except Exception as e:
        logger.error(f"Failed to list clusters: {e}")
        sys.exit(1)


@cli.command("infobases")
@click.argument("cluster_id")
@click.option("--config", "-c", help="Path to config file", default=".env")
def get_infobases_cmd(cluster_id: str, config: str):
    """
    Получение информационных баз кластера
    """
    try:
        settings = load_settings(config)
        cluster_id = cluster_id.strip("[]\"'")
        infobases = get_infobases(settings, cluster_id)
        safe_output(infobases, indent=2, default=str)

    except Exception as e:
        logger.error(f"Failed to get infobases: {e}")
        sys.exit(1)


@cli.command("sessions")
@click.argument("cluster_id")
@click.option("--config", "-c", help="Path to config file", default=".env")
def get_sessions_cmd(cluster_id: str, config: str):
    """
    Получение сессий кластера
    """
    try:
        settings = load_settings(config)
        cluster_id = cluster_id.strip("[]\"'")
        sessions = get_sessions(settings, cluster_id)
        safe_output(sessions, indent=2, default=str)

    except Exception as e:
        logger.error(f"Failed to get sessions: {e}")
        sys.exit(1)


@cli.command("jobs")
@click.argument("cluster_id")
@click.option("--config", "-c", help="Path to config file", default=".env")
def get_jobs_cmd(cluster_id: str, config: str):
    """
    Получение фоновых заданий кластера
    """
    try:
        settings = load_settings(config)
        cluster_id = cluster_id.strip("[]\"'")
        jobs = get_jobs(settings, cluster_id)
        safe_output(jobs, indent=2, default=str)

    except Exception as e:
        logger.error(f"Failed to get jobs: {e}")
        sys.exit(1)


@cli.command("metrics")
@click.argument("cluster_id", required=False)
@click.option("--config", "-c", help="Path to config file", default=".env")
@click.option("--check-activity", is_flag=True, help="Check calls-last-5min for active sessions")
@click.option("--check-traffic", is_flag=True, help="Check bytes-last-5min for active sessions")
@click.option("--min-calls", type=int, default=0, help="Minimum calls in last 5 minutes")
@click.option("--min-bytes", type=int, default=0, help="Minimum bytes in last 5 minutes")
def get_metrics(
    config: str,
    cluster_id: Optional[str],
    check_activity: bool,
    check_traffic: bool,
    min_calls: int,
    min_bytes: int,
):
    """
    Получение метрик кластера (для Zabbix)

    Если cluster_id не указан, собирает метрики для всех кластеров

    Опции для фильтрации активных сессий:
        --check-activity  — проверять calls-last-5min
        --check-traffic   — проверять bytes-last-5min
        --min-calls       — мин. количество вызовов (по умолчанию 0)
        --min-bytes       — мин. объём трафика (по умолчанию 0)
    """
    try:
        settings = load_settings(config)

        # Используем ClusterManager для получения метрик с новыми полями
        from ..monitoring.cluster.manager import ClusterManager

        manager = ClusterManager(settings)

        if cluster_id:
            cluster_id = cluster_id.strip("[]\"'")
            metrics = manager.get_cluster_metrics(cluster_id)

            if not metrics:
                safe_output({"error": f"Cluster {cluster_id} not found"})
                sys.exit(1)

            safe_output(metrics, indent=2, default=str)
        else:
            # Метрики для всех кластеров
            clusters = discover_clusters(settings)
            results = []

            for cluster in clusters:
                cid = cluster["id"]
                metrics = manager.get_cluster_metrics(cid)
                if metrics:
                    results.append(metrics)

            safe_output(results, indent=2, default=str)

    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("all")
@click.argument("cluster_id")
@click.option("--config", "-c", help="Path to config file", default=".env")
def get_all(cluster_id: str, config: str):
    """
    Получение всей информации о кластере
    """
    try:
        settings = load_settings(config)
        cluster_id = cluster_id.strip("[]\"'")

        # Получаем информацию о кластере
        clusters = discover_clusters(settings)
        cluster = next((c for c in clusters if c["id"] == cluster_id), None)

        if not cluster:
            safe_output({"error": f"Cluster {cluster_id} not found"})
            sys.exit(1)

        # Получаем все данные
        infobases = get_infobases(settings, cluster_id)
        sessions = get_sessions(settings, cluster_id)
        jobs = get_jobs(settings, cluster_id)

        # Используем строгую проверку активности (все критерии)
        from ..monitoring.session.filters import is_session_active

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

        result = {
            "cluster": {
                "id": cluster["id"],
                "name": cluster["name"],
                "host": cluster["host"],
                "port": cluster["port"],
                "status": cluster["status"],
            },
            "infobases": infobases,
            "sessions": sessions,
            "jobs": jobs,
            "statistics": {
                "total_infobases": len(infobases),
                "total_sessions": len(sessions),
                "active_sessions": active_sessions,
                "total_jobs": len(jobs),
                "active_jobs": sum(1 for j in jobs if j.get("status") == "running"),
            },
            "timestamp": datetime.now().isoformat(),
        }

        safe_output(result, indent=2, default=str)

    except Exception as e:
        logger.error(f"Failed to get cluster info: {e}")
        sys.exit(1)


@cli.command("status")
@click.argument("cluster_id")
@click.option("--config", "-c", help="Path to config file", default=".env")
def get_cluster_status(cluster_id: str, config: str):
    """
    Получение статуса кластера (available/unavailable/unknown)

    Выводит только статус для использования в Zabbix UserParameter
    """
    try:
        settings = load_settings(config)
        cluster_id = cluster_id.strip("[]\"'")

        # Находим кластер в списке
        clusters = discover_clusters(settings)
        cluster = next((c for c in clusters if c["id"] == cluster_id), None)

        if not cluster:
            # Кластер не найден — unknown
            click.echo("unknown")
            sys.exit(0)

        # Выводим только статус
        status = cluster.get("status", "unknown")
        click.echo(status)

    except Exception as e:
        logger.error(f"Failed to get cluster status: {e}")
        # При ошибке возвращаем unknown
        click.echo("unknown")
        sys.exit(0)


@cli.command("memory")
@click.option("--config", "-c", help="Path to config file", default=".env")
def get_process_memory(config: str):
    """
    Получение памяти процессов 1С (rphost, rmngr, ragent)
    """
    try:
        settings = load_settings(config)

        from ..utils.process_memory import get_1c_process_memory

        memory = get_1c_process_memory(settings.rac_host)

        result = {
            "rphost": memory["rphost"],
            "rmngr": memory["rmngr"],
            "ragent": memory["ragent"],
            "total": memory["total"],
        }
        safe_output(result, indent=2)

    except Exception as e:
        logger.error(f"Failed to get process memory: {e}")
        safe_output({"error": str(e)}, indent=2)
        sys.exit(1)


@cli.command("test")
@click.option("--config", "-c", help="Path to config file", default=".env")
def test_connection(config: str):
    """
    Тестирование подключения к 1С
    """
    try:
        settings = load_settings(config)

        safe_print("🔧 Тестирование подключения к 1С...\n")

        # Проверка наличия rac
        safe_print(f"📁 RAC path: {settings.rac_path}")
        if os.path.exists(str(settings.rac_path)):
            safe_print("   ✅ RAC executable found")
        else:
            safe_print("   ❌ RAC executable not found")

        # Проверка доступности RAS
        safe_print(f"\n🌐 RAS: {settings.rac_host}:{settings.rac_port}")
        if check_ras_availability(settings):
            safe_print("   ✅ RAS is available")
        else:
            safe_print("   ❌ RAS is not available")
            sys.exit(1)

        # Проверка кластеров
        clusters = discover_clusters(settings)

        safe_print(f"\n📊 Clusters found: {len(clusters)}")
        for cluster in clusters:
            safe_print(f"   - {cluster['name']} ({cluster['id']})")

            # Проверка сбора метрик
            try:
                sessions = get_sessions(settings, cluster["id"])
                jobs = get_jobs(settings, cluster["id"])

                # Используем строгую проверку активности (все критерии)
                from ..monitoring.session.filters import is_session_active

                total_sessions = len(sessions)
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

                safe_print(
                    f"     ✅ Metrics collected: "
                    f"{total_sessions} sessions, "
                    f"{active_sessions} active (strict), "
                    f"{total_jobs} jobs"
                )
            except Exception as e:
                safe_print(f"     ❌ Error: {e}")

        safe_print("\n✅ Все проверки пройдены успешно")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)


@cli.command("check-config")
@click.option("--config", "-c", help="Path to config file", default=".env")
def check_config_cmd(config: str):
    """
    Проверка корректности настройки конфигурации проекта
    """
    try:
        settings = load_settings(config)

        print("=" * 60)
        print("РЕЗУЛЬТАТЫ ПРОВЕРКИ КОНФИГУРАЦИИ")
        print("=" * 60)
        print()

        results = []
        success_count = 0

        # Проверка RAC_PATH
        rac_path = str(settings.rac_path)
        if not rac_path:
            results.append(("RAC_PATH", False, "Путь к исполняемому файлу не задан"))
        elif not os.path.exists(rac_path):
            results.append(("RAC_PATH", False, f"Файл не найден: {rac_path}"))
        else:
            results.append(("RAC_PATH", True, f"Файл доступен: {rac_path}"))
            success_count += 1

        # Проверка LOG_PATH
        log_path = settings.log_path or "./logs"
        try:
            Path = __import__("pathlib").Path
            path_obj = Path(log_path)
            path_obj.mkdir(parents=True, exist_ok=True)
            test_file = path_obj / ".permission_test"
            test_file.touch()
            test_file.unlink()
            results.append(("LOG_PATH", True, f"Директория для логов доступна: {log_path}"))
            success_count += 1
        except Exception as e:
            results.append(("LOG_PATH", False, f"Ошибка: {e}"))

        # Проверка RAC_HOST
        if not settings.rac_host:
            results.append(("RAC_HOST", False, "Хост RAS не задан"))
        else:
            results.append(("RAC_HOST", True, f"Хост RAS: {settings.rac_host}"))
            success_count += 1

        # Проверка RAC_PORT
        if not settings.rac_port or settings.rac_port <= 0:
            results.append(("RAC_PORT", False, "Порт RAS не задан или недействителен"))
        else:
            results.append(("RAC_PORT", True, f"Порт RAS: {settings.rac_port}"))
            success_count += 1

        # Проверка подключения к RAS
        ras_ok = check_ras_availability(settings)
        if ras_ok:
            results.append(("RAS_CONNECTION", True, "Подключение к RAS успешно установлено"))
            success_count += 1
        else:
            results.append(("RAS_CONNECTION", False, "Ошибка подключения к RAS"))

        total_count = len(results)

        for setting_name, is_valid, message in results:
            status = "+" if is_valid else "-"
            print(f"[{status}] {setting_name:<15} - {message}")

        print("-" * 60)
        print(f"Проверок пройдено: {success_count}/{total_count}")

        if success_count == total_count:
            print(":) Вся конфигурация корректна!")
            sys.exit(0)
        else:
            print(":( Обнаружены проблемы с конфигурацией")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Check config failed: {e}")
        sys.exit(1)


@cli.command("techjournal")
@click.option("--config", "-c", help="Path to config file", default=".env")
@click.option("--period", "-p", "period_minutes", help="Period in minutes", default=5, type=int)
@click.option("--json-output", is_flag=True, help="Output in JSON format")
def techjournal_metrics(config: str, period_minutes: int, json_output: bool):
    """
    Мониторинг техжурнала 1С

    Собирает метрики из логов техжурнала (ошибки, блокировки,
    долгие вызовы, медленный SQL) за указанный период.
    """
    try:
        settings = load_settings(config)

        # Получаем путь к логам техжурнала
        log_base = getattr(settings, "techjournal_log_base", None)
        if not log_base:
            from pathlib import Path
            log_base = getattr(settings, "log_path", "./logs")
            if isinstance(log_base, str):
                log_base = str(Path(log_base).parent / "1c_techjournal")

        from ..monitoring.techjournal import MetricsCollector

        collector = MetricsCollector(log_base)

        if json_output:
            metrics = collector.collect(period_minutes=period_minutes)
            import json
            click.echo(json.dumps(metrics.to_dict(), indent=2, ensure_ascii=False))
        else:
            summary = collector.get_summary(period_minutes=period_minutes)
            click.echo(summary)

    except Exception as e:
        logger.error(f"Failed to collect techjournal metrics: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def monitor():
    """Точка входа для обратной совместимости"""
    args = sys.argv[1:]

    if not args or args[0].startswith("-"):
        sys.argv = [sys.argv[0], "metrics"] + args
    else:
        cluster_id = args[0]
        rest_args = args[1:]
        sys.argv = [sys.argv[0], "metrics", cluster_id] + rest_args

    cli()


# =============================================================================
# Entry points для project.scripts (прямой вызов команд)
# =============================================================================


def discovery():
    """Entry point для zbx-1c-discovery"""
    sys.argv = [sys.argv[0], "discovery"] + sys.argv[1:]
    cli()


def check_ras_cmd():
    """Entry point для zbx-1c-check-ras"""
    sys.argv = [sys.argv[0], "check-ras"] + sys.argv[1:]
    cli()


def list_clusters():
    """Entry point для zbx-1c-clusters"""
    sys.argv = [sys.argv[0], "clusters"] + sys.argv[1:]
    cli()


def get_metrics():
    """Entry point для zbx-1c-metrics"""
    sys.argv = [sys.argv[0], "metrics"] + sys.argv[1:]
    cli()


def get_cluster_status():
    """Entry point для zbx-1c-status"""
    sys.argv = [sys.argv[0], "status"] + sys.argv[1:]
    cli()


def get_infobases_cmd():
    """Entry point для zbx-1c-infobases"""
    sys.argv = [sys.argv[0], "infobases"] + sys.argv[1:]
    cli()


def get_sessions_cmd():
    """Entry point для zbx-1c-sessions"""
    sys.argv = [sys.argv[0], "sessions"] + sys.argv[1:]
    cli()


def get_jobs_cmd():
    """Entry point для zbx-1c-jobs"""
    sys.argv = [sys.argv[0], "jobs"] + sys.argv[1:]
    cli()


def get_all():
    """Entry point для zbx-1c-all"""
    sys.argv = [sys.argv[0], "all"] + sys.argv[1:]
    cli()


def get_process_memory():
    """Entry point для zbx-1c-memory"""
    sys.argv = [sys.argv[0], "memory"] + sys.argv[1:]
    cli()


def test_connection():
    """Entry point для zbx-1c-test"""
    sys.argv = [sys.argv[0], "test"] + sys.argv[1:]
    cli()


def check_config_cmd():
    """Entry point для zbx-1c-check-config"""
    sys.argv = [sys.argv[0], "check-config"] + sys.argv[1:]
    cli()


def techjournal_cmd():
    """Entry point для zbx-1c-techjournal"""
    from .techjournal import techjournal_cli

    techjournal_cli()


if __name__ == "__main__":
    cli()
