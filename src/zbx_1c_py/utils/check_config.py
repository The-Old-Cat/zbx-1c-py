#!/usr/bin/env python3
"""
Скрипт для проверки корректности настройки конфигурации проекта zbx-1c-py.

Этот скрипт проверяет:
- Наличие и доступность исполняемого файла rac
- Правильность настроек подключения к RAS
- Доступность директории для логов
- Правильность формата настроек
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import List, Tuple

# Добавляем путь к src для импорта модулей проекта
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zbx_1c_py.config import settings


def check_executable_access(path: str) -> Tuple[bool, str]:
    """Проверяет, существует ли исполняемый файл и доступен ли он для запуска."""
    if not path:
        return False, "Путь к исполняемому файлу не задан"

    path_obj = Path(path)

    if not path_obj.exists():
        return False, f"Файл не найден: {path}"

    if not path_obj.is_file():
        return False, f"Путь указывает не на файл: {path}"

    # Проверяем, является ли файл исполняемым (для Unix-систем)
    if hasattr(os, "access") and hasattr(os, "X_OK"):
        if not os.access(path, os.X_OK):
            return False, f"Файл не является исполняемым: {path}"

    return True, f"Файл доступен: {path}"


def check_log_directory(log_path: str) -> Tuple[bool, str]:
    """Проверяет, доступна ли директория для записи логов."""
    if not log_path:
        # Используем директорию по умолчанию
        log_path = "./logs"

    path_obj = Path(log_path)

    # Пытаемся создать директорию, если она не существует
    try:
        path_obj.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        return False, f"Нет прав на создание директории: {log_path}"
    except OSError as e:
        return False, f"Ошибка при создании директории {log_path}: {e}"

    # Проверяем, можно ли записывать в директорию
    try:
        test_file = path_obj / ".permission_test"
        test_file.touch()
        test_file.unlink()
    except PermissionError:
        return False, f"Нет прав на запись в директорию: {log_path}"
    except (OSError, IOError) as e:
        return False, f"Ошибка при проверке прав записи в {log_path}: {e}"

    return True, f"Директория для логов доступна: {log_path}"


def check_ras_connection() -> Tuple[bool, str]:
    """Проверяет подключение к RAS с помощью простой команды."""
    rac_path = settings.rac_path
    rac_host = settings.rac_host
    rac_port = settings.rac_port

    # Проверяем, доступен ли исполняемый файл
    exec_ok, exec_msg = check_executable_access(rac_path)
    if not exec_ok:
        return False, exec_msg

    # Пытаемся выполнить простую команду для проверки подключения
    try:
        command = [rac_path, f"{rac_host}:{rac_port}", "cluster", "list"]
        result = subprocess.run(
            command, capture_output=True, text=True, check=False, timeout=10  # 10 секунд таймаут
        )

        if result.returncode == 0:
            return True, "Подключение к RAS успешно установлено"
        else:
            stderr_output = result.stderr.strip()
            stdout_output = result.stdout.strip()
            error_msg = (
                stderr_output or stdout_output or f"Команда завершилась с кодом {result.returncode}"
            )
            return False, f"Ошибка подключения к RAS: {error_msg}"

    except subprocess.TimeoutExpired:
        return False, "Таймаут при подключении к RAS. Проверьте хост и порт."
    except FileNotFoundError:
        return False, f"Не найден исполняемый файл: {rac_path}"
    except (subprocess.SubprocessError, OSError, ValueError) as e:
        return False, f"Ошибка при подключении к RAS: {e}"


def validate_settings() -> List[Tuple[str, bool, str]]:
    """Проверяет настройки на корректность."""
    results = []

    # Проверяем путь к rac
    rac_ok, rac_msg = check_executable_access(settings.rac_path)
    results.append(("RAC_PATH", rac_ok, rac_msg))

    # Проверяем директорию логов
    log_ok, log_msg = check_log_directory(settings.log_path)
    results.append(("LOG_PATH", log_ok, log_msg))

    # Проверяем настройки хоста и порта
    if not settings.rac_host:
        results.append(("RAC_HOST", False, "Хост RAS не задан"))
    else:
        results.append(("RAC_HOST", True, f"Хост RAS: {settings.rac_host}"))

    if not settings.rac_port or settings.rac_port <= 0:
        results.append(("RAC_PORT", False, "Порт RAS не задан или недействителен"))
    else:
        results.append(("RAC_PORT", True, f"Порт RAS: {settings.rac_port}"))

    # Проверяем подключение к RAS
    ras_ok, ras_msg = check_ras_connection()
    results.append(("RAS_CONNECTION", ras_ok, ras_msg))

    return results


def print_results(results: List[Tuple[str, bool, str]]):
    """Выводит результаты проверки."""
    print("=" * 60)
    print("РЕЗУЛЬТАТЫ ПРОВЕРКИ КОНФИГУРАЦИИ")
    print("=" * 60)

    success_count = 0
    total_count = len(results)

    for setting_name, is_valid, message in results:
        status = "+" if is_valid else "-"
        print(f"[{status}] {setting_name:<15} - {message}")
        if is_valid:
            success_count += 1

    print("-" * 60)
    print(f"Проверок пройдено: {success_count}/{total_count}")

    if success_count == total_count:
        print(":) Вся конфигурация корректна!")
        return True
    else:
        print(":( Обнаружены проблемы с конфигурацией")
        return False


def main():
    """Основная функция проверки конфигурации."""
    print("Проверка конфигурации проекта zbx-1c-py...")
    print(f"Текущая директория: {os.getcwd()}")
    print()

    # Загружаем настройки
    print("Загруженные настройки:")
    print(f"  RAC_PATH: {settings.rac_path}")
    print(f"  RAC_HOST: {settings.rac_host}")
    print(f"  RAC_PORT: {settings.rac_port}")
    print(f"  LOG_PATH: {settings.log_path}")
    print(f"  USER_NAME: {'*' * len(settings.user_name) if settings.user_name else '(не задан)'}")
    print(f"  DEBUG: {settings.debug}")
    print()

    # Выполняем проверки
    results = validate_settings()

    # Выводим результаты
    success = print_results(results)

    # Возвращаем код возврата
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
