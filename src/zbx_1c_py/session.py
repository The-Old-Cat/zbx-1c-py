"""
Модуль для управления сессиями 1С:Предприятия через утилиту rac.exe.

Обеспечивает:
1. Формирование команд для взаимодействия с RAS.
2. Безопасное выполнение внешних процессов с обработкой специфических исключений.
3. Фильтрацию и парсинг полученных данных о сессиях.
"""

import subprocess
from typing import List, Dict, Any
from loguru import logger

try:
    from .config import settings
    from .clusters import cluster_id
    from .utils.helpers import parse_rac_output, decode_output, universal_filter
    from .session_active import filter_active_sessions
except ImportError:
    # Fallback для случая, когда файл запускается напрямую
    from config import settings
    from clusters import cluster_id
    from utils.helpers import parse_rac_output, decode_output, universal_filter
    from session_active import filter_active_sessions


def get_session_command(cluster_uuid: str) -> List[str]:
    """
    Формирует список аргументов командной строки для вызова rac.exe.

    Args:
        cluster_uuid (str): Идентификатор кластера 1С.

    Returns:
        List[str]: Список строк для запуска через subprocess.run.
    """
    rac_path = settings.rac_path
    ras_address = f"{settings.rac_host}:{settings.rac_port}"

    # Базовая структура команды
    command = [rac_path, ras_address, "session", "list", "--cluster", cluster_uuid]

    # Добавляем авторизацию, если параметры заданы в конфиге
    if settings.user_name:
        command.extend(["--cluster-user", settings.user_name])
    if settings.user_pass:
        command.extend(["--cluster-pwd", settings.user_pass])

    return command


def fetch_raw_sessions(cluster_uuid: str) -> List[Dict[str, Any]]:
    """
    Выполняет запрос к RAS и возвращает список сессий.

    Вместо перехвата общего Exception, обрабатываются конкретные сценарии:
    - FileNotFoundError: путь к rac.exe указан неверно.
    - subprocess.TimeoutExpired: служба RAS не ответила вовремя.
    - subprocess.SubprocessError: внутренние ошибки подсистемы процессов.
    """
    if not cluster_uuid:
        logger.error("Запрос отклонен: отсутствует cluster_id")
        return []

    cmd = get_session_command(cluster_uuid)

    try:
        # Ограничиваем время выполнения, чтобы не блокировать основной поток
        result = subprocess.run(cmd, capture_output=True, check=False, text=False, timeout=20)

        if result.returncode == 0:
            stdout_text = decode_output(result.stdout)
            return parse_rac_output(stdout_text)

        # Логируем специфическую ошибку от самой утилиты rac.exe
        stderr_text = decode_output(result.stderr)
        logger.error(f"RAC вернул ошибку (код {result.returncode}): {stderr_text}")

    except FileNotFoundError:
        logger.error(
            f"Файл rac.exe не найден по пути: {settings.rac_path}. Проверьте PATH или конфиг."
        )
    except subprocess.TimeoutExpired:
        logger.warning(f"Превышено время ожидания (20с) при запросе к {settings.rac_host}")
    except subprocess.SubprocessError as e:
        logger.error(f"Системная ошибка при запуске процесса: {str(e)}")
    # Exception не используется согласно правилу W0718

    return []


def get_active_sessions_report(only_active: bool = True) -> List[Dict[str, Any]]:
    """
    Получает список сессий и применяет фильтры активности и структуры.

    Args:
        only_active (bool): Флаг включения умной фильтрации (трафик, вызовы, hibernate).

    Returns:
        List[Dict[str, Any]]: Список словарей с данными сессий.
    """
    # Шаг 1: Получение "сырых" данных
    raw_sessions = fetch_raw_sessions(cluster_id)
    if not raw_sessions:
        return []

    # Шаг 2: Бизнес-фильтрация (живые пользователи)
    if only_active:
        # Используем логику из session_active.py
        processed_data = filter_active_sessions(raw_sessions, threshold_minutes=10)
    else:
        processed_data = raw_sessions

    # Шаг 3: Форматирование вывода (оставляем только нужные колонки)
    final_report = universal_filter(
        processed_data, ["session-id", "user-name", "app-id", "last-active-at"]
    )

    logger.info(f"Сформирован отчет: {len(final_report)} сессий.")
    return final_report


if __name__ == "__main__":
    # Локальное тестирование
    print("Запуск мониторинга сессий...")
    for session in get_active_sessions_report(only_active=True):
        user = session.get("user-name", "Unknown")
        app = session.get("app-id", "N/A")
        print(f"-> {user} работает в {app}")
