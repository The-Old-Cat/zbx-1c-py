"""
Модуль для поиска информационных баз 1С:Предприятия на основе конфигурации.

Обеспечивает:
1. Получение списка информационных баз из кластера 1С.
2. Фильтрацию баз по различным критериям.
3. Проверку доступности баз.
4. Возврат информации о найденных базах.
"""

import subprocess
import os
from typing import List, Dict, Any, Optional
from loguru import logger

from zbx_1c.core.config import settings
from zbx_1c.utils.converters import parse_rac_output


def get_all_infobases_from_config(ras_address: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Получает список всех информационных баз в кластерах, указанных в конфигурации.

    Args:
        ras_address (Optional[str]): Адрес RAS-сервера в формате host:port.
                                   Если не указан, используется адрес из настроек.

    Returns:
        List[Dict[str, Any]]: Список словарей с информацией об информационных базах
    """
    if ras_address is None:
        ras_address = f"{settings.rac_host}:{settings.rac_port}"

    all_infobases = []

    # Получаем список кластеров
    from zbx_1c.monitoring.cluster.manager import ClusterManager
    manager = ClusterManager(settings)
    clusters = manager.discover_clusters()
    cluster_ids = [str(c.get("id", "")) for c in clusters]

    if not cluster_ids:
        logger.warning(f"Не удалось получить список кластеров для RAS: {ras_address}")
        return []

    for cluster_id in cluster_ids:
        logger.info(f"Получение информационных баз для кластера: {cluster_id}")
        infobases = get_infobases_for_cluster(cluster_id, ras_address)
        all_infobases.extend(infobases)

    return all_infobases


def get_infobases_for_cluster(
    cluster_id: str, ras_address: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Получает список информационных баз для конкретного кластера.

    Args:
        cluster_id (str): Идентификатор кластера 1С
        ras_address (Optional[str]): Адрес RAS-сервера в формате host:port.
                                   Если не указан, используется адрес из настроек.

    Returns:
        List[Dict[str, Any]]: Список словарей с информацией об информационных базах
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
            # Добавляем информацию о кластере и RAS-сервере к каждой базе
            for infobase in infobases:
                infobase["cluster_id"] = cluster_id
                infobase["ras_address"] = ras_address
            return infobases

        stderr_text = result.stderr.decode("cp866" if os.name == "nt" else "utf-8", errors="replace")
        logger.error(
            f"RAC ошибка получения infobases (код {result.returncode}) для {ras_address}, кластер {cluster_id}: {stderr_text}"
        )

    except FileNotFoundError:
        logger.error(f"Файл не найден: {rac_path} для RAS {ras_address}. Проверьте настройки.")
    except subprocess.TimeoutExpired:
        logger.warning(
            f"Сервер RAS {ras_address} не ответил за 15 секунд для кластера {cluster_id}."
        )
    except subprocess.SubprocessError as e:
        logger.error(
            f"Системная ошибка при запуске rac.exe для {ras_address}, кластер {cluster_id}: {e}"
        )

    return []


def filter_infobases_by_criteria(
    infobases: List[Dict[str, Any]],
    name_pattern: Optional[str] = None,
    exclude_templates: bool = True,
    min_connections: Optional[int] = None,
    max_connections: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Фильтрует список информационных баз по заданным критериям.

    Args:
        infobases (List[Dict[str, Any]]): Список информационных баз
        name_pattern (Optional[str]): Паттерн для поиска в названии базы
        exclude_templates (bool): Исключать ли шаблоны конфигуратора
        min_connections (Optional[int]): Минимальное количество подключений
        max_connections (Optional[int]): Максимальное количество подключений

    Returns:
        List[Dict[str, Any]]: Отфильтрованный список информационных баз
    """
    filtered = infobases

    # Фильтрация по имени
    if name_pattern:
        name_lower = name_pattern.lower()
        filtered = [ib for ib in filtered if name_lower in ib.get("name", "").lower()]

    # Исключение шаблонов
    if exclude_templates:
        filtered = [
            ib
            for ib in filtered
            if not ib.get("name", "").lower().startswith("шаблон")
            and not ib.get("name", "").lower().startswith("template")
        ]

    # Фильтрация по количеству подключений
    if min_connections is not None:
        filtered = [ib for ib in filtered if int(ib.get("connections", 0)) >= min_connections]

    if max_connections is not None:
        filtered = [ib for ib in filtered if int(ib.get("connections", 0)) <= max_connections]

    return filtered


def search_infobases_by_name(
    name_pattern: str, ras_address: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Ищет информационные базы по части имени.

    Args:
        name_pattern (str): Часть имени для поиска
        ras_address (Optional[str]): Адрес RAS-сервера в формате host:port.
                                   Если не указан, используется адрес из настроек.

    Returns:
        List[Dict[str, Any]]: Список найденных информационных баз
    """
    all_infobases = get_all_infobases_from_config(ras_address)
    return filter_infobases_by_criteria(all_infobases, name_pattern=name_pattern)


def get_infobase_details(
    infobase_id: str, cluster_id: str, ras_address: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Получает детальную информацию об информационной базе.

    Args:
        infobase_id (str): Идентификатор информационной базы
        cluster_id (str): Идентификатор кластера 1С
        ras_address (Optional[str]): Адрес RAS-сервера в формате host:port.
                                   Если не указан, используется адрес из настроек.

    Returns:
        Optional[Dict[str, Any]]: Словарь с детальной информацией об информационной базе
    """
    if ras_address is None:
        ras_address = f"{settings.rac_host}:{settings.rac_port}"

    rac_path = str(settings.rac_path)
    command = [rac_path, "infobase", "list", "--cluster", cluster_id, ras_address]

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

            # Находим нужную информационную базу
            for infobase in infobases:
                if infobase.get("infobase") == infobase_id:
                    infobase["cluster_id"] = cluster_id
                    infobase["ras_address"] = ras_address
                    return infobase

            logger.warning(f"Информационная база {infobase_id} не найдена в кластере {cluster_id}")
            return None

        stderr_text = result.stderr.decode("cp866" if os.name == "nt" else "utf-8", errors="replace")
        logger.error(
            f"RAC ошибка получения деталей infobase (код {result.returncode}) для {ras_address}, кластер {cluster_id}: {stderr_text}"
        )

    except FileNotFoundError:
        logger.error(f"Файл не найден: {rac_path} для RAS {ras_address}. Проверьте настройки.")
    except subprocess.TimeoutExpired:
        logger.warning(
            f"Сервер RAS {ras_address} не ответил за 15 секунд для кластера {cluster_id}."
        )
    except subprocess.SubprocessError as e:
        logger.error(
            f"Системная ошибка при запуске rac.exe для {ras_address}, кластер {cluster_id}: {e}"
        )

    return None


def get_infobase_statistics(infobases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Возвращает статистику по найденным информационным базам.

    Args:
        infobases (List[Dict[str, Any]]): Список информационных баз

    Returns:
        Dict[str, Any]: Словарь со статистикой
    """
    total_bases = len(infobases)
    total_connections = sum(int(ib.get("connections", 0)) for ib in infobases)
    clusters = set(ib.get("cluster_id", "") for ib in infobases if ib.get("cluster_id"))

    # Группировка баз по кластерам
    bases_by_cluster = {}
    for ib in infobases:
        cluster_id = ib.get("cluster_id", "unknown")
        if cluster_id not in bases_by_cluster:
            bases_by_cluster[cluster_id] = []
        bases_by_cluster[cluster_id].append(ib)

    stats = {
        "total_bases": total_bases,
        "total_connections": total_connections,
        "total_clusters": len(clusters),
        "clusters": list(clusters),
        "bases_by_cluster": bases_by_cluster,
        "average_connections_per_base": total_connections / total_bases if total_bases > 0 else 0,
    }

    return stats


def get_infobase_sessions(
    infobase_id: str, cluster_id: str, ras_address: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Получает список сессий для конкретной информационной базы.

    Args:
        infobase_id (str): Идентификатор информационной базы
        cluster_id (str): Идентификатор кластера 1С
        ras_address (Optional[str]): Адрес RAS-сервера в формате host:port.
                                   Если не указан, используется адрес из настроек.

    Returns:
        List[Dict[str, Any]]: Список сессий для указанной информационной базы
    """
    if ras_address is None:
        ras_address = f"{settings.rac_host}:{settings.rac_port}"

    rac_path = str(settings.rac_path)
    command = [rac_path, "session", "list", "--cluster", cluster_id, ras_address]

    # Добавляем авторизацию, если параметры заданы в конфиге
    if settings.user_name:
        command.extend(["--cluster-user", settings.user_name])
    if settings.user_pass:
        command.extend(["--cluster-pwd", settings.user_pass])

    try:
        result = subprocess.run(command, capture_output=True, check=False, timeout=15)

        if result.returncode == 0:
            decoded_text = result.stdout.decode("cp866" if os.name == "nt" else "utf-8", errors="replace")
            all_sessions = parse_rac_output(decoded_text)

            # Фильтруем сессии для конкретной информационной базы
            infobase_sessions = [
                session for session in all_sessions if session.get("infobase") == infobase_id
            ]

            return infobase_sessions

        stderr_text = result.stderr.decode("cp866" if os.name == "nt" else "utf-8", errors="replace")
        logger.error(
            f"RAC ошибка получения сессий (код {result.returncode}) для {ras_address}, кластер {cluster_id}: {stderr_text}"
        )

    except FileNotFoundError:
        logger.error(f"Файл не найден: {rac_path} для RAS {ras_address}. Проверьте настройки.")
    except subprocess.TimeoutExpired:
        logger.warning(
            f"Сервер RAS {ras_address} не ответил за 15 секунд для кластера {cluster_id}."
        )
    except subprocess.SubprocessError as e:
        logger.error(
            f"Системная ошибка при запуске rac.exe для {ras_address}, кластер {cluster_id}: {e}"
        )

    return []


def get_infobase_connection_stats(
    infobase_id: str, cluster_id: str, ras_address: Optional[str] = None
) -> Dict[str, Any]:
    """
    Получает статистику подключений для конкретной информационной базы.

    Args:
        infobase_id (str): Идентификатор информационной базы
        cluster_id (str): Идентификатор кластера 1С
        ras_address (Optional[str]): Адрес RAS-сервера в формате host:port.
                                   Если не указан, используется адрес из настроек.

    Returns:
        Dict[str, Any]: Словарь со статистикой подключений
    """
    sessions = get_infobase_sessions(infobase_id, cluster_id, ras_address)

    total_sessions = len(sessions)

    # Подсчет активных сессий (не в спящем режиме)
    active_sessions = [s for s in sessions if s.get("hibernate") != "yes"]
    active_count = len(active_sessions)

    # Подсчет сессий по типам приложений
    app_types = {}
    for session in sessions:
        app_id = session.get("app-id", "Unknown")
        app_types[app_id] = app_types.get(app_id, 0) + 1

    # Подсчет сессий по пользователям
    users = {}
    for session in sessions:
        user_name = session.get("user-name", "Unknown")
        users[user_name] = users.get(user_name, 0) + 1

    return {
        "infobase_id": infobase_id,
        "cluster_id": cluster_id,
        "total_sessions": total_sessions,
        "active_sessions": active_count,
        "inactive_sessions": total_sessions - active_count,
        "app_types": app_types,
        "unique_users": len(users),
        "users_list": list(users.keys()),
        "user_sessions": users,
    }


def get_enhanced_infobase_list_with_connections(
    cluster_id: str, ras_address: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Получает список информационных баз с дополнительной информацией о подключениях.

    Args:
        cluster_id (str): Идентификатор кластера 1С
        ras_address (Optional[str]): Адрес RAS-сервера в формате host:port.
                                   Если не указан, используется адрес из настроек.

    Returns:
        List[Dict[str, Any]]: Список информационных баз с информацией о подключениях
    """
    infobases = get_infobases_for_cluster(cluster_id, ras_address)

    enhanced_list = []
    for infobase in infobases:
        infobase_id = infobase.get("infobase")
        if infobase_id:
            connection_stats = get_infobase_connection_stats(infobase_id, cluster_id, ras_address)
            # Добавляем информацию о подключениях к информации об инфобазе
            enhanced_infobase = {**infobase, **connection_stats}
            enhanced_list.append(enhanced_infobase)

    return enhanced_list


def get_detailed_infobase_status(
    infobase_id: str, cluster_id: str, ras_address: Optional[str] = None
) -> Dict[str, Any]:
    """
    Получает детальный статус информационной базы, включая информацию о сессиях и доступности.

    Args:
        infobase_id (str): Идентификатор информационной базы
        cluster_id (str): Идентификатор кластера 1С
        ras_address (Optional[str]): Адрес RAS-сервера в формате host:port.
                                   Если не указан, используется адрес из настроек.

    Returns:
        Dict[str, Any]: Детальная информация о статусе информационной базы
    """
    # Получаем информацию о сессиях
    connection_stats = get_infobase_connection_stats(infobase_id, cluster_id, ras_address)

    # Получаем информацию о самой информационной базе
    infobase_info = get_infobase_details(infobase_id, cluster_id, ras_address)

    # Сводим всю информацию вместе
    status_info = {
        "infobase_id": infobase_id,
        "cluster_id": cluster_id,
        "infobase_info": infobase_info or {},
        "connection_stats": connection_stats,
        "has_active_sessions": connection_stats["active_sessions"] > 0,
        "has_any_sessions": connection_stats["total_sessions"] > 0,
        "is_apparently_active": connection_stats["total_sessions"] > 0
        or connection_stats["active_sessions"] > 0,
    }

    return status_info


if __name__ == "__main__":
    # Тестирование функций модуля
    import sys
    from pathlib import Path

    # Добавляем путь к родительскому каталогу в sys.path для импорта
    sys.path.insert(0, str(Path(__file__).parent.parent))

    print("=== Тестирование поиска информационных баз 1С ===")

    # Получаем все информационные базы
    print(f"\nПолучение всех информационных баз для RAS: {settings.rac_host}:{settings.rac_port}")
    all_infobases = get_all_infobases_from_config()

    if all_infobases:
        print(f"Найдено {len(all_infobases)} информационных баз:")

        # Вариант вывода с ID (оригинальный)
        print("Вывод с ID:")
        for idx, ib in enumerate(all_infobases, 1):
            name = ib.get("name", "N/A")
            infobase_id = ib.get("infobase", "N/A")
            cluster_id = ib.get("cluster_id", "N/A")
            connections = ib.get("connections", "N/A")
            print(
                f"{idx}. {name} (ID: {infobase_id}, Кластер: {cluster_id}, Подключений: {connections})"
            )
        
        print("\n" + "-"*50)
        print("Вывод только имен (без ID):")
        # Вариант вывода только с именами (новый)
        for idx, ib in enumerate(all_infobases, 1):
            name = ib.get("name", "N/A")
            print(f"{idx}. {name}")

        # Выводим статистику
        stats = get_infobase_statistics(all_infobases)
        print("\nСтатистика:")
        print(f"- Всего баз: {stats['total_bases']}")
        print(f"- Всего подключений: {stats['total_connections']}")
        print(
            f"- Среднее количество подключений на базу: {stats['average_connections_per_base']:.2f}"
        )
        print(f"- Количество кластеров: {stats['total_clusters']}")
        print(f"- Кластеры: {', '.join(stats['clusters'])}")

        # Пример фильтрации
        print("\nПример фильтрации баз с количеством подключений > 0:")
        active_bases = filter_infobases_by_criteria(all_infobases, min_connections=1)
        print(f"Найдено {len(active_bases)} активных баз:")
        for ib in active_bases:
            name = ib.get("name", "N/A")
            connections = ib.get("connections", "N/A")
            print(f"- {name} (Подключений: {connections})")
    else:
        print("Не удалось получить список информационных баз")

        # Попробуем получить список кластеров
        print("\nПроверка доступных кластеров...")
        from zbx_1c.monitoring.cluster.manager import ClusterManager
        manager = ClusterManager(settings)
        clusters = manager.discover_clusters()
        if clusters:
            print(f"Найдено {len(clusters)} кластеров:")
            for cluster in clusters:
                cluster_name = cluster.get("name", "")
                cluster_id = str(cluster.get("id", ""))
                print(f"- {cluster_name} (ID: {cluster_id})")
        else:
            print("Не удалось получить список кластеров")


def get_infobases_without_uid(ras_address: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Получает список информационных баз без уникальных идентификаторов (UID).
    Функция возвращает только те базы, у которых отсутствует или пустое значение поля 'infobase'.

    Args:
        ras_address (Optional[str]): Адрес RAS-сервера в формате host:port.
                                   Если не указан, используется адрес из настроек.

    Returns:
        List[Dict[str, Any]]: Список словарей с информацией об информационных базах без UID
    """
    if ras_address is None:
        ras_address = f"{settings.rac_host}:{settings.rac_port}"

    all_infobases = get_all_infobases_from_config(ras_address)

    # Фильтруем базы, у которых нет UID (пустое или None значение поля 'infobase')
    infobases_without_uid = [
        ib for ib in all_infobases if not ib.get("infobase") or ib.get("infobase") == ""
    ]

    return infobases_without_uid


def get_infobases_with_name_only(ras_address: Optional[str] = None) -> List[str]:
    """
    Получает список имен информационных баз без уникальных идентификаторов (UID).
    Функция возвращает только имена тех баз, у которых отсутствует или пустое значение поля 'infobase'.

    Args:
        ras_address (Optional[str]): Адрес RAS-сервера в формате host:port.
                                   Если не указан, используется адрес из настроек.

    Returns:
        List[str]: Список имен информационных баз без UID
    """
    infobases_without_uid = get_infobases_without_uid(ras_address)
    return [ib.get("name", "N/A") for ib in infobases_without_uid]


def get_all_infobases_names_only(ras_address: Optional[str] = None) -> List[str]:
    """
    Получает список имен всех информационных баз без уникальных идентификаторов (ID).
    Функция возвращает только имена всех баз, независимо от наличия или отсутствия UID.

    Args:
        ras_address (Optional[str]): Адрес RAS-сервера в формате host:port.
                                   Если не указан, используется адрес из настроек.

    Returns:
        List[str]: Список имен всех информационных баз
    """
    if ras_address is None:
        ras_address = f"{settings.rac_host}:{settings.rac_port}"

    all_infobases = get_all_infobases_from_config(ras_address)

    # Возвращаем только имена всех баз
    infobases_names = [ib.get("name", "N/A") for ib in all_infobases]

    return infobases_names


def print_infobases_names_only(ras_address: Optional[str] = None) -> None:
    """
    Выводит список имен всех информационных баз без уникальных идентификаторов (ID).
    Функция печатает только имена всех баз, независимо от наличия или отсутствия UID.

    Args:
        ras_address (Optional[str]): Адрес RAS-сервера в формате host:port.
                                   Если не указан, используется адрес из настроек.
    """
    infobases_names = get_all_infobases_names_only(ras_address)
    
    print("Список информационных баз (только имена):")
    for i, name in enumerate(infobases_names, 1):
        print(f"{i}. {name}")


def print_simple_infobases_list(ras_address: Optional[str] = None) -> None:
    """
    Выводит простой список информационных баз только с именами, без ID.
    Функция печатает только имена всех баз в простом формате.

    Args:
        ras_address (Optional[str]): Адрес RAS-сервера в формате host:port.
                                   Если не указан, используется адрес из настроек.
    """
    if ras_address is None:
        ras_address = f"{settings.rac_host}:{settings.rac_port}"

    all_infobases = get_all_infobases_from_config(ras_address)
    
    print("Список информационных баз (только имена):")
    for i, ib in enumerate(all_infobases, 1):
        name = ib.get('name', 'N/A')
        print(f"{i}. {name}")


def generate_zabbix_userparameters() -> str:
    """
    Генерирует кроссплатформенные UserParameter для Zabbix агента.
    
    Returns:
        str: Строка с UserParameter для Zabbix агента
    """
    import platform
    import sys
    from pathlib import Path
    
    # Определяем путь к интерпретатору Python
    python_executable = sys.executable
    
    # Определяем путь к проекту
    project_root = Path(__file__).parent.parent.parent.resolve()
    main_script_path = project_root / "src" / "api" / "main.py"
    
    # Определяем правильный формат пути в зависимости от ОС для Zabbix
    os_name = platform.system().lower()
    if os_name == "windows":
        # Для Windows в Zabbix конфигурации нужно удваивать обратные слэши
        python_path = str(Path(python_executable)).replace('\\', '\\\\')
        script_path = str(Path(main_script_path)).replace('\\', '\\\\')
    else:
        # Для Unix-подобных систем используем обычные пути
        python_path = str(Path(python_executable))
        script_path = str(Path(main_script_path))
    
    # Генерируем UserParameter
    userparams = f"""# Discovery: без параметров
UserParameter=zbx1cpy.clusters.discovery, "{python_path}" "{script_path}" --discovery

# Metrics: с параметром кластера ($1)
UserParameter=zbx1cpy.metrics[*], "{python_path}" "{script_path}" --cluster-id $1

# Тестовый параметр
UserParameter=test.echo[*], "{python_path}" -c "import sys; print(sys.executable)"
"""
    return userparams


def print_zabbix_userparameters() -> None:
    """
    Выводит сгенерированные кроссплатформенные UserParameter для Zabbix агента.
    """
    print("Кроссплатформенные UserParameter для Zabbix агента:")
    print(generate_zabbix_userparameters())
