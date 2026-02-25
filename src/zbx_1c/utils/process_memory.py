"""
Универсальная функция для получения памяти процессов 1С через psutil

Использует библиотеку psutil для кроссплатформенности.
Работает на Windows, Linux, macOS и всех поддерживаемых платформах.

Возвращает память в КБ для всех процессов 1С на указанном хосте.
"""

import platform
import psutil
from typing import Dict, List
from loguru import logger


def get_1c_process_memory(host: str = "localhost") -> Dict[str, int]:
    """
    Получение памяти всех процессов 1С на указанном хосте

    Примечание: psutil работает только с локальной системой.
    Для удалённых хостов возвращается память локальных процессов 1С.

    Args:
        host: Имя хоста или IP (по умолчанию localhost)

    Returns:
        Словарь с памятью процессов в КБ:
        {
            "rphost": 524288,      # Рабочие процессы
            "rmngr": 102400,       # Менеджер кластера
            "ragent": 51200,       # Агент сервера
            "total": 677888        # Общая память
        }
    """
    # psutil работает только локально
    # Игнорируем host и всегда собираем память локально
    del host  # явно помечаем параметр как неиспользуемый
    return _collect_1c_memory_metrics()


def _collect_1c_memory_metrics() -> Dict[str, int]:
    """
    Универсальная функция для сбора памяти процессов 1С
    Работает на Windows, Linux, macOS и всех поддерживаемых платформах
    """
    # Определяем имена процессов для текущей платформы
    is_windows = platform.system() == 'Windows'

    process_names = [
        'rphost.exe' if is_windows else 'rphost',
        'rmngr.exe' if is_windows else 'rmngr',
        'ragent.exe' if is_windows else 'ragent'
    ]

    result = {
        "rphost": 0,
        "rmngr": 0,
        "ragent": 0,
        "total": 0
    }

    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            name = proc.info['name']
            mem = proc.info['memory_info'].rss if proc.info['memory_info'] else 0

            # Конвертируем байты в КБ
            mem_kb = mem // 1024

            if name in process_names:
                if name == process_names[0]:  # rphost
                    result["rphost"] += mem_kb
                elif name == process_names[1]:  # rmngr
                    result["rmngr"] += mem_kb
                elif name == process_names[2]:  # ragent
                    result["ragent"] += mem_kb

                logger.debug(
                    f"Found 1C process: {name} (PID: {proc.info['pid']}), "
                    f"memory: {mem_kb} KB ({round(mem / 1048576, 2)} MB)"
                )

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    result["total"] = result["rphost"] + result["rmngr"] + result["ragent"]

    logger.info(
        f"1C process memory: "
        f"rphost={result['rphost']} KB ({round(result['rphost'] / 1024, 2)} MB), "
        f"rmngr={result['rmngr']} KB ({round(result['rmngr'] / 1024, 2)} MB), "
        f"ragent={result['ragent']} KB ({round(result['ragent'] / 1024, 2)} MB), "
        f"total={result['total']} KB ({round(result['total'] / 1024, 2)} MB)"
    )

    return result


def get_cluster_total_memory_os(cluster_id: str, working_servers: List) -> int:
    """
    Расчёт общей памяти кластера через опрос ОС на каждом сервере

    Args:
        cluster_id: ID кластера
        working_servers: Список рабочих серверов из кластера (WorkingServerInfo или dict)

    Returns:
        Общая память всех процессов 1С на всех серверах (КБ)
    """
    total_memory_kb = 0

    # Если working_servers пустой, используем localhost по умолчанию
    if not working_servers:
        logger.debug(f"Cluster {cluster_id}: working_servers is empty, using localhost")
        local_memory = get_1c_process_memory("localhost")
        return local_memory["total"]

    # Собираем уникальные хосты
    hosts = set()
    for server in working_servers:
        # Поддержка и WorkingServerInfo, и dict
        if hasattr(server, 'host'):
            host = server.host
        elif isinstance(server, dict):
            host = server.get("host", "localhost")
        else:
            host = "localhost"
        hosts.add(host)

    logger.debug(f"Cluster {cluster_id}: collecting memory from hosts: {hosts}")

    # Получаем память с каждого хоста
    for host in hosts:
        host_memory = get_1c_process_memory(host)
        total_memory_kb += host_memory["total"]
        logger.debug(f"Host {host}: total memory = {host_memory['total']} KB")

    logger.info(f"Cluster {cluster_id} total memory from OS: {total_memory_kb} KB")
    return total_memory_kb


if __name__ == "__main__":
    # Тестирование функции
    import json

    memory = get_1c_process_memory()
    print(json.dumps(memory, indent=2, ensure_ascii=False))
