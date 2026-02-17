#!/usr/bin/env python3
"""
CLI команды для интеграции с Zabbix
Работает точно так же как run_direct.py
"""

import sys
import json
import click
from typing import Optional, List, Dict
from datetime import datetime
import socket
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
            cluster = {
                "id": data.get("cluster"),
                "name": data.get("name", "unknown"),
                "host": data.get("host", settings.rac_host),
                "port": data.get("port", settings.rac_port),
                "status": "unknown",
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
    """Получение фоновых заданий"""
    cmd_parts = [
        str(settings.rac_path),
        "job",
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
def get_metrics(config: str, cluster_id: Optional[str]):
    """
    Получение метрик кластера (для Zabbix)

    Если cluster_id не указан, собирает метрики для всех кластеров
    """
    try:
        settings = load_settings(config)

        if cluster_id:
            cluster_id = cluster_id.strip("[]\"'")
            # Получаем информацию о кластере
            clusters = discover_clusters(settings)
            cluster = None
            for c in clusters:
                if c["id"] == cluster_id:
                    cluster = c
                    break

            if not cluster:
                safe_output({"error": f"Cluster {cluster_id} not found"})
                sys.exit(1)

            # Получаем сессии и задания
            sessions = get_sessions(settings, cluster_id)
            jobs = get_jobs(settings, cluster_id)

            # Подсчет метрик
            # total_sessions — общее количество сессий
            total_sessions = len(sessions)
            # active_sessions — сессии, которые не в hibernate
            active_sessions = sum(
                1 for s in sessions if s.get("hibernate") == "no"
            )

            # total_jobs — общее количество заданий
            total_jobs = len(jobs)
            # active_bg_jobs — задания со статусом "running"
            active_jobs = sum(1 for j in jobs if j.get("status") == "running")

            result = {
                "cluster": {
                    "id": cluster["id"],
                    "name": cluster["name"],
                    "status": cluster["status"],
                },
                "metrics": {
                    "total_sessions": total_sessions,
                    "active_sessions": active_sessions,
                    "total_jobs": total_jobs,
                    "active_bg_jobs": active_jobs,
                    "status": 1,
                },
            }

            safe_output(result, indent=2, default=str)
        else:
            # Метрики для всех кластеров
            clusters = discover_clusters(settings)
            results = []

            for cluster in clusters:
                cid = cluster["id"]
                sessions = get_sessions(settings, cid)
                jobs = get_jobs(settings, cid)

                # total_sessions — общее количество сессий
                total_sessions = len(sessions)
                # active_sessions — сессии, которые не в hibernate
                active_sessions = sum(
                    1 for s in sessions if s.get("hibernate") == "no"
                )

                # total_jobs — общее количество заданий
                total_jobs = len(jobs)
                # active_bg_jobs — задания со статусом "running"
                active_jobs = sum(1 for j in jobs if j.get("status") == "running")

                results.append(
                    {
                        "cluster": {
                            "id": cid,
                            "name": cluster["name"],
                            "status": cluster["status"],
                        },
                        "metrics": {
                            "total_sessions": total_sessions,
                            "active_sessions": active_sessions,
                            "total_jobs": total_jobs,
                            "active_bg_jobs": active_jobs,
                            "status": 1,
                        },
                    }
                )

            safe_output(results, indent=2, default=str)

    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
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
                "active_sessions": sum(
                    1 for s in sessions if s.get("hibernate") == "no"
                ),
                "total_jobs": len(jobs),
                "active_jobs": sum(1 for j in jobs if j.get("status") == "running"),
            },
            "timestamp": datetime.now().isoformat(),
        }

        safe_output(result, indent=2, default=str)

    except Exception as e:
        logger.error(f"Failed to get cluster info: {e}")
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
        if settings.rac_path.exists():  # type: ignore[attr-defined]
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

                total_sessions = len(sessions)
                active_sessions = sum(
                    1 for s in sessions if s.get("session-id") and s.get("hibernate") == "no"
                )
                total_jobs = len(jobs)

                safe_print(
                    f"     ✅ Metrics collected: "
                    f"{total_sessions} sessions, "
                    f"{active_sessions} active, "
                    f"{total_jobs} jobs"
                )
            except Exception as e:
                safe_print(f"     ❌ Error: {e}")

        safe_print("\n✅ Все проверки пройдены успешно")

    except Exception as e:
        logger.error(f"Test failed: {e}")
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


if __name__ == "__main__":
    cli()
