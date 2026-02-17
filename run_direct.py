#!/usr/bin/env python
"""
Упрощенная версия без Pydantic для тестирования
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
import socket
from datetime import datetime

# Добавляем путь к src
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from zbx_1c.core.config import Settings


def safe_print(text: str):
    """Безопасный вывод в консоль"""
    try:
        print(text)
    except UnicodeEncodeError:
        try:
            print(text.encode("ascii", errors="replace").decode("ascii"))
        except:
            print(str(text).encode("ascii", errors="replace").decode("ascii"))


def execute_rac_command(cmd_parts: List[str]) -> Optional[Dict]:
    """Выполнение команды rac"""
    try:
        safe_print(f"Executing: {' '.join(cmd_parts)}")

        result = subprocess.run(cmd_parts, capture_output=True, timeout=30)

        # Пробуем декодировать вывод
        for enc in ["cp866", "cp1251", "utf-8"]:
            try:
                stdout = result.stdout.decode(enc, errors="replace")
                stderr = result.stderr.decode(enc, errors="replace")
                return {"returncode": result.returncode, "stdout": stdout, "stderr": stderr}
            except:
                continue

        return {
            "returncode": result.returncode,
            "stdout": result.stdout.decode("cp866", errors="replace"),
            "stderr": result.stderr.decode("cp866", errors="replace"),
        }

    except Exception as e:
        safe_print(f"Ошибка выполнения: {e}")
        return None


def parse_rac_output(output: str) -> List[Dict[str, Any]]:
    """Парсинг вывода rac утилиты"""
    if not output or not output.strip():
        return []

    result = []
    current_item = {}

    for line in output.split("\n"):
        line = line.strip()
        if not line:
            if current_item:
                result.append(current_item)
                current_item = {}
            continue

        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            value = value.strip()

            # Убираем кавычки
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]

            # Конвертация типов
            if value.lower() in ("true", "false"):
                current_item[key] = value.lower() == "true"
            elif value.isdigit():
                current_item[key] = int(value)
            else:
                current_item[key] = value

    if current_item:
        result.append(current_item)

    return result


def discover_clusters(settings: Settings) -> List[Dict]:
    """Обнаружение кластеров"""

    cmd_parts = [
        str(settings.rac_path),
        "cluster",
        "list",
        f"{settings.rac_host}:{settings.rac_port}",
    ]

    safe_print(f"\nExecuting discovery command...")

    result = execute_rac_command(cmd_parts)
    if not result or result["returncode"] != 0 or not result["stdout"]:
        safe_print("Не удалось получить список кластеров")
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
                "status": data.get("status", "unknown"),
            }

            if cluster["id"]:
                clusters.append(cluster)
                safe_print(f"Найден кластер: {cluster['name']} ({cluster['id']})")
        except Exception as e:
            safe_print(f"Ошибка парсинга кластера: {e}")

    return clusters


def get_infobases(settings: Settings, cluster_id: str) -> List[Dict]:
    """Получение информационных баз"""

    cmd_parts = [
        str(settings.rac_path),
        "infobase",
        "summary",
        "list",
        f"--cluster={cluster_id}",
        f"--cluster-user={settings.user_name}",
        f"--cluster-pwd={settings.user_pass}",
        f"{settings.rac_host}:{settings.rac_port}",
    ]

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
        f"--cluster-user={settings.user_name}",
        f"--cluster-pwd={settings.user_pass}",
        f"{settings.rac_host}:{settings.rac_port}",
    ]

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
        f"--cluster-user={settings.user_name}",
        f"--cluster-pwd={settings.user_pass}",
        f"{settings.rac_host}:{settings.rac_port}",
    ]

    result = execute_rac_command(cmd_parts)
    if result and result["returncode"] == 0 and result["stdout"]:
        return parse_rac_output(result["stdout"])

    return []


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


def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python run_direct_simple.py check-ras            - проверка доступности RAS")
        print("  python run_direct_simple.py discovery            - обнаружение кластеров")
        print("  python run_direct_simple.py infobases <id>       - инфобазы кластера")
        print("  python run_direct_simple.py sessions <id>        - сессии кластера")
        print("  python run_direct_simple.py jobs <id>            - фоновые задания")
        print("  python run_direct_simple.py metrics <id>         - метрики кластера")
        return 1

    command = sys.argv[1]

    try:
        settings = Settings()
        safe_print(f"RAC_PATH: {settings.rac_path}")
        safe_print(f"RAS: {settings.rac_host}:{settings.rac_port}")
        safe_print(f"Аутентификация: {'включена' if settings.user_name else 'выключена'}")

        if command == "check-ras":
            is_available = check_ras_availability(settings)
            result = {
                "host": settings.rac_host,
                "port": settings.rac_port,
                "available": is_available,
                "rac_path": str(settings.rac_path),
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if is_available else 1

        elif command == "discovery":
            clusters = discover_clusters(settings)
            result = {
                "data": [
                    {
                        "{#CLUSTER.ID}": c["id"],
                        "{#CLUSTER.NAME}": c["name"],
                        "{#CLUSTER.HOST}": c["host"],
                        "{#CLUSTER.PORT}": c["port"],
                    }
                    for c in clusters
                ]
            }
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return 0

        elif command == "infobases":
            if len(sys.argv) < 3:
                print("Ошибка: необходимо указать ID кластера")
                return 1

            cluster_id = sys.argv[2].strip("[]\"'")
            infobases = get_infobases(settings, cluster_id)
            print(json.dumps(infobases, indent=2, ensure_ascii=False, default=str))
            return 0

        elif command == "sessions":
            if len(sys.argv) < 3:
                print("Ошибка: необходимо указать ID кластера")
                return 1

            cluster_id = sys.argv[2].strip("[]\"'")
            sessions = get_sessions(settings, cluster_id)
            print(json.dumps(sessions, indent=2, ensure_ascii=False, default=str))
            return 0

        elif command == "jobs":
            if len(sys.argv) < 3:
                print("Ошибка: необходимо указать ID кластера")
                return 1

            cluster_id = sys.argv[2].strip("[]\"'")
            jobs = get_jobs(settings, cluster_id)
            print(json.dumps(jobs, indent=2, ensure_ascii=False, default=str))
            return 0

        elif command == "metrics":
            if len(sys.argv) < 3:
                print("Ошибка: необходимо указать ID кластера")
                return 1

            cluster_id = sys.argv[2].strip("[]\"'")

            # Получаем информацию о кластере
            clusters = discover_clusters(settings)
            cluster = None
            for c in clusters:
                if c["id"] == cluster_id:
                    cluster = c
                    break

            if not cluster:
                print(f"Кластер {cluster_id} не найден")
                return 1

            # Получаем сессии и задания
            sessions = get_sessions(settings, cluster_id)
            jobs = get_jobs(settings, cluster_id)

            # Подсчет метрик
            total_sessions = len(sessions)
            active_sessions = sum(
                1 for s in sessions if s.get("session-id") and s.get("hibernate") == "no"
            )

            total_jobs = len(jobs)
            active_jobs = sum(1 for j in jobs if j.get("status") == "running")

            result = {
                "cluster": {
                    "id": cluster["id"],
                    "name": cluster["name"],
                    "status": cluster["status"],
                },
                "metrics": [
                    {"key": "zbx1cpy.cluster.total_sessions", "value": total_sessions},
                    {"key": "zbx1cpy.cluster.active_sessions", "value": active_sessions},
                    {"key": "zbx1cpy.cluster.total_jobs", "value": total_jobs},
                    {"key": "zbx1cpy.cluster.active_jobs", "value": active_jobs},
                ],
            }

            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return 0

        else:
            print(f"Неизвестная команда: {command}")
            return 1

    except Exception as e:
        safe_print(f"Ошибка: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
