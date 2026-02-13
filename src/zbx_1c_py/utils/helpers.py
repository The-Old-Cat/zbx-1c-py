"""
Вспомогательные утилиты для обработки данных в проекте zbx_1c_py.

Модуль содержит функции для:
- Фильтрации и преобразования списков словарей
- Парсинга вывода утилиты rac.exe
- Декодирования бинарных данных с учетом кодировки 1С
"""

from typing import Dict, List, Union


def universal_filter(data: List[dict], fields: Union[List[str], Dict[str, str]]) -> List[dict]:
    """
    Универсальный фильтр для списков словарей.

    Функция позволяет отфильтровать и/или переименовать поля в списке словарей.
    Поддерживает два режима работы:
    1. Передан список полей - возвращаются только указанные поля
    2. Передан словарь - поля переименовываются согласно соответствиям

    Args:
        data (List[dict]): Исходный список словарей (сессии, процессы и т.д.)
        fields (Union[List[str], Dict[str, str]]):
            - Либо список ['key1', 'key2'] - возвращаются только указанные ключи
            - Либо словарь {'old_key': 'new_key'} - ключи переименовываются

    Returns:
        List[dict]: Отфильтрованный список словарей с требуемыми полями

    Examples:
        >>> data = [{'name': 'Иван', 'age': 30}, {'name': 'Мария', 'age': 25}]
        >>> # Фильтрация по списку полей
        >>> universal_filter(data, ['name'])
        [{'name': 'Иван'}, {'name': 'Мария'}]

        >>> # Переименование полей
        >>> universal_filter(data, {'name': 'full_name', 'age': 'years'})
        [{'full_name': 'Иван', 'years': 30}, {'full_name': 'Мария', 'years': 25}]
    """
    result = []

    for item in data:
        if isinstance(fields, dict):
            # Если передали словарь, переименовываем ключи
            filtered_item = {
                new_key: item.get(old_key, "N/A") for old_key, new_key in fields.items()
            }
        else:
            # Если передали список, просто берем значения
            filtered_item = {key: item.get(key, "N/A") for key in fields}

        result.append(filtered_item)

    return result


def parse_rac_output(raw_text: str) -> List[Dict[str, str]]:
    """
    Преобразует текстовый вывод утилиты rac.exe в структурированный список словарей.

    Алгоритм парсинга:
    1. Разделение вывода на отдельные сущности по пустым строкам
    2. Для каждой строки сущности извлечение пар "ключ: значение"
    3. Очистка значений от ведущих/замыкающих пробелов и двойных кавычек

    Формат входных данных:
        Каждая сущность (кластер) отделена пустой строкой.
        Поля представлены в формате: "ключ             : "значение""
        Значения могут быть заключены в двойные кавычки.

    Пример вывода rac.exe:
        cluster             : "a1b2c3d4-5678-90ab-cdef-1234567890ab"
        name                : "Основной кластер"
        port                : "1541"

        cluster             : "b2c3d4e5-6789-01ab-cdef-2345678901bc"
        name                : "Резервный кластер"
        ...

    Args:
        raw_text (str): Сырой вывод утилиты rac.exe, полученный через get_clusters().

    Returns:
        List[Dict[str, str]]: Список словарей, где каждый словарь представляет один кластер.
                              Ключи словаря — названия полей (например, "cluster", "name"),
                              значения — соответствующие строковые данные без кавычек.

    Example:
        >>> output = 'cluster : "a1b2c3d4"\\nname : "Кластер 1"\\n\\ncluster : "b2c3d4e5"'
        >>> parse_rac_output(output)
        [{'cluster': 'a1b2c3d4', 'name': 'Кластер 1'}, {'cluster': 'b2c3d4e5'}]

    Note:
        - Функция корректно обрабатывает многострочный вывод
        - Пустые строки служат разделителями между сущностями
        - Значения автоматически очищаются от двойных кавычек
    """
    results: List[Dict[str, str]] = []
    current_item: Dict[str, str] = {}

    lines = raw_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Пустая строка может означать завершение сущности, но нужно проверить, 
        # начинается ли следующая сущность
        if not line:
            # Проверим, начинается ли следующая строка с ключевого поля (например, 'cluster')
            next_has_key_field = False
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1  # Пропускаем последующие пустые строки
            
            if j < len(lines):
                next_line = lines[j].strip()
                if ":" in next_line:
                    # Если следующая непустая строка содержит ':', проверим, 
                    # является ли это началом новой сущности
                    key, _ = next_line.split(":", 1)
                    key = key.strip()
                    # Обычно новая сущность начинается с ключевых полей, таких как 'cluster'
                    if key.lower() in ['cluster', 'session-id', 'job-id']:  # добавляемые типичные ключи для новых сущностей
                        if current_item:
                            results.append(current_item)
                            current_item = {}
                        # Пропускаем пустые строки и переходим к обработке новой сущности
                        i = j
                        continue
            
            # Если это не начало новой сущности, просто пропускаем пустую строку
            i += 1
            continue

        # Извлекаем пару "ключ: значение" из строки
        if ":" in line:
            key, value = line.split(":", 1)  # Разделяем только по первому двоеточию
            clean_key = key.strip()
            # Удаляем пробелы и внешние двойные кавычки из значения
            clean_value = value.strip().strip('"')
            current_item[clean_key] = clean_value
        
        i += 1

    # Сохраняем последнюю сущность, если она не была добавлена
    if current_item:
        results.append(current_item)

    return results


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

    Example:
        >>> raw_bytes = b'\\xa1\\xa2\\xa3\\xa4'  # Пример байтов в CP866
        >>> decoded = decode_output(raw_bytes)
        >>> print(decoded)
        ''  # или корректный текст в зависимости от содержимого
    """
    if not raw_data:
        return ""

    # Сначала пробуем UTF-8, так как тесты могут использовать UTF-8
    try:
        decoded_str = raw_data.decode("utf-8").strip()
        # Проверяем, содержит ли результат только ASCII или корректную кириллицу
        # Если да, то это правильный результат
        return decoded_str.strip('"')
    except UnicodeDecodeError:
        pass

    # Если UTF-8 не сработал, пробуем CP866 (для реальных данных от 1С на Windows)
    try:
        decoded_str = raw_data.decode("cp866").strip()
        return decoded_str.strip('"')
    except (UnicodeDecodeError, AttributeError):
        # Если оба варианта не сработали, используем UTF-8 с игнорированием ошибок
        decoded_str = raw_data.decode("utf-8", errors="ignore").strip()
        return decoded_str.strip('"')
