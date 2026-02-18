"""
Модуль для анализа нагрузки информационных баз 1С:Предприятия.

Содержит логику анализа метрик нагрузки для отдельных информационных баз:
1. Количество сессий (всего и активных)
2. Количество активных фоновых заданий
3. Наличие блокировок
4. Объем трафика
5. Интенсивность вызовов

Модуль позволяет принимать обоснованные решения о разделении кластеров
при достижении пороговых значений нагрузки.
"""

import subprocess
import os
from typing import List, Dict, Any, Optional
from loguru import logger

from zbx_1c.core.config import settings
from zbx_1c.monitoring.session.collector import SessionCollector
from zbx_1c.monitoring.session.filters import filter_active_sessions
from zbx_1c.monitoring.jobs.reader import JobReader
from zbx_1c.utils.converters import parse_rac_output


def get_all_infobases(cluster_id: str, ras_address: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Получает список всех информационных баз в кластере.

    Функция использует rac.exe для получения информации обо всех
    информационных базах, зарегистрированных в кластере 1С.
    Это позволяет анализировать нагрузку по отдельным базам.

    Args:
        cluster_id (str): Идентификатор кластера 1С
        ras_address (Optional[str]): Адрес RAS-сервера в формате host:port.
                                   Если не указан, используется адрес из настроек.

    Returns:
        List[Dict[str, Any]]: Список словарей с информацией об информационных базах,
                             где каждый словарь содержит поля:
                             - infobase: идентификатор информационной базы
                             - name: имя базы
                             - descr: описание базы
                             - protection: уровень защиты
                             - ras_address: адрес RAS-сервера, с которого получена информация

    Example:
        >>> bases = get_all_infobases("a1b2c3d4-5678-90ab-cdef-1234567890ab")
        >>> for base in bases:
        ...     print(f"База: {base['name']} ({base['infobase']})")
    """
    if ras_address is None:
        ras_address = f"{settings.rac_host}:{settings.rac_port}"

    rac_path = str(settings.rac_path)
    command = [rac_path, "infobase", "summary", "list", f"--cluster={cluster_id}", ras_address]

    # Добавляем авторизацию, если параметры заданы в конфиге
    if settings.user_name:
        command.extend(["--cluster-user", settings.user_name])
    if settings.user_pass:
        command.extend(["--cluster-pwd", settings.user_pass])

    try:
        result = subprocess.run(command, capture_output=True, check=False, timeout=15)

        if result.returncode == 0:
            decoded_text = result.stdout.decode("cp866" if os.name == "nt" else "utf-8", errors="replace")
            infobases = parse_rac_output(decoded_text)
            # Добавляем информацию о RAS-сервере к каждой базе
            for infobase in infobases:
                infobase["ras_address"] = ras_address
            return infobases

        stderr_text = result.stderr.decode("cp866" if os.name == "nt" else "utf-8", errors="replace")
        logger.error(
            f"RAC ошибка получения infobases (код {result.returncode}) для {ras_address}: {stderr_text}"
        )

    except FileNotFoundError:
        logger.error(f"Файл не найден: {rac_path} для RAS {ras_address}. Проверьте настройки.")
    except subprocess.TimeoutExpired:
        logger.warning(f"Сервер RAS {ras_address} не ответил за 15 секунд.")
    except subprocess.SubprocessError as e:
        logger.error(f"Системная ошибка при запуске rac.exe для {ras_address}: {e}")

    return []


def analyze_infobase_load(
    cluster_id: str, infobase_name: str, ras_address: Optional[str] = None
) -> Dict[str, Any]:
    """
    Анализирует нагрузку информационной базы по различным метрикам.

    Функция собирает и анализирует метрики нагрузки для конкретной
    информационной базы, включая количество сессий, активность,
    блокировки и другие показатели производительности.

    Args:
        cluster_id (str): Идентификатор кластера 1С
        infobase_name (str): Имя информационной базы
        ras_address (Optional[str]): Адрес RAS-сервера в формате host:port.
                                   Если не указан, используется адрес из настроек.

    Returns:
        Dict[str, Any]: Словарь с метриками нагрузки базы, включающий:
                       - intensity_points: суммарная интенсивность вызовов
                       - sessions_total: общее количество сессий
                       - sessions_active: количество активных сессий
                       - bg_jobs_active: количество активных фоновых заданий
                       - locks_detected: количество сессий в ожидании блокировок
                       - traffic_mb: объем трафика за определенный период
                       - avg_call_duration: средняя длительность вызовов
                       - ras_address: адрес RAS-сервера, с которого получена информация

    Example:
        >>> load_metrics = analyze_infobase_load("cluster-id", "my-base")
        >>> print(f"Интенсивность: {load_metrics['intensity_points']}")
        >>> print(f"Активных сессий: {load_metrics['sessions_active']}")
    """
    if ras_address is None:
        ras_address = f"{settings.rac_host}:{settings.rac_port}"

    # Получаем все сессии для кластера
    session_collector = SessionCollector(settings)
    all_sessions_raw = session_collector.get_sessions(cluster_id)
    # Конвертируем в dict если нужно
    all_sessions: List[Dict[str, Any]] = []
    for s in all_sessions_raw:
        if hasattr(s, 'model_dump'):
            all_sessions.append(s.model_dump())  # type: ignore
        else:
            all_sessions.append(s)  # type: ignore

    # Фильтруем сессии для конкретной информационной базы
    infobase_sessions = [
        s
        for s in all_sessions
        if s.get("infobase", "").lower() == infobase_name.lower()
        or s.get("name", "").lower() == infobase_name.lower()
    ]

    # Подсчитываем метрики
    total_sessions = len(infobase_sessions)
    active_sessions = len(filter_active_sessions(infobase_sessions, threshold_minutes=5))

    # Получаем фоновые задания для кластера
    job_reader = JobReader(settings)
    bg_jobs = job_reader.get_jobs(cluster_id)
    active_bg_jobs = [j for j in bg_jobs if j.get("status") == "running"]

    # Определяем количество сессий в ожидании блокировок
    locked_sessions = [s for s in infobase_sessions if s.get("wait-info", "").startswith("Lock")]

    # Пример расчета интенсивности (в реальности это может быть более сложным)
    intensity_points = sum(
        int(s.get("calls-last-5min", 0)) for s in infobase_sessions if s.get("calls-last-5min")
    )

    # Пример оценки трафика (в реальности это может быть более сложным)
    traffic_mb = sum(
        int(s.get("bytes-last-5min", 0)) for s in infobase_sessions if s.get("bytes-last-5min")
    ) / (1024 * 1024)

    return {
        "intensity_points": intensity_points,
        "sessions_total": total_sessions,
        "sessions_active": active_sessions,
        "bg_jobs_active": len(active_bg_jobs),
        "locks_detected": len(locked_sessions),
        "traffic_mb": round(traffic_mb, 2),
        "avg_call_duration": 0,  # В реальности это потребует дополнительных данных
        "ras_address": ras_address,
        "infobase_name": infobase_name,
        "cluster_id": cluster_id,
    }


def get_infobase_session_limits(cluster_id: str, ras_address: Optional[str] = None) -> Dict[str, int]:
    """
    Получение лимитов сессий (max-connections) для всех информационных баз кластера
    Лимит max-connections устанавливается на уровне Информационной Базы в консоли администрирования

    Args:
        cluster_id (str): Идентификатор кластера 1С
        ras_address (Optional[str]): Адрес RAS-сервера в формате host:port.
                                   Если не указан, используется адрес из настроек.

    Returns:
        Dict[str, int]: Словарь {infobase_id: max_connections}
                       max_connections = 0 означает отсутствие лимита (без ограничений)
    """
    if ras_address is None:
        ras_address = f"{settings.rac_host}:{settings.rac_port}"

    infobases = get_all_infobases(cluster_id, ras_address)
    limits = {}

    for infobase in infobases:
        infobase_id = infobase.get("infobase") or infobase.get("id")
        if not infobase_id:
            continue

        # Лимит сессий для ИБ - это поле max-connections
        # 0 = без ограничений
        limit = int(infobase.get("max-connections", 0) or 0)
        limits[infobase_id] = limit
        logger.debug(
            f"Infobase {infobase.get('name', infobase_id)} max-connections: {limit}"
        )

    return limits


def get_total_infobase_session_limit(
    cluster_id: str, ras_address: Optional[str] = None
) -> int:
    """
    Получение общего лимита сессий для кластера (сумма лимитов всех ИБ)
    Лимит max-connections устанавливается на уровне Информационной Базы

    Args:
        cluster_id (str): Идентификатор кластера 1С
        ras_address (Optional[str]): Адрес RAS-сервера в формате host:port.
                                   Если не указан, используется адрес из настроек.

    Returns:
        int: Общий лимит сессий (0 если не установлен ни для одной ИБ)
    """
    limits = get_infobase_session_limits(cluster_id, ras_address)
    total = sum(limits.values())

    logger.debug(f"Total infobase session limit for cluster {cluster_id}: {total}")
    return total


def get_infobase_recommendations(load_metrics: Dict[str, Any]) -> List[str]:
    """
    Формирует рекомендации по оптимизации на основе метрик нагрузки информационной базы.

    Args:
        load_metrics (Dict[str, Any]): Метрики нагрузки, полученные из analyze_infobase_load

    Returns:
        List[str]: Список рекомендаций по оптимизации
    """
    recommendations = []

    intensity_points = load_metrics.get("intensity_points", 0)
    sessions_active = load_metrics.get("sessions_active", 0)
    bg_jobs_active = load_metrics.get("bg_jobs_active", 0)
    locks_detected = load_metrics.get("locks_detected", 0)

    # Рекомендации на основе интенсивности
    if intensity_points > 200:
        recommendations.append(
            "КРИТИЧНО: Высокая интенсивность вызовов (>200). Рассмотрите выделение отдельного кластера"
        )
    elif intensity_points > 70:
        recommendations.append(
            "ВЫСОКО: Высокая интенсивность вызовов. Рассмотрите разделение в пиковые периоды"
        )

    # Рекомендации на основе активных сессий
    if sessions_active > 50:
        recommendations.append(
            "ВНИМАНИЕ: Большое количество активных сессий (>50). Проверьте распределение нагрузки"
        )

    # Рекомендации на основе фоновых заданий
    if bg_jobs_active > 15:
        recommendations.append(
            "ВНИМАНИЕ: Большое количество активных фоновых заданий (>15). Проверьте планировщик заданий"
        )

    # Рекомендации на основе блокировок
    if locks_detected > 0:
        recommendations.append(
            "ВАЖНО: Обнаружены сессии в ожидании блокировок. Проверьте технологический журнал"
        )

    # Если нет рекомендаций, значит нагрузка в норме
    if not recommendations:
        recommendations.append("ИНФОРМАЦИЯ: Нагрузка в пределах нормы")

    return recommendations


