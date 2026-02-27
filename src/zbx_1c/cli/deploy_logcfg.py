#!/usr/bin/env python3
"""
Скрипт деплоя шаблона logcfg.xml на сервер 1С.

Подставляет переменные окружения из .env в шаблон config/logcfg.xml
и копирует результат в целевую директорию сервера 1С.

Кроссплатформенный (Windows, Linux, macOS).
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

# Фикс кодировки UTF-8 для консоли Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Загружаем переменные окружения из .env
load_dotenv()


def get_env_required(name: str) -> str:
    """Получить переменную окружения, ошибка если не задана."""
    value = os.getenv(name)
    if not value:
        print(f"❌ Ошибка: переменная окружения {name} не задана в .env")
        sys.exit(1)
    return value


def get_project_root() -> Path:
    """Возвращает корневую директорию проекта."""
    # __file__ = src/zbx_1c/cli/deploy_logcfg.py
    # parent = src/zbx_1c/cli
    # parent.parent = src/zbx_1c
    # parent.parent.parent = src
    # parent.parent.parent.parent = project root
    return Path(__file__).resolve().parent.parent.parent.parent


def substitute_template(template_path: Path, replacements: dict[str, str]) -> str:
    """Подставляет значения в шаблон XML."""
    content = template_path.read_text(encoding="utf-8")
    for placeholder, value in replacements.items():
        # Нормализуем слеши: все пути в XML должны быть единообразны
        # Для Windows используем обратные слеши, для Linux/macOS — прямые
        if sys.platform == "win32":
            normalized_value = value.replace("/", "\\")
        else:
            normalized_value = value.replace("\\", "/")
        content = content.replace(f"{{{{{placeholder}}}}}", normalized_value)
    return content


def validate_xml_content(content: str) -> bool:
    """Базовая валидация XML (проверка структуры)."""
    required_tags = ["<config", "<log", "</config>"]
    return all(tag in content for tag in required_tags)


def extract_log_paths(xml_content: str) -> list[str]:
    """
    Извлекает пути к директориям логов из XML-контента.

    Ищет атрибуты location в тегах <log> и <query:log>.

    Args:
        xml_content: Содержимое XML-файла

    Returns:
        Список путей к директориям
    """
    paths = []

    # Паттерн для поиска location="..." в тегах log и query:log
    pattern = r'<(?:query:)?log[^>]*\slocation="([^"]+)"'
    matches = re.findall(pattern, xml_content)

    for location in matches:
        # Извлекаем родительскую директорию из пути
        # Например: G:\1c_log\zabbix\errors → G:\1c_log\zabbix
        dir_path = Path(location).parent
        paths.append(str(dir_path))

    # Удаляем дубликаты
    return list(set(paths))


def create_log_directories(
    template_path: Path,
    replacements: dict[str, str],
    dry_run: bool = False,
) -> bool:
    """
    Создаёт директории для логов на основе шаблона.

    Args:
        template_path: Путь к шаблону logcfg.xml
        replacements: Словарь замен для подстановки в шаблон
        dry_run: Только показать, что будет сделано

    Returns:
        True если успешно
    """
    if not template_path.exists():
        print(f"❌ Шаблон не найден: {template_path}")
        return False

    # Читаем и подставляем значения в шаблон
    content = substitute_template(template_path, replacements)

    # Извлекаем пути
    log_dirs = extract_log_paths(content)

    if not log_dirs:
        print("⚠️  Не найдены директории для логов в шаблоне")
        return True

    print(f"📁 Директории для логов ({len(log_dirs)}):")

    for dir_path in log_dirs:
        path = Path(dir_path)

        if dry_run:
            status = "существует" if path.exists() else "будет создана"
            print(f"   {dir_path} — {status}")
        else:
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                print(f"   ✅ Создана: {dir_path}")
            else:
                print(f"   ✓ Существует: {dir_path}")

    return True


def deploy_logcfg(
    template_path: Path,
    target_path: Path,
    replacements: dict[str, str],
    backup: bool = True,
    dry_run: bool = False,
) -> bool:
    """
    Деплой logcfg.xml.

    Args:
        template_path: Путь к шаблону
        target_path: Путь назначения
        replacements: Словарь замен {placeholder: value}
        backup: Создать бэкап существующего файла
        dry_run: Только показать, что будет сделано

    Returns:
        True если успешно
    """
    # Проверяем существование шаблона
    if not template_path.exists():
        print(f"❌ Шаблон не найден: {template_path}")
        return False

    # Генерируем итоговый контент
    content = substitute_template(template_path, replacements)

    # Валидация
    if not validate_xml_content(content):
        print("❌ Ошибка: сгенерированный XML некорректен")
        return False

    # Dry run
    if dry_run:
        print("📋 Dry run — изменения не вносятся:")
        print(f"   Шаблон: {template_path}")
        print(f"   Назначение: {target_path}")
        print(f"   Переменные: {replacements}")
        print("\n📄 Сгенерированный контент:")
        print("-" * 60)
        print(content)
        print("-" * 60)
        return True

    # Создаём родительскую директорию
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Бэкап существующего файла
    if target_path.exists() and backup:
        backup_path = target_path.with_suffix(".xml.bak")
        shutil.copy2(target_path, backup_path)
        print(f"💾 Бэкап сохранён: {backup_path}")

    # Записываем файл
    target_path.write_text(content, encoding="utf-8")
    print(f"✅ Успешно: {target_path}")

    return True


def main() -> int:
    """Точка входа."""
    parser = argparse.ArgumentParser(
        description="Деплой шаблона logcfg.xml на сервер 1С",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  %(prog)s                     # Обычный деплой
  %(prog)s --dry-run           # Показать, что будет сделано
  %(prog)s --no-backup         # Без бэкапа
  %(prog)s --no-create-dirs    # Не создавать директории
  %(prog)s --template my.xml   # Свой шаблон
        """,
    )

    parser.add_argument(
        "--template",
        type=Path,
        default=None,
        help="Путь к шаблону (по умолчанию: LOGCFG_TEMPLATE из .env)",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=None,
        help="Путь назначения (по умолчанию: 1C_LOGCFG_TARGET из .env)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Не создавать бэкап существующего файла",
    )
    parser.add_argument(
        "--no-create-dirs",
        action="store_true",
        help="Не создавать директории для логов автоматически",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Режим 'сухого запуска' — без записи файлов",
    )

    args = parser.parse_args()

    # Получаем пути из переменных окружения или аргументов
    project_root = get_project_root()

    # Получаем шаблон: если путь относительный — добавляем project_root
    template_env = get_env_required("LOGCFG_TEMPLATE")
    template_path = args.template or Path(template_env)
    if not template_path.is_absolute():
        template_path = project_root / template_path

    # Получаем целевой путь
    target_env = get_env_required("1C_LOGCFG_TARGET")
    target_path = args.target or Path(target_env)

    # Нормализуем пути (конвертируем / в \ для Windows)
    if sys.platform == "win32":
        template_path = Path(str(template_path).replace("/", "\\"))
        target_path = Path(str(target_path).replace("/", "\\"))

    # Переменные для подстановки
    replacements = {
        "LOG_BASE": get_env_required("1C_LOG_BASE"),
        "LOG_ANALYTICS": get_env_required("1C_LOG_ANALYTICS"),
    }

    print(f"🚀 Деплой logcfg.xml")
    print(f"   Шаблон: {template_path}")
    print(f"   Назначение: {target_path}")
    print(f"   Бэкап: {'нет' if args.no_backup else 'да'}")
    print(f"   Создание директорий: {'нет' if args.no_create_dirs else 'да'}")
    print()

    # Создаём директории для логов (если не отключено)
    if not args.no_create_dirs:
        success = create_log_directories(
            template_path=template_path,
            replacements=replacements,
            dry_run=args.dry_run,
        )
        if not success:
            return 1
        print()

    success = deploy_logcfg(
        template_path=template_path,
        target_path=target_path,
        replacements=replacements,
        backup=not args.no_backup,
        dry_run=args.dry_run,
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
