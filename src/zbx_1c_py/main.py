"""
Центральный модуль мониторинга 1С для Zabbix.
Реализует схему Master/Dependent items для эффективного сбора метрик.
Поддерживает автоматическую масштабируемость: один вызов = один кластер.

Модуль предоставляет следующие функции:
- Автоматическое обнаружение кластеров 1С (LLD - Low Level Discovery)
- Сбор метрик сессий и фоновых заданий для каждого кластера
- Проверка доступности сервиса RAS
- Интеграция с Zabbix через JSON-ответы

Аргументы командной строки:
- --discovery: Возвращает JSON с информацией о кластерах для LLD
- --check-ras: Проверяет доступность сервиса RAS
- <cluster_id>: Собирает метрики для указанного кластера
"""

import json
import os
import sys
import subprocess
import io
from typing import List, Dict, Any
from loguru import logger

# Импорт ваших модулей
try:
    from .clusters import all_available_clusters, check_ras_availability
    from .session import fetch_raw_sessions
    from .session_active import filter_active_sessions
    from .background_jobs import is_background_job_active
    from .utils.helpers import parse_rac_output, decode_output
    from .config import settings
except ImportError:
    # Fallback для случая, когда файл запускается напрямую
    from clusters import all_available_clusters, check_ras_availability
    from session import fetch_raw_sessions
    from session_active import filter_active_sessions
    from background_jobs import is_background_job_active
    from utils.helpers import parse_rac_output, decode_output
    from config import settings


# Экспортируем get_all_clusters как функцию модуля main для интеграционных тестов
def get_all_clusters():
    """
    Обертка для функции get_all_clusters из модуля clusters.
    
    Эта функция предоставляется для интеграционных тестов, которые ожидают
    наличие этой функции в модуле main.
    """
    from . import clusters as clusters_module  # Импортируем локально, чтобы избежать циклических импортов
    return clusters_module.get_all_clusters()

# Настройка логирования: только ошибки и только в файл
# В тестовой среде не добавляем логгирование в файл

if not os.getenv("PYTEST_CURRENT_TEST"):
    logger.remove()
    log_file_path = os.path.join(settings.log_path, "1c_monitoring.log")

    logger.add(
        log_file_path,
        rotation="5 MB",
        level="ERROR",
        encoding="utf-8",
    )

# Принудительная установка кодировки UTF-8 для корректного вывода в Zabbix
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def get_discovery_json() -> str:
    """
    Генерирует JSON для Zabbix LLD (Low-Level Discovery).

    Функция создает структурированный JSON-ответ, содержащий информацию
    о доступных кластерах 1С, который используется Zabbix для
    автоматического обнаружения и мониторинга элементов.

    Returns:
        str: JSON-строка с массивом объектов, каждый из которых содержит
             уникальный идентификатор кластера ({#CLUSTER_ID}) и его имя ({#CLUSTER_NAME}).

    Example:
        [
            {
                "{#CLUSTER_ID}": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
                "{#CLUSTER_NAME}": "Основной кластер"
            },
            {
                "{#CLUSTER_ID}": "b2c3d4e5-6789-01ab-cdef-2345678901bc",
                "{#CLUSTER_NAME}": "Резервный кластер"
            }
        ]
    """
    discovery_data = [
        {"{#CLUSTER_ID}": c.get("cluster"), "{#CLUSTER_NAME}": c.get("name")}
        for c in get_all_clusters()
        if c.get("cluster")
    ]
    return json.dumps(discovery_data, ensure_ascii=False)


def fetch_background_jobs_raw(cluster_id: str) -> List[Dict[str, Any]]:
    """
    Получает список фоновых заданий для указанного кластера 1С.

    Функция выполняет команду rac.exe для получения информации о фоновых
    заданиях, запущенных в указанном кластере 1С. Результат парсится
    и возвращается в виде списка словарей.

    Args:
        cluster_id (str): Уникальный идентификатор кластера 1С

    Returns:
        List[Dict[str, Any]]: Список словарей с информацией о фоновых заданиях,
                             где каждый словарь содержит поля, полученные
                             из вывода rac.exe (например, state, duration, started-at)

    Raises:
        subprocess.TimeoutExpired: Если выполнение команды превышает 15 секунд
        FileNotFoundError: Если не найден исполняемый файл rac.exe
        subprocess.SubprocessError: При других ошибках выполнения процесса

    Example:
        [
            {
                "job-id": "123",
                "state": "active",
                "duration": "125000",
                "started-at": "2026-02-11T10:04:00",
                "user-name": "Иванов И.И.",
                "description": "Расчёт зарплаты"
            }
        ]
    """
    cmd = [
        settings.rac_path,
        f"{settings.rac_host}:{settings.rac_port}",
        "background-job",
        "list",
        "--cluster",
        cluster_id,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=15, check=False)
        if result.returncode == 0:
            return parse_rac_output(decode_output(result.stdout))
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.error(f"Ошибка получения задач для {cluster_id}: {e}")
    return []


def collect_metrics_for_cluster(cluster_id: str) -> str:
    """
    Сбор метрик для ОДНОГО кластера по его ID.
    Возвращает объект (не массив!) для корректной работы JSONPath в Zabbix.

    Функция собирает и анализирует метрики для указанного кластера 1С:
    - Общее количество сессий
    - Количество активных сессий (пользователи, реально работающие в системе)
    - Количество активных фоновых заданий

    Args:
        cluster_id (str): Уникальный идентификатор кластера 1С

    Returns:
        str: JSON-строка с объектом метрик, содержащим:
             - cluster_id: идентификатор кластера
             - cluster_name: имя кластера
             - metrics: объект с метриками (total_sessions, active_sessions, active_bg_jobs, status)

    Example:
        {
            "cluster_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
            "cluster_name": "Основной кластер",
            "metrics": {
                "total_sessions": 25,
                "active_sessions": 8,
                "active_bg_jobs": 2,
                "status": 1
            }
        }

    Note:
        - Возвращает объект, а не массив, для корректной работы JSONPath в Zabbix
        - Если кластер не найден или произошла ошибка, возвращается объект с status: 0
        - Активные сессии определяются с порогом 10 минут
        - Активные фоновые задания определяются с максимальной длительностью 60 минут
    """
    for cluster in all_available_clusters:
        c_id = str(cluster.get("cluster", ""))
        c_name = str(cluster.get("name", "Unknown"))

        if c_id != cluster_id:
            continue

        try:
            # Сессии
            raw_sessions = fetch_raw_sessions(c_id)
            active_sessions = filter_active_sessions(raw_sessions, threshold_minutes=10)

            # Фоновые задания
            raw_jobs = fetch_background_jobs_raw(c_id)
            active_jobs = [
                j for j in raw_jobs if is_background_job_active(j, max_duration_minutes=60)
            ]

            return json.dumps(
                {
                    "cluster_id": c_id,
                    "cluster_name": c_name,
                    "metrics": {
                        "total_sessions": len(raw_sessions),
                        "active_sessions": len(active_sessions),
                        "active_bg_jobs": len(active_jobs),
                        "status": 1,
                    },
                },
                ensure_ascii=False,
            )
        except (subprocess.SubprocessError, OSError, ValueError) as e:
            logger.error(f"Ошибка кластера {c_name} ({c_id}): {e}")
            break

    return json.dumps(
        {
            "cluster_id": cluster_id,
            "cluster_name": "Unknown",
            "metrics": {
                "total_sessions": 0,
                "active_sessions": 0,
                "active_bg_jobs": 0,
                "status": 0,
            },
        },
        ensure_ascii=False,
    )


def main():
    """
    Главная точка входа в приложение.

    Функция обрабатывает аргументы командной строки и выполняет соответствующие действия:
    - Режим обнаружения (--discovery): возвращает JSON с информацией о кластерах
    - Режим проверки RAS (--check-ras): проверяет доступность сервиса RAS
    - Режим сбора метрик: принимает ID кластера и возвращает метрики для него
    - Режим по умолчанию: если аргументы не переданы, обрабатывает первый доступный кластер

    Args:
        None: Читает аргументы из sys.argv

    Returns:
        None: Выводит результат в stdout в формате JSON

    Exit codes:
        0: Успешное выполнение (вывод в stdout)

    Examples:
        # Обнаружение кластеров
        python main.py --discovery

        # Проверка доступности RAS
        python main.py --check-ras

        # Сбор метрик для конкретного кластера
        python main.py a1b2c3d4-5678-90ab-cdef-1234567890ab

        # Сбор метрик для первого кластера (по умолчанию)
        python main.py
    """
    # Обработка аргументов командной строки
    # Отфильтровываем системные флаги для получения позиционных аргументов (ID кластера)
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]

    if "--discovery" in sys.argv:
        # Режим обнаружения: возвращаем список кластеров для LLD
        print(get_discovery_json())

    elif "--check-ras" in sys.argv:
        # НОВОЕ: Режим проверки доступности самого сервиса RAS
        status = check_ras_availability()
        print(json.dumps(status, ensure_ascii=False))

    elif args:
        # Режим сбора метрик: первый аргумент = cluster_id
        target_cluster_id = args[0].strip()
        print(collect_metrics_for_cluster(target_cluster_id))

    else:
        # Логика по умолчанию (если аргументы не переданы)
        if all_available_clusters:
            first_cluster_id = str(all_available_clusters[0].get("cluster", ""))
            print(collect_metrics_for_cluster(first_cluster_id))
        else:
            print(
                json.dumps(
                    {
                        "cluster_id": "",
                        "cluster_name": "No clusters available",
                        "metrics": {
                            "total_sessions": 0,
                            "active_sessions": 0,
                            "active_bg_jobs": 0,
                            "status": 0,
                        },
                    },
                    ensure_ascii=False,
                )
            )

    # Завершение работы
    try:
        sys.stdout.flush()
    except BrokenPipeError:
        pass


if __name__ == "__main__":
    main()
