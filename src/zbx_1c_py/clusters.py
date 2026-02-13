"""
Модуль для управления кластерами 1С:Предприятия через утилиту rac.exe.

Обеспечивает:
1. Получение полного списка доступных кластеров.
2. Проверку доступности сервиса RAS.
3. Безопасное извлечение идентификаторов (UUID) кластеров.
4. Обработку системных ошибок при взаимодействии с RAS.

Модуль предоставляет функции для:
- Проверки доступности RAS-сервиса
- Получения информации о кластерах
- Извлечения идентификаторов кластеров
- Инициализации глобальных данных о кластерах
"""

import os
import subprocess
import sys
from typing import List, Dict, Any, Optional
from loguru import logger

# Предполагается, что эти модули находятся в той же директории
try:
    from .config import settings
    from .utils.helpers import parse_rac_output, decode_output
except ImportError:
    # Fallback для случая, когда файл запускается напрямую
    from config import settings
    from utils.helpers import parse_rac_output, decode_output

if not os.getenv("PYTEST_CURRENT_TEST"):
    logger.remove()
    log_file_path = os.path.join(settings.log_path, "1c_clusters.log")

    logger.add(
        log_file_path,
        rotation="5 MB",
        level="ERROR",
        encoding="utf-8",
    )


def check_ras_availability() -> Dict[str, Any]:
    """
    Проверяет доступность сервиса RAS (Remote Administration Service) 1С.

    Функция отправляет базовый запрос к RAS-сервису для проверки его
    работоспособности и готовности принимать команды. Используется
    для диагностики связи перед выполнением основных операций мониторинга.

    Returns:
        Dict[str, Any]: Словарь с результатами проверки, содержащий:
            - available (bool): Доступен ли сервис (True/False)
            - message (str): Сообщение о статусе или ошибке
            - code (int): Код результата (0 - успех, 404 - файл не найден и т.д.)

    Example:
        >>> result = check_ras_availability()
        >>> if result['available']:
        ...     print(f"RAS доступен: {result['message']}")
        ... else:
        ...     print(f"Ошибка: {result['message']}")

    Note:
        - Использует короткий таймаут (5 секунд) для быстрой проверки
        - В случае ошибки возвращает структурированную информацию об ошибке
        - Может вернуть различные коды ошибок в зависимости от ситуации
    """
    rac_path = settings.rac_path
    ras_address = f"{settings.rac_host}:{settings.rac_port}"
    command = [rac_path, ras_address, "cluster", "list"]

    try:
        # Пытаемся получить список кластеров с коротким таймаутом
        result = subprocess.run(command, capture_output=True, text=False, check=False, timeout=5)

        if result.returncode == 0:
            return {"available": True, "message": "RAS is reachable", "code": 0}

        stderr_text = decode_output(result.stderr)
        return {
            "available": False,
            "message": f"RAC Error (Code {result.returncode}): {stderr_text}",
            "code": result.returncode,
        }

    except subprocess.TimeoutExpired:
        return {
            "available": False,
            "message": "Timeout: RAS service is not responding",
            "code": 408,
        }
    except FileNotFoundError:
        return {"available": False, "message": f"File not found: {rac_path}", "code": 404}
    except (PermissionError, OSError) as e:
        return {"available": False, "message": f"System error: {str(e)}", "code": 500}


def get_all_clusters() -> List[Dict[str, Any]]:
    """
    Выполняет запрос к RAS и возвращает список всех обнаруженных кластеров 1С.

    Функция использует утилиту rac.exe для получения информации обо всех
    кластерах, зарегистрированных в RAS-сервисе. Результат парсится и
    возвращается в виде списка словарей с информацией о каждом кластере.

    Returns:
        List[Dict[str, Any]]: Список словарей, где каждый словарь содержит
                             информацию о кластере 1С, включая:
                             - cluster: UUID кластера
                             - name: имя кластера
                             - другие поля в зависимости от конфигурации кластера

    Raises:
        subprocess.TimeoutExpired: Если выполнение команды превышает 15 секунд
        FileNotFoundError: Если не найден исполняемый файл rac.exe
        subprocess.SubprocessError: При других ошибках выполнения процесса

    Example:
        >>> clusters = get_all_clusters()
        >>> for cluster in clusters:
        ...     print(f"Кластер: {cluster['name']} (ID: {cluster['cluster']})")

    Note:
        - Использует таймаут 15 секунд для предотвращения зависания
        - В случае ошибки возвращает пустой список
        - Ошибки логируются в файл 1c_clusters.log
    """
    rac_path = settings.rac_path
    ras_address = f"{settings.rac_host}:{settings.rac_port}"
    command = [rac_path, ras_address, "cluster", "list"]

    try:
        # Запускаем процесс с ограничением по времени
        result = subprocess.run(command, capture_output=True, check=False, text=False, timeout=15)

        if result.returncode == 0:
            decoded_text = decode_output(result.stdout)
            return parse_rac_output(decoded_text)

        stderr_text = decode_output(result.stderr)
        logger.error(f"RAC ошибка (код {result.returncode}): {stderr_text}")

    except FileNotFoundError:
        logger.error(f"Файл не найден: {rac_path}. Проверьте настройки.")
    except subprocess.TimeoutExpired:
        logger.warning(f"Сервер RAS {ras_address} не ответил за 15 секунд.")
    except subprocess.SubprocessError as e:
        logger.error(f"Системная ошибка при запуске rac.exe: {e}")

    return []


def get_cluster_ids() -> List[str]:
    """
    Возвращает список UUID всех найденных кластеров 1С.

    Функция извлекает уникальные идентификаторы (UUID) из информации
    о кластерах, полученной через get_all_clusters(). Пустые значения
    исключаются из результата.

    Returns:
        List[str]: Список строк с UUID кластеров 1С

    Example:
        >>> cluster_ids = get_cluster_ids()
        >>> print(f"Найдено {len(cluster_ids)} кластеров")
        >>> for cid in cluster_ids:
        ...     print(f"- {cid}")

    Note:
        - Функция исключает кластеры с пустыми или None значениями UUID
        - Возвращает только действительные идентификаторы кластеров
        - Может вернуть пустой список, если кластеры не найдены
    """
    clusters = get_all_clusters()
    # Фильтрация для исключения пустых значений
    cluster_ids: List[str] = [
        str(c.get("cluster")) for c in clusters if c.get("cluster") is not None
    ]
    return cluster_ids


def get_default_cluster() -> Optional[Dict[str, Any]]:
    """
    Возвращает первый найденный кластер из списка доступных кластеров.

    Функция используется для получения "по умолчанию" кластера,
    когда требуется работать с одним кластером из всех доступных.
    Если кластеры не найдены, возвращает None.

    Returns:
        Optional[Dict[str, Any]]: Словарь с информацией о первом кластере
                                 или None, если кластеры не найдены

    Example:
        >>> default_cluster = get_default_cluster()
        >>> if default_cluster:
        ...     print(f"По умолчанию: {default_cluster['name']}")
        ... else:
        ...     print("Кластеры не найдены")

    Note:
        - Возвращает первый элемент из списка кластеров
        - Может вернуть None, если список кластеров пуст
        - Используется как fallback вариант при отсутствии явного выбора
    """
    clusters = get_all_clusters()
    return clusters[0] if clusters else None


def initialize_cluster_info():
    """
    Инициализирует глобальные данные о кластерах 1С.

    Функция получает информацию обо всех доступных кластерах,
    извлекает данные о первом кластере (идентификатор и имя)
    и возвращает их для дальнейшего использования в приложении.

    Returns:
        tuple: Кортеж из трех элементов:
            - all_clusters (List[Dict[str, Any]]): Список всех кластеров
            - c_id (str): Идентификатор первого кластера (или пустая строка)
            - c_name (str): Имя первого кластера (или пустая строка)

    Example:
        >>> clusters, cluster_id, cluster_name = initialize_cluster_info()
        >>> print(f"Всего кластеров: {len(clusters)}")
        >>> if cluster_id:
        ...     print(f"Первый кластер: {cluster_name} (ID: {cluster_id})")

    Note:
        - Используется для инициализации глобальных переменных в модуле
        - Возвращает пустые строки, если кластеры не найдены
        - Является вспомогательной функцией для инициализации модуля
    """
    all_clusters = get_all_clusters()
    _default = all_clusters[0] if all_clusters else None

    c_id = str(_default.get("cluster", "")) if _default else ""
    c_name = str(_default.get("name", "")) if _default else ""

    return all_clusters, c_id, c_name


# Инициализация глобальных переменных для экспорта в другие модули
# Эти переменные содержат информацию о доступных кластерах 1С и используются
# другими модулями приложения (например, main.py) для выполнения операций
all_available_clusters, cluster_id, cluster_name = initialize_cluster_info()

if __name__ == "__main__":
    # Тестовый запуск модуля
    logger.add(sys.stderr, level="DEBUG")

    print("\n--- Проверка доступности RAS ---")
    ras_status = check_ras_availability()
    print(f"Статус: {'OK' if ras_status['available'] else 'ОШИБКА'}")
    print(f"Сообщение: {ras_status['message']}")

    print("\n--- Отчет по кластерам 1С ---")
    ids = get_cluster_ids()
    if not ids:
        print("Кластеры не найдены.")
    else:
        for i, cid in enumerate(ids, 1):
            print(f"Кластер #{i}: ID = {cid}")
