"""
Парсеры для вывода rac license list
"""

import re
from typing import Dict, Any, List
from ..core.models import LicenseInfo, LicenseStats


def parse_license_output(output: str) -> List[Dict[str, Any]]:
    """
    Парсинг вывода rac license list

    Пример вывода rac license list:
        license-type: local
        total: 5
        in-use: 3
        free: 2
        series: SLK
        description: "1С:Предприятие 8. Клиентская лицензия"

        license-type: local
        total: 50
        in-use: 12
        free: 38
        series: HASP
        description: "1С:Предприятие 8. Серверная лицензия"

    Args:
        output: Вывод команды rac license list

    Returns:
        Список словарей с данными о лицензиях
    """
    if not output or not output.strip():
        return []

    result = []
    current_license: Dict[str, Any] = {}

    for line in output.split("\n"):
        line = line.strip()

        # Пустая строка — конец текущего блока лицензии
        if not line:
            if current_license:
                result.append(current_license)
                current_license = {}
            continue

        # Парсим строку вида "key: value"
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower().replace("-", "_")
            value = value.strip()

            # Убираем кавычки
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]

            # Конвертация числовых значений
            if key in ("total", "in_use", "free"):
                try:
                    current_license[key] = int(value)
                except ValueError:
                    current_license[key] = 0
            else:
                current_license[key] = value

    # Добавляем последнюю лицензию
    if current_license:
        result.append(current_license)

    return result


def parse_license_type(output: str) -> str:
    """
    Определение типа лицензирования из вывода rac

    Args:
        output: Вывод команды rac license list

    Returns:
        Тип лицензирования: "server", "local", "hasp", "mixed", "unknown"
    """
    licenses = parse_license_output(output)

    if not licenses:
        return "unknown"

    types_found = set()
    for lic in licenses:
        lic_type = lic.get("license_type", "").lower()
        series = lic.get("series", "").upper()

        # Определяем тип по полю license-type
        if lic_type in ("server", "network"):
            types_found.add("server")
        elif lic_type == "local":
            # Проверяем серию для уточнения
            if "HASP" in series or "USB" in series:
                types_found.add("hasp")
            else:
                types_found.add("local")
        elif lic_type == "hasp":
            types_found.add("hasp")
        else:
            types_found.add("unknown")

    if len(types_found) > 1:
        return "mixed"
    elif len(types_found) == 1:
        return types_found.pop()
    else:
        return "unknown"


def calculate_license_totals(licenses: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Подсчет суммарных значений по всем лицензиям

    Args:
        licenses: Список распарсенных лицензий

    Returns:
        Словарь с суммарными значениями: {total, used, free}
    """
    total = sum(lic.get("total", 0) for lic in licenses)
    used = sum(lic.get("in_use", 0) for lic in licenses)
    free = sum(lic.get("free", 0) for lic in licenses)

    return {
        "total": total,
        "used": used,
        "free": free,
    }


def parse_license_stats(output: str, license_type: str, host: str = "localhost") -> LicenseStats:
    """
    Парсинг статистики по лицензиям в модель LicenseStats

    Args:
        output: Вывод команды rac license list
        license_type: Тип лицензирования (server/local/hasp/unknown)
        host: Хост источника лицензий

    Returns:
        Модель LicenseStats со статистикой
    """
    licenses_data = parse_license_output(output)
    licenses = [LicenseInfo.from_dict(lic) for lic in licenses_data]
    totals = calculate_license_totals(licenses_data)

    return LicenseStats(
        license_type=license_type,
        host=host,
        licenses=licenses,
        total_licenses=totals["total"],
        used_licenses=totals["used"],
        free_licenses=totals["free"],
    )
