"""
Модуль для взаимодействия с RAS (Remote Administration System) 1С:Предприятия
через утилиту rac.exe. Предоставляет функции для получения списка кластеров, парсинга
вывода утилиты и автоматического определения параметров кластера.

Основные возможности:
- Получение списка кластеров через RAS (Remote Administration System) с конфигурируемыми
  хостом и портом подключения
- Парсинг текстового вывода rac.exe в структурированный список словарей
- Автоматическое извлечение и сохранение в настройки:
    * cluster_id — уникальный идентификатор кластера (UUID)
    * cluster_name — человекочитаемое имя кластера

Конфигурация:
- rac_path — путь к исполняемому файлу rac.exe
- rac_host — хост сервера RAS (по умолчанию: localhost)
- rac_port — порт сервера RAS (по умолчанию: 1545)
- cluster_id — автоматически определяемый идентификатор кластера

Зависимости:
- rac.exe (входит в состав платформы 1С:Предприятие)
- loguru — для структурированного логирования
- config.settings — централизованное хранение конфигурационных параметров
"""

import subprocess
from typing import Dict, List
from loguru import logger
from config import settings


def get_clusters() -> str:
    """
    Получает список кластеров 1С через утилиту rac.exe с параметрами из конфигурации.

    Формирует и выполняет команду:
        rac.exe <rac_host>:<rac_port> cluster list

    Returns:
        str: Сырой текстовый вывод утилиты rac.exe в кодировке cp866.
             В случае ошибки возвращает пустую строку.

    Raises:
        subprocess.CalledProcessError: Перехватывается внутри функции с логированием.
        FileNotFoundError: Перехватывается внутри функции с логированием.

    Notes:
        - Кодировка cp866 (OEM 866) обязательна для корректного отображения кириллицы
          в консольном выводе Windows.
        - Параметры подключения (хост и порт) берутся из конфигурации:
          * settings.rac_host — адрес сервера RAS (например, "localhost")
          * settings.rac_port — порт сервера RAS (стандартный: 1545)
        - Путь к исполняемому файлу rac.exe задаётся в settings.rac_path.

    Example:
        При настройках:
            rac_host = "srv-1c"
            rac_port = 1545
        Будет выполнена команда:
            rac.exe srv-1c:1545 cluster list
    """
    rac_path = settings.rac_path
    rac_host = settings.rac_host
    rac_port = settings.rac_port
    # Формируем адрес подключения в формате "хост:порт"
    ras_address = f"{rac_host}:{rac_port}"
    command = [rac_path, ras_address, "cluster", "list"]

    try:
        # Выполняем команду с захватом вывода в кодировке cp866 для поддержки кириллицы
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="cp866",
            check=True,
        )
        logger.debug(f"Успешно получен вывод кластеров ({len(result.stdout)} символов)")
        return result.stdout

    except subprocess.CalledProcessError as e:
        # Ошибка выполнения команды: недоступность сервера, отсутствие прав и т.д.
        logger.error(
            f"Ошибка выполнения команды rac.exe (код возврата {e.returncode}):\n"
            f"Команда: {' '.join(command)}\n"
            f"STDERR: {e.stderr.strip() if e.stderr else '<пусто>'}"
        )
        return ""
    except FileNotFoundError:
        # Исполняемый файл rac.exe не найден по указанному пути
        logger.error(f"Исполняемый файл rac.exe не найден по пути: {rac_path}")
        logger.error("Проверьте корректность настройки 'settings.rac_path'")
        return ""


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
    """
    results: List[Dict[str, str]] = []
    current_item: Dict[str, str] = {}

    # Обрабатываем вывод построчно
    for line in raw_text.splitlines():
        line = line.strip()
        # Пустая строка означает завершение текущей сущности
        if not line:
            if current_item:  # Сохраняем накопленную сущность
                results.append(current_item)
                current_item = {}
            continue

        # Извлекаем пару "ключ: значение" из строки
        if ":" in line:
            key, value = line.split(":", 1)  # Разделяем только по первому двоеточию
            clean_key = key.strip()
            # Удаляем пробелы и внешние двойные кавычки из значения
            clean_value = value.strip().strip('"')
            current_item[clean_key] = clean_value

    # Сохраняем последнюю сущность, если она не была добавлена из-за отсутствия завершающей пустой строки
    if current_item:
        results.append(current_item)

    logger.debug(f"Спарсировано {len(results)} кластер(ов) из вывода RAC")
    return results


# === Автоматическое определение параметров кластера ===
# Получаем сырые данные о кластерах от сервера RAS
raw_clusters = get_clusters()

# Преобразуем текстовый вывод в структурированный список словарей
clusters_list = parse_rac_output(raw_clusters)

# Инициализируем переменные для хранения параметров кластера
auto_cluster_id = None
auto_cluster_name = None

# Извлекаем параметры первого кластера из списка (если список не пуст)
if clusters_list:
    first_cluster = clusters_list[0]
    auto_cluster_id = first_cluster.get("cluster")
    auto_cluster_name = first_cluster.get("name")

    if auto_cluster_id:
        # Сохраняем идентификатор кластера в глобальные настройки приложения
        cluster_id = auto_cluster_id
        logger.info(
            f"Кластер автоматически определён: "
            f"[Имя={auto_cluster_name or '<без имени>'}, ID={cluster_id}]"
        )
    else:
        logger.error("Ошибка: первый элемент в выводе RAC не содержит обязательного поля 'cluster'")
else:
    logger.error("Не удалось определить кластер: вывод RAC пуст или не содержит валидных данных")

# Экспортируем параметры кластера как строковые переменные для внешнего использования
cluster_id: str = str(auto_cluster_id) if auto_cluster_id else ""
cluster_name: str = str(auto_cluster_name) if auto_cluster_name else ""


# === Блок ручного тестирования модуля ===
if __name__ == "__main__":
    logger.info("Запуск модуля в режиме тестирования (__main__)")
    logger.info(f"Параметры подключения: {settings.rac_host}:{settings.rac_port}")

    # Получаем и выводим сырые данные
    output = get_clusters()
    print("\n=== Сырой вывод rac.exe ===")
    print(output if output else "<пустой вывод>")

    # Выводим спарсированные данные в человекочитаемом формате
    print("\n=== Спарсированные данные о кластерах ===")
    parsed = parse_rac_output(output)
    if not parsed:
        print("  <нет данных>")
    else:
        for i, item in enumerate(parsed, 1):
            print(f"\nКластер #{i}:")
            for k, v in sorted(item.items()):
                print(f"  {k:20s}: {v}")

    # Выводим автоматически определённые параметры кластера
    print("\n=== Автоматически определённые параметры кластера ===")
    print(f"cluster_name : {auto_cluster_name or '<не определён>'}")
    print(f"cluster_id   : {auto_cluster_id or '<не определён>'}")
