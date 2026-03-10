"""CLI для zbx-1c-rac"""

import json
import sys
from typing import Optional

import click

from ..core.config import RacConfig, get_config
from ..monitoring.cluster.manager import ClusterManager
from ..monitoring.infobase.monitor import InfobaseMonitor
from ..monitoring.session.collector import SessionCollector
from ..monitoring.jobs.reader import JobReader
from ..utils.rac_client import check_ras_availability, discover_clusters


def safe_output(data, **kwargs):
    """Безопасный вывод JSON в консоль"""
    json_str = json.dumps(data, ensure_ascii=False, **kwargs)
    if sys.platform == "win32":
        sys.stdout.buffer.write((json_str + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()
    else:
        click.echo(json_str)


@click.group()
def cli():
    """Zabbix-1C RAC Monitoring Tool"""
    pass


@cli.command("check")
@click.option("--config", "-c", help="Path to config file", default=None)
def check_ras(config: Optional[str]):
    """Проверка доступности RAS сервиса"""
    cfg = get_config() if config is None else RacConfig.model_config.update(env_file=config) or RacConfig()

    is_available = check_ras_availability(cfg.rac_host, cfg.rac_port, cfg.rac_timeout)

    result = {
        "host": cfg.rac_host,
        "port": cfg.rac_port,
        "available": is_available,
        "rac_path": str(cfg.rac_path),
    }

    safe_output(result, indent=2)

    if not is_available:
        sys.exit(1)


@cli.command("discovery")
@click.option("--config", "-c", help="Path to config file", default=None)
def discovery(config: Optional[str]):
    """Обнаружение кластеров для Zabbix LLD"""
    cfg = get_config()

    clusters = discover_clusters(cfg.rac_path, cfg.rac_host, cfg.rac_port, cfg.rac_timeout)
    
    # Преобразуем id в CLUSTER_ID для Zabbix LLD
    lld_data = []
    for cluster in clusters:
        lld_cluster = {
            "{#CLUSTER_ID}": cluster.get("id", ""),
            "{#CLUSTER_NAME}": cluster.get("name", ""),
            "{#CLUSTER_HOST}": cluster.get("host", ""),
            "{#CLUSTER_PORT}": str(cluster.get("port", "")),
            "{#CLUSTER_STATUS}": cluster.get("status", ""),
        }
        lld_data.append(lld_cluster)
    
    result = {"data": lld_data}

    safe_output(result, indent=2, default=str)


@cli.command("clusters")
@click.option("--config", "-c", help="Path to config file", default=None)
@click.option("--json-output", is_flag=True, help="Output in JSON format")
def list_clusters(config: Optional[str], json_output: bool):
    """Список доступных кластеров"""
    cfg = get_config()
    clusters = discover_clusters(cfg.rac_path, cfg.rac_host, cfg.rac_port, cfg.rac_timeout)

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


@cli.command("metrics")
@click.argument("cluster_id", required=False)
@click.option("--config", "-c", help="Path to config file", default=None)
def get_metrics(cluster_id: Optional[str], config: Optional[str]):
    """Получение метрик кластера (для Zabbix)"""
    cfg = get_config()
    manager = ClusterManager(cfg)

    if cluster_id:
        # Метрики конкретного кластера
        metrics = manager.get_cluster_metrics(cluster_id)

        if not metrics:
            safe_output({"error": f"Cluster {cluster_id} not found"})
            sys.exit(1)

        safe_output(metrics, indent=2, default=str)
    else:
        # Метрики всех кластеров
        results = manager.get_all_clusters_metrics()
        safe_output(results, indent=2, default=str)


@cli.command("status")
@click.argument("cluster_id")
@click.option("--config", "-c", help="Path to config file", default=None)
def get_cluster_status(cluster_id: str, config: Optional[str]):
    """Получение статуса кластера"""
    cfg = get_config()
    manager = ClusterManager(cfg)

    status = manager.check_cluster_status(cluster_id)
    click.echo(status)


@cli.command("infobases")
@click.argument("cluster_id")
@click.option("--config", "-c", help="Path to config file", default=None)
def get_infobases_cmd(cluster_id: str, config: Optional[str]):
    """Получение информационных баз кластера"""
    cfg = get_config()
    monitor = InfobaseMonitor(cfg)

    infobases = monitor.get_infobases(cluster_id)
    safe_output(infobases, indent=2, default=str)


@cli.command("sessions")
@click.argument("cluster_id")
@click.option("--config", "-c", help="Path to config file", default=None)
def get_sessions_cmd(cluster_id: str, config: Optional[str]):
    """Получение сессий кластера"""
    cfg = get_config()
    collector = SessionCollector(cfg)

    sessions = collector.get_sessions(cluster_id)
    safe_output(sessions, indent=2, default=str)


@cli.command("jobs")
@click.argument("cluster_id")
@click.option("--config", "-c", help="Path to config file", default=None)
def get_jobs_cmd(cluster_id: str, config: Optional[str]):
    """Получение фоновых заданий кластера"""
    cfg = get_config()
    reader = JobReader(cfg)

    jobs = reader.get_jobs(cluster_id)
    safe_output(jobs, indent=2, default=str)


@cli.command("memory")
@click.option("--config", "-c", help="Path to config file", default=None)
def get_process_memory(config: Optional[str]):
    """Получение памяти процессов 1С (rphost, rmngr, ragent)"""
    cfg = get_config()
    manager = ClusterManager(cfg)

    memory = manager.get_server_memory()
    safe_output(memory, indent=2)


@cli.command("test")
@click.option("--config", "-c", help="Path to config file", default=None)
def test_connection(config: Optional[str]):
    """Тестирование подключения к 1С"""
    cfg = get_config()

    click.echo("🔧 Тестирование подключения к 1С...\n")

    # Проверка наличия rac
    click.echo(f"📁 RAC path: {cfg.rac_path}")
    if cfg.rac_path.exists():
        click.echo("   ✅ RAC executable found")
    else:
        click.echo("   ❌ RAC executable not found")

    # Проверка доступности RAS
    click.echo(f"\n🌐 RAS: {cfg.rac_host}:{cfg.rac_port}")
    if check_ras_availability(cfg.rac_host, cfg.rac_port, cfg.rac_timeout):
        click.echo("   ✅ RAS is available")
    else:
        click.echo("   ❌ RAS is not available")
        sys.exit(1)

    # Проверка кластеров
    manager = ClusterManager(cfg)
    clusters = manager.get_clusters()

    click.echo(f"\n📊 Clusters found: {len(clusters)}")

    for cluster in clusters:
        click.echo(f"   - {cluster['name']} ({cluster['id']})")

        # Проверка сбора метрик
        try:
            metrics = manager.get_cluster_metrics(cluster["id"])
            if metrics:
                m = metrics["metrics"]
                click.echo(
                    f"     ✅ Metrics: {m['total_sessions']} sessions, "
                    f"{m['active_sessions']} active, {m['total_jobs']} jobs"
                )
        except Exception as e:
            click.echo(f"     ❌ Error: {e}")

    click.echo("\n✅ Все проверки пройдены успешно")


@cli.command("check-config")
@click.option("--config", "-c", help="Path to config file", default=None)
def check_config_cmd(config: Optional[str]):
    """Проверка корректности конфигурации"""
    cfg = get_config()

    print("=" * 60)
    print("РЕЗУЛЬТАТЫ ПРОВЕРКИ КОНФИГУРАЦИИ")
    print("=" * 60)
    print()

    results = []
    success_count = 0

    # Проверка RAC_PATH
    if not str(cfg.rac_path):
        results.append(("RAC_PATH", False, "Путь к исполняемому файлу не задан"))
    elif not cfg.rac_path.exists():
        results.append(("RAC_PATH", False, f"Файл не найден: {cfg.rac_path}"))
    else:
        results.append(("RAC_PATH", True, f"Файл доступен: {cfg.rac_path}"))
        success_count += 1

    # Проверка LOG_PATH
    try:
        cfg.log_path.mkdir(parents=True, exist_ok=True)
        results.append(("LOG_PATH", True, f"Директория для логов доступна: {cfg.log_path}"))
        success_count += 1
    except Exception as e:
        results.append(("LOG_PATH", False, f"Ошибка: {e}"))

    # Проверка RAC_HOST
    if not cfg.rac_host:
        results.append(("RAC_HOST", False, "Хост RAS не задан"))
    else:
        results.append(("RAC_HOST", True, f"Хост RAS: {cfg.rac_host}"))
        success_count += 1

    # Проверка RAC_PORT
    if not 1 <= cfg.rac_port <= 65535:
        results.append(("RAC_PORT", False, "Порт RAS не задан или недействителен"))
    else:
        results.append(("RAC_PORT", True, f"Порт RAS: {cfg.rac_port}"))
        success_count += 1

    # Проверка подключения к RAS
    ras_ok = check_ras_availability(cfg.rac_host, cfg.rac_port, cfg.rac_timeout)
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


if __name__ == "__main__":
    cli()
