"""
Конвертеры для парсинга вывода RAC
Точно так же как в run_direct.py
"""

import sys
from typing import Dict, Any, List


def get_console_encoding() -> str:
    """
    Получить кодировку консоли для текущей ОС.

    Returns:
        str: Название кодировки
    """
    if sys.platform == "win32":
        # Windows использует CP866 для русской локали
        return "cp866"
    else:
        # Linux/macOS используют UTF-8
        return "utf-8"


def encode_for_console(text: str) -> str:
    """
    Кодировать текст в кодировку консоли текущей ОС.

    Args:
        text: Текст для кодирования (UTF-8)

    Returns:
        str: Текст в кодировке консоли
    """
    encoding = get_console_encoding()
    if encoding == "cp866":
        # Для Windows: кодируем русские символы в CP866
        # Это нужно для корректного отображения в консоли и Zabbix Agent
        result = []
        for char in text:
            try:
                # Пробуем закодировать символ в CP866
                char.encode("cp866")
                result.append(char)
            except UnicodeEncodeError:
                # Символ нет в CP866, оставляем как есть (это будет \uXXXX)
                result.append(char)
        return "".join(result)
    return text


def decode_from_console(text_bytes: bytes) -> str:
    """
    Декодировать байты из кодировки консоли текущей ОС.

    Args:
        text_bytes: Байты для декодирования

    Returns:
        str: Декодированный текст в UTF-8
    """
    encoding = get_console_encoding()
    return text_bytes.decode(encoding, errors="replace")


def decode_output(raw_data: bytes) -> str:
    """
    Декодирует бинарные данные от rac.exe с учетом специфики 1С на Windows.

    1С на Windows использует кодировку консоли CP866 для корректного
    отображения кириллицы. Функция сначала пробует декодировать данные
    в CP866, а при неудаче использует UTF-8 с игнорированием ошибок.

    Args:
        raw_data (bytes): Бинарные данные, полученные от rac.exe

    Returns:
        str: Декодированная строка с текстовым содержимым

    Note:
        - Основная кодировка для 1С на Windows - CP866
        - При неудаче используется UTF-8 с игнорированием ошибок
        - Пустые данные возвращаются как пустая строка
        - Результат автоматически очищается от лишних пробелов
        - Кавычки удаляются из результата
    """
    if not raw_data:
        return ""

    # Для Windows сначала пробуем CP866 (основная кодировка 1С)
    if sys.platform == "win32":
        try:
            decoded_str = raw_data.decode("cp866").strip()
            return decoded_str.strip('"')
        except (UnicodeDecodeError, AttributeError):
            pass
        # Если CP866 не сработал, пробуем UTF-8
        try:
            decoded_str = raw_data.decode("utf-8").strip()
            return decoded_str.strip('"')
        except UnicodeDecodeError:
            pass
        # Если оба варианта не сработали, используем UTF-8 с игнорированием ошибок
        decoded_str = raw_data.decode("utf-8", errors="ignore").strip()
        return decoded_str.strip('"')
    else:
        # Для Linux/macOS используем UTF-8
        try:
            decoded_str = raw_data.decode("utf-8").strip()
            return decoded_str.strip('"')
        except UnicodeDecodeError:
            decoded_str = raw_data.decode("utf-8", errors="ignore").strip()
            return decoded_str.strip('"')


def parse_rac_output(output: str) -> List[Dict[str, Any]]:
    """
    Парсинг вывода rac утилиты - точная копия из run_direct.py

    Args:
        output: Вывод команды rac

    Returns:
        Список словарей с данными
    """
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


def parse_clusters(output: str) -> List[Dict[str, Any]]:
    """
    Парсинг вывода cluster list

    Args:
        output: Вывод команды cluster list

    Returns:
        Список кластеров
    """
    data = parse_rac_output(output)
    clusters = []

    for item in data:
        cluster = {
            "id": item.get("cluster") or item.get("id"),
            "name": item.get("name", "unknown"),
            "host": item.get("host"),
            "port": item.get("port"),
            "status": "unknown",  # Будет определён в ClusterManager/discover_clusters
        }
        clusters.append(cluster)

    return clusters


def parse_infobases(output: str) -> List[Dict[str, Any]]:
    """Парсинг вывода infobase summary list"""
    return parse_rac_output(output)


def parse_sessions(output: str) -> List[Dict[str, Any]]:
    """Парсинг вывода session list"""
    return parse_rac_output(output)


def parse_jobs(output: str) -> List[Dict[str, Any]]:
    """Парсинг вывода job list"""
    return parse_rac_output(output)


def format_lld_data(clusters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Форматирование данных для Zabbix LLD

    Args:
        clusters: Список кластеров

    Returns:
        Данные в формате Zabbix LLD
    """
    return {
        "data": [
            {
                "{#CLUSTER.ID}": c.get("id", ""),
                "{#CLUSTER.NAME}": c.get("name", "unknown"),
                "{#CLUSTER.HOST}": c.get("host", ""),
                "{#CLUSTER.PORT}": c.get("port", ""),
                "{#CLUSTER.STATUS}": c.get("status", "unknown"),
            }
            for c in clusters
            if c.get("id")
        ]
    }


def format_metrics(
    cluster_id: str,
    cluster_name: str,
    total_sessions: int,
    active_sessions: int,
    total_jobs: int,
    active_jobs: int,
    total_infobases: int = 0,
    status: str = "unknown",
) -> Dict[str, Any]:
    """
    Форматирование метрик для Zabbix

    Returns:
        Данные в формате метрик
    """
    return {
        "cluster": {
            "id": cluster_id,
            "name": cluster_name,
            "status": status,
        },
        "metrics": [
            {"key": "zbx1cpy.cluster.total_sessions", "value": total_sessions},
            {"key": "zbx1cpy.cluster.active_sessions", "value": active_sessions},
            {"key": "zbx1cpy.cluster.total_jobs", "value": total_jobs},
            {"key": "zbx1cpy.cluster.active_jobs", "value": active_jobs},
            {"key": "zbx1cpy.cluster.total_infobases", "value": total_infobases},
        ],
    }
