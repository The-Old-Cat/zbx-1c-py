"""
Утилиты для парсинга и конвертации данных RAC.
"""

import json
from typing import Any, Dict, List, Optional


def decode_output(data: bytes) -> str:
    """
    Декодирование вывода команды rac с учетом кодировки.

    Args:
        data: Байты для декодирования.

    Returns:
        Декодированная строка.
    """
    # Пробуем UTF-8, затем CP1251 (для Windows/Russian)
    for encoding in ["utf-8", "cp1251", "latin-1"]:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue

    # Если ничего не подошло, декодируем с заменой
    return data.decode("utf-8", errors="replace")


def parse_rac_output(output: str) -> List[Dict[str, Any]]:
    """
    Парсинг вывода команды rac.

    Формат вывода rac:
        cluster: <uuid>
        name: <name>
        host: <host>

    Args:
        output: Вывод команды rac.

    Returns:
        Список словарей с данными.
    """
    result = []
    current_item: Dict[str, Any] = {}

    for line in output.split("\n"):
        line = line.strip()
        if not line:
            if current_item:
                result.append(current_item)
                current_item = {}
            continue

        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            # Преобразуем значения
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            elif value.isdigit():
                value = int(value)

            current_item[key] = value

    # Добавляем последний элемент
    if current_item:
        result.append(current_item)

    return result


def format_lld_data(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Форматирование данных для Zabbix LLD (Low Level Discovery).

    Args:
        data: Список обнаруженных элементов.

    Returns:
        Данные в формате Zabbix LLD.
    """
    return {
        "data": data,
    }


def safe_json_output(data: Any, indent: int = 2) -> str:
    """
    Безопасный вывод JSON с правильной кодировкой.

    Args:
        data: Данные для вывода.
        indent: Отступ для форматирования.

    Returns:
        JSON строка.
    """
    return json.dumps(data, ensure_ascii=False, indent=indent, default=str)
