#!/usr/bin/env python
# run_publisher.py
"""Запуск публикатора 1С с автоматическим получением списка баз."""

import sys
import os
import logging
import re
import platform
import subprocess
from pathlib import Path
from datetime import datetime

# =============================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# =============================================================


def setup_logging():
    """Настраивает логирование."""
    log_dir = Path("G:/Automation/zbx-1c-py/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"publisher_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    console_handler = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    print(f"[LOG] Лог файл: {log_file}")
    return log_file


log_file = setup_logging()
logger = logging.getLogger(__name__)


def check_admin_rights() -> bool:
    """Проверяет наличие прав администратора."""
    system = platform.system().lower()
    
    if system == "windows":
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    elif system == "linux":
        try:
            return os.geteuid() == 0
        except AttributeError:
            try:
                return os.getuid() == 0
            except AttributeError:
                try:
                    result = subprocess.run(['id', '-u'], capture_output=True, text=True)
                    return result.stdout.strip() == '0'
                except:
                    return False
        except Exception:
            return False
    # Для macOS и других ОС считаем что права есть
    return True


def find_env_file() -> Path:
    """Ищет .env файл."""
    possible_paths = [
        Path.cwd() / ".env",
        Path(__file__).parent / ".env",
        Path(__file__).parent.parent / ".env",
        Path("G:/Automation/zbx-1c-py") / ".env",
    ]

    for path in possible_paths:
        if path.exists():
            logger.info(f"Найден .env: {path}")
            return path

    logger.warning(".env не найден")
    return None


def load_env_file(env_path: Path) -> dict:
    """Загружает .env файл."""
    env_vars = {}

    if not env_path:
        return env_vars

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]

                    env_vars[key] = value
                    os.environ[key] = value

                    # Логируем с маскировкой
                    key_upper = key.upper()
                    if any(x in key_upper for x in ("PASSWORD", "PWD", "SECRET")):
                        logger.debug(f"  {key} = ***")
                    elif any(x in key_upper for x in ("USER", "USERNAME", "LOGIN")):
                        masked_value = value[:3] + "***" if value else ""
                        logger.debug(f"  {key} = {masked_value}")
                    else:
                        logger.debug(f"  {key} = {value[:50] if len(value) > 50 else value}")

    except Exception as e:
        logger.error(f"Ошибка загрузки .env: {e}")

    logger.info(f"Загружено переменных: {len(env_vars)}")
    return env_vars


def setup_python_path():
    """Настраивает PYTHONPATH."""
    src_path = Path(__file__).parent / "src"
    if src_path.exists() and str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
        logger.info(f"Добавлен путь: {src_path}")


def print_config_summary(config):
    """Выводит краткую сводку конфигурации."""
    print("\n" + "=" * 60)
    print("КОНФИГУРАЦИЯ")
    print("=" * 60)
    print(f"  Сервер 1С:           {config.SERVER_1C_HOST}:{config.SERVER_1C_PORT}")
    print(f"  Режим публикации:    {config.PUBLISH_MODE}")
    print(f"  Тип публикации:      {config.PUBLISH_TYPE}")
    print(f"  Каталог публикации:  {config.PUBLISH_ROOT}")
    print(f"  Путь к webinst:      {config.WEBINST_PATH}")
    print(f"  Путь к Apache conf:  {config.APACHE_CONF_PATH}")
    print(f"  Уровень логирования: {getattr(config, 'PUBLISHER_LOG_LEVEL', 'INFO')}")
    print(f"  Лог файл:            {log_file}")
    print("=" * 60)


def display_bases(bases, title="НАЙДЕННЫЕ ИНФОРМАЦИОННЫЕ БАЗЫ"):
    """Отображает список баз."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

    if not bases:
        print("  Нет баз для отображения")
        return

    for i, base in enumerate(bases, 1):
        if hasattr(base, "folder_path") and base.folder_path:
            print(f"  {i}. {base.folder_path}/{base.name}")
        elif hasattr(base, "full_name"):
            print(f"  {i}. {base.full_name}")
        else:
            print(f"  {i}. {base}")

    print("-" * 60)
    print(f"  Всего: {len(bases)}")
    print("=" * 60)


def display_published_bases(published):
    """Отображает список опубликованных баз."""
    print("\n" + "=" * 60)
    print("ОПУБЛИКОВАННЫЕ БАЗЫ")
    print("=" * 60)

    if not published:
        print("  Нет опубликованных баз")
        return

    for i, base in enumerate(published, 1):
        print(f"  {i}. {base}")

    print("-" * 60)
    print(f"  Всего: {len(published)}")
    print("=" * 60)


def main():
    """Основная функция."""
    logger.info("=" * 60)
    logger.info("ЗАПУСК АВТОПУБЛИКАТОРА 1С")
    logger.info("=" * 60)

    # Проверяем права администратора
    if not check_admin_rights():
        print("\n" + "=" * 60)
        print("⚠ ВНИМАНИЕ!")
        print("=" * 60)
        print("Скрипт не запущен с правами администратора.")
        print("Для публикации/удаления баз 1С и управления Apache")
        print("необходимы права администратора.")
        print("\nПожалуйста, запустите скрипт от имени администратора:")
        print("  - Щёлкните правой кнопкой по .bat файлу")
        print("  - Выберите 'Запуск от имени администратора'")
        print("=" * 60)
        
        confirm = input("\nПродолжить без прав администратора? (y/n): ").strip().lower()
        if confirm != 'y':
            print("  Завершение работы.")
            return

    # 1. Загрузка конфигурации
    print("\n[1] Загрузка конфигурации...")
    env_file = find_env_file()
    if env_file:
        load_env_file(env_file)

    # 2. Настройка путей
    print("\n[2] Настройка путей...")
    setup_python_path()

    # 3. Импорт модулей
    print("\n[3] Загрузка модулей...")
    try:
        from zbx_1c_publisher.core.config import PublisherConfig
        from zbx_1c_publisher.core.publisher import (
            publish_multiple_bases,
            delete_multiple_bases,
            delete_all_published_bases,
            get_published_bases,
            find_webinst,
        )
        from zbx_1c_publisher.core.discovery import get_bases_from_server
        from zbx_1c_publisher.core.apache_conf import (
            ensure_1c_conf_included,
            validate_apache_config,
            list_1c_aliases,
        )

        print("    ✓ Модули загружены")
    except ImportError as e:
        print(f"    ✗ Ошибка: {e}")
        logger.error(f"Ошибка импорта: {e}")
        return

    # 4. Инициализация конфигурации
    print("\n[4] Инициализация конфигурации...")
    try:
        config = PublisherConfig()
        print("    ✓ Конфигурация загружена")
    except Exception as e:
        print(f"    ✗ Ошибка: {e}")
        logger.error(f"Ошибка конфигурации: {e}")
        return

    # 5. Вывод конфигурации
    print_config_summary(config)

    # 6. Проверка webinst
    print("\n[5] Проверка webinst...")
    webinst = find_webinst(config)
    if not webinst:
        print("    ✗ webinst не найден!")
        logger.error("webinst не найден")
        return
    print(f"    ✓ webinst найден: {webinst}")

    # 7. Проверка конфигурации Apache
    print("\n[6] Проверка конфигурации Apache...")
    if not ensure_1c_conf_included(config):
        print("    ⚠ Не удалось подключить httpd-1c.conf")

    ok, msg = validate_apache_config(config)
    if ok:
        print(f"    ✓ {msg}")
    else:
        print(f"    ✗ Ошибка: {msg}")
        logger.warning(f"Ошибка конфигурации Apache: {msg}")

    # 8. Главное меню
    while True:
        print("\n" + "=" * 60)
        print("ГЛАВНОЕ МЕНЮ")
        print("=" * 60)
        print("  1 - Публикация новых баз")
        print("  2 - Переопубликовать существующие базы")
        print("  3 - Удалить публикации")
        print("  4 - Удалить ВСЕ публикации")
        print("  5 - Показать список доступных баз")
        print("  6 - Показать список опубликованных баз")
        print("  7 - Показать алиасы 1С в Apache")
        print("  0 - Выход")
        print("=" * 60)

        choice = input("\nВаш выбор: ").strip()

        if choice == "0":
            print("\n  Завершение работы.")
            break

        elif choice == "1":
            print("\n[7] Получение списка баз...")
            bases = get_bases_from_server(config)

            if not bases:
                print("\n    ✗ Не удалось получить список баз!")
                continue

            display_bases(bases, "ДОСТУПНЫЕ БАЗЫ")

            print("\nВыберите действие:")
            print("  1 - Опубликовать все базы")
            print("  2 - Опубликовать выбранные")
            print("  3 - Опубликовать по префиксу")

            sub_choice = input("\nВаш выбор: ").strip()

            if sub_choice == "1":
                bases_to_publish = [
                    b.full_name if hasattr(b, "full_name") else b.name for b in bases
                ]
                print(f"\n  Будут опубликованы ВСЕ {len(bases_to_publish)} баз")
            elif sub_choice == "2":
                indices = input("\nВведите номера через запятую: ").strip()
                try:
                    selected = [int(i.strip()) - 1 for i in indices.split(",")]
                    bases_to_publish = [
                        bases[i].full_name if hasattr(bases[i], "full_name") else bases[i].name
                        for i in selected
                        if 0 <= i < len(bases)
                    ]
                    print(f"\n  Выбрано: {len(bases_to_publish)}")
                except Exception:
                    print("  ✗ Неверный ввод!")
                    continue
            elif sub_choice == "3":
                prefix = input("\nВведите префикс: ").strip()
                bases_to_publish = [
                    b.full_name if hasattr(b, "full_name") else b.name
                    for b in bases
                    if b.name.startswith(prefix)
                ]
                print(f"\n  Найдено баз с префиксом '{prefix}': {len(bases_to_publish)}")
            else:
                print("  ✗ Неверный выбор!")
                continue

            if not bases_to_publish:
                print("\n  ✗ Нет баз для публикации!")
                continue

            confirm = input(f"\nПубликовать {len(bases_to_publish)} баз? (y/n): ")
            if confirm.lower() != "y":
                print("  Отменено")
                continue

            print("\n" + "=" * 60)
            print("НАЧАЛО ПУБЛИКАЦИИ")
            print("=" * 60)

            results = publish_multiple_bases(bases_to_publish, config, skip_existing=False)

            print("\n" + "=" * 60)
            print("РЕЗУЛЬТАТЫ")
            print("=" * 60)

            success = sum(1 for v in results.values() if v[0])
            for base, (ok, msg) in results.items():
                status = "✅" if ok else "❌"
                print(f"  {status} {base}")
                if not ok:
                    logger.error(f"Ошибка {base}: {msg[:200]}")

            print("-" * 60)
            print(f"  Успешно: {success} из {len(bases_to_publish)}")
            print("=" * 60)

        elif choice == "2":
            print("\n[7] Получение списка опубликованных баз...")
            published = get_published_bases(config)
            display_published_bases(published)

            if not published:
                print("\n  ✗ Нет опубликованных баз!")
                continue

            print("\nВыберите действие:")
            print("  1 - Переопубликовать все базы")
            print("  2 - Переопубликовать выбранные")
            print("  3 - Переопубликовать по префиксу")

            sub_choice = input("\nВаш выбор: ").strip()

            if sub_choice == "1":
                bases_to_republish = published
                print(f"\n  Будут переопубликованы ВСЕ {len(bases_to_republish)} баз")
            elif sub_choice == "2":
                indices = input("\nВведите номера через запятую: ").strip()
                try:
                    selected = [int(i.strip()) - 1 for i in indices.split(",")]
                    bases_to_republish = [published[i] for i in selected if 0 <= i < len(published)]
                    print(f"\n  Выбрано: {len(bases_to_republish)}")
                except Exception:
                    print("  ✗ Неверный ввод!")
                    continue
            elif sub_choice == "3":
                prefix = input("\nВведите префикс: ").strip()
                bases_to_republish = [b for b in published if b.startswith(prefix)]
                print(f"\n  Найдено баз с префиксом '{prefix}': {len(bases_to_republish)}")
            else:
                print("  ✗ Неверный выбор!")
                continue

            if not bases_to_republish:
                print("\n  ✗ Нет баз для переопубликования!")
                continue

            confirm = input(f"\nПереопубликовать {len(bases_to_republish)} баз? (y/n): ")
            if confirm.lower() != "y":
                print("  Отменено")
                continue

            print("\n" + "=" * 60)
            print("НАЧАЛО ПЕРЕОПУБЛИКОВАНИЯ")
            print("=" * 60)

            # Сначала удаляем, потом публикуем заново
            print("\nУдаление старых публикаций...")
            delete_results = delete_multiple_bases(bases_to_republish, config, delete_files=True, auto_restart=False)
            
            print("\nПубликация заново...")
            results = publish_multiple_bases(bases_to_republish, config, skip_existing=False)

            print("\n" + "=" * 60)
            print("РЕЗУЛЬТАТЫ")
            print("=" * 60)

            success = sum(1 for v in results.values() if v[0])
            for base, (ok, msg) in results.items():
                status = "✅" if ok else "❌"
                print(f"  {status} {base}")
                if not ok:
                    logger.error(f"Ошибка {base}: {msg[:200]}")

            print("-" * 60)
            print(f"  Успешно: {success} из {len(bases_to_republish)}")
            print("=" * 60)

        elif choice == "3":
            print("\n[7] Получение списка опубликованных баз...")
            published = get_published_bases(config)
            display_published_bases(published)

            if not published:
                print("\n  ✗ Нет опубликованных баз для удаления!")
                continue

            print("\nВыберите действие:")
            print("  1 - Удалить все публикации")
            print("  2 - Удалить выбранные")
            print("  3 - Удалить по префиксу")

            sub_choice = input("\nВаш выбор: ").strip()

            if sub_choice == "1":
                bases_to_delete = published
                print(f"\n  Будут удалены ВСЕ {len(bases_to_delete)} публикаций")
            elif sub_choice == "2":
                indices = input("\nВведите номера через запятую: ").strip()
                try:
                    selected = [int(i.strip()) - 1 for i in indices.split(",")]
                    bases_to_delete = [published[i] for i in selected if 0 <= i < len(published)]
                    print(f"\n  Выбрано: {len(bases_to_delete)}")
                except Exception:
                    print("  ✗ Неверный ввод!")
                    continue
            elif sub_choice == "3":
                prefix = input("\nВведите префикс: ").strip()
                bases_to_delete = [b for b in published if b.startswith(prefix)]
                print(f"\n  Найдено баз с префиксом '{prefix}': {len(bases_to_delete)}")
            else:
                print("  ✗ Неверный выбор!")
                continue

            if not bases_to_delete:
                print("\n  ✗ Нет баз для удаления!")
                continue

            delete_files_input = (
                input("\nУдалять файлы публикации? (y/n, по умолчанию y): ").strip().lower()
            )
            delete_files = delete_files_input != "n"

            confirm = input(f"\nУдалить {len(bases_to_delete)} публикаций? (yes/no): ")
            if confirm.lower() != "yes":
                print("  Отменено")
                continue

            print("\n" + "=" * 60)
            print("НАЧАЛО УДАЛЕНИЯ")
            print("=" * 60)

            results = delete_multiple_bases(
                bases_to_delete, config, delete_files=delete_files, auto_restart=True
            )

            print("\n" + "=" * 60)
            print("РЕЗУЛЬТАТЫ УДАЛЕНИЯ")
            print("=" * 60)

            success = sum(1 for v in results.values() if v[0])
            for base, (ok, msg) in results.items():
                status = "✅" if ok else "❌"
                print(f"  {status} {base}")
                if not ok:
                    logger.error(f"Ошибка удаления {base}: {msg[:200]}")

            print("-" * 60)
            print(f"  Успешно удалено: {success} из {len(bases_to_delete)}")
            print("=" * 60)

        elif choice == "4":
            print("\n[7] Получение списка опубликованных баз...")
            published = get_published_bases(config)
            display_published_bases(published)

            if not published:
                print("\n  ✗ Нет опубликованных баз для удаления!")
                continue

            print(f"\n⚠ ВНИМАНИЕ! Вы собираетесь удалить ВСЕ {len(published)} публикаций!")
            delete_files_input = (
                input("\nУдалять файлы публикации? (y/n, по умолчанию y): ").strip().lower()
            )
            delete_files = delete_files_input != "n"

            confirm = input(f"\nДля подтверждения введите 'УДАЛИТЬ ВСЕ': ")
            if confirm != "УДАЛИТЬ ВСЕ":
                print("  Отменено")
                continue

            print("\n" + "=" * 60)
            print("НАЧАЛО УДАЛЕНИЯ ВСЕХ ПУБЛИКАЦИЙ")
            print("=" * 60)

            results = delete_all_published_bases(
                config, delete_files=delete_files, auto_restart=True
            )

            print("\n" + "=" * 60)
            print("РЕЗУЛЬТАТЫ УДАЛЕНИЯ")
            print("=" * 60)

            success = sum(1 for v in results.values() if v[0])
            for base, (ok, msg) in results.items():
                status = "✅" if ok else "❌"
                print(f"  {status} {base}")

            print("-" * 60)
            print(f"  Успешно удалено: {success} из {len(published)}")
            print("=" * 60)

        elif choice == "5":
            print("\n[7] Получение списка баз...")
            bases = get_bases_from_server(config)

            if not bases:
                print("\n    ✗ Не удалось получить список баз!")
                continue

            display_bases(bases, "ДОСТУПНЫЕ БАЗЫ")

        elif choice == "6":
            print("\n[7] Получение списка опубликованных баз...")
            published = get_published_bases(config)
            display_published_bases(published)

        elif choice == "7":
            print("\n[7] Получение списка алиасов 1С...")
            aliases = list_1c_aliases(config)
            if aliases:
                print("\n  Найдены алиасы:")
                for alias in aliases:
                    print(f"    - /{alias}")
            else:
                print("  Алиасы не найдены")

        else:
            print("  ✗ Неверный выбор!")

    print(f"\nЛог сохранен в: {log_file}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрерывание пользователем")
        logger.info("Прерывание пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        logger.error(f"Необработанная ошибка: {e}", exc_info=True)
    finally:
        print(f"\nЛог сохранен в: {log_file}")
        input("\nНажмите Enter для выхода...")