"""
Валидаторы данных
"""

import re
from typing import Any
from uuid import UUID


def validate_cluster_id(cluster_id: str) -> bool:
    """
    Валидация ID кластера

    Args:
        cluster_id: ID кластера

    Returns:
        True если валидный, иначе False
    """
    try:
        UUID(cluster_id)
        return True
    except ValueError:
        return False


def validate_hostname(hostname: str) -> bool:
    """
    Валидация имени хоста

    Args:
        hostname: Имя хоста

    Returns:
        True если валидный, иначе False
    """
    if len(hostname) > 255:
        return False

    if hostname[-1] == ".":
        hostname = hostname[:-1]

    allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))


def validate_port(port: Any) -> bool:
    """
    Валидация порта

    Args:
        port: Номер порта

    Returns:
        True если валидный, иначе False
    """
    try:
        port = int(port)
        return 1 <= port <= 65535
    except (ValueError, TypeError):
        return False


def validate_rac_path(path: str) -> bool:
    """
    Валидация пути к rac

    Args:
        path: Путь к исполняемому файлу

    Returns:
        True если валидный, иначе False
    """
    from pathlib import Path
    import os

    path_obj = Path(path)

    if not path_obj.exists():
        return False

    # Проверка прав на выполнение (для Unix)
    if os.name != "nt" and not os.access(path_obj, os.X_OK):
        return False

    return True


def sanitize_command_arg(arg: str) -> str:
    """
    Санитизация аргумента команды

    Args:
        arg: Аргумент для санитизации

    Returns:
        Безопасный аргумент
    """
    # Удаляем потенциально опасные символы
    dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\\", '"', "'"]

    for char in dangerous_chars:
        arg = arg.replace(char, "")

    return arg.strip()
