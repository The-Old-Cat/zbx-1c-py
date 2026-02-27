#!/usr/bin/env python3
"""
Скрипт для очистки старых логов технического журнала 1С.

Удаляет файлы логов старше указанного возраста или превышающие лимит размера.
Может использоваться в планировщике задач (Task Scheduler / cron).
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Фикс кодировки UTF-8 для консоли Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Загружаем переменные окружения
load_dotenv()


def get_log_base() -> Path:
    """Получает базовый путь для логов из переменных окружения."""
    log_base = os.getenv("1C_LOG_BASE", "G:/1c_log/zabbix")
    return Path(log_base.replace("/", "\\") if sys.platform == "win32" else log_base)


def get_log_analytics() -> Path:
    """Получает путь для аналитических логов."""
    log_analytics = os.getenv("1C_LOG_ANALYTICS", "G:/1c_log/analytics")
    return Path(log_analytics.replace("/", "\\") if sys.platform == "win32" else log_analytics)


def get_file_age_days(file_path: Path) -> int:
    """Возвращает возраст файла в днях."""
    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
    age = datetime.now() - mtime
    return age.days


def get_file_size_mb(file_path: Path) -> float:
    """Возвращает размер файла в МБ."""
    return file_path.stat().st_size / (1024 * 1024)


def cleanup_directory(
    dir_path: Path,
    max_age_days: int = 7,
    max_size_mb: float = 100.0,
    max_files: int = 10,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict:
    """
    Очищает директорию от старых логов.

    Args:
        dir_path: Путь к директории
        max_age_days: Максимальный возраст файлов (дней)
        max_size_mb: Максимальный размер файла (МБ)
        max_files: Максимальное количество файлов (хранятся последние N)
        dry_run: Только показать, что будет удалено
        verbose: Подробный вывод

    Returns:
        Статистика очистки
    """
    stats = {
        "total_files": 0,
        "deleted_files": 0,
        "deleted_size_mb": 0.0,
        "by_age": 0,
        "by_size": 0,
        "by_count": 0,
    }

    if not dir_path.exists():
        if verbose:
            print(f"⚠️  Директория не найдена: {dir_path}")
        return stats

    # Получаем все файлы, сортируем по времени модификации (новые последние)
    files = sorted(
        dir_path.glob("*.log"),
        key=lambda f: f.stat().st_mtime,
    )
    stats["total_files"] = len(files)

    if not files:
        if verbose:
            print(f"✓ {dir_path} — файлов нет")
        return stats

    # Удаляем по возрасту и размеру
    for file_path in files:
        age_days = get_file_age_days(file_path)
        size_mb = get_file_size_mb(file_path)
        should_delete = False
        reason = ""

        # Проверка по возрасту
        if age_days > max_age_days:
            should_delete = True
            reason = f"возраст {age_days} дн. > {max_age_days}"
            stats["by_age"] += 1

        # Проверка по размеру
        elif size_mb > max_size_mb:
            should_delete = True
            reason = f"размер {size_mb:.1f} МБ > {max_size_mb:.1f}"
            stats["by_size"] += 1

        if should_delete:
            if dry_run:
                if verbose:
                    print(f"🗑️  {file_path} ({reason})")
            else:
                file_path.unlink()
                if verbose:
                    print(f"✅ Удалён: {file_path} ({reason})")
            stats["deleted_files"] += 1
            stats["deleted_size_mb"] += size_mb

    # Удаляем лишние файлы (оставляем только max_files последних)
    if len(files) > max_files:
        files_to_delete = files[: len(files) - max_files]
        for file_path in files_to_delete:
            # Если файл уже был удалён по возрасту/размеру, пропускаем
            if not file_path.exists():
                continue

            if dry_run:
                if verbose:
                    print(f"🗑️  {file_path} (лишний, всего {len(files)} > {max_files})")
            else:
                file_path.unlink()
                if verbose:
                    print(f"✅ Удалён: {file_path} (лишний)")
            stats["deleted_files"] += 1
            stats["deleted_size_mb"] += get_file_size_mb(file_path)
            stats["by_count"] += 1

    return stats


def main() -> int:
    """Точка входа."""
    parser = argparse.ArgumentParser(
        description="Очистка старых логов технического журнала 1С",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  %(prog)s                      # Очистка с настройками по умолчанию
  %(prog)s --dry-run            # Показать, что будет удалено
  %(prog)s --days 30            # Хранить 30 дней
  %(prog)s --max-size 500       # Макс. размер 500 МБ
  %(prog)s --max-files 5        # Хранить макс. 5 файлов
  %(prog)s --verbose            # Подробный вывод
        """,
    )

    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help="Путь к директории логов (по умолчанию: 1C_LOG_BASE)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Максимальный возраст файлов в днях (по умолчанию: 7)",
    )
    parser.add_argument(
        "--max-size",
        type=float,
        default=100.0,
        help="Максимальный размер файла в МБ (по умолчанию: 100)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=10,
        help="Максимальное количество файлов (по умолчанию: 10)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Режим 'сухого запуска' — без удаления",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Подробный вывод",
    )
    parser.add_argument(
        "--analytics",
        action="store_true",
        help="Очистить также аналитические логи",
    )

    args = parser.parse_args()

    # Определяем директории
    log_dirs = []

    if args.log_dir:
        log_dirs.append(args.log_dir)
    else:
        log_base = get_log_base()
        # Добавляем поддиректории
        for subdir in ["errors", "locks", "slow_calls", "slow_sql"]:
            log_dirs.append(log_base / subdir)

        if args.analytics:
            log_analytics = get_log_analytics()
            for subdir in ["errors_full"]:
                log_dirs.append(log_analytics / subdir)

    print(f"🗑️  Очистка логов 1С")
    print(f"   Макс. возраст: {args.days} дн.")
    print(f"   Макс. размер: {args.max_size} МБ")
    print(f"   Макс. файлов: {args.max_files}")
    print(f"   Режим: {'dry-run' if args.dry_run else 'запись'}")
    print()

    total_stats = {
        "total_files": 0,
        "deleted_files": 0,
        "deleted_size_mb": 0.0,
    }

    for dir_path in log_dirs:
        if verbose := args.verbose:
            print(f"📁 {dir_path}:")

        stats = cleanup_directory(
            dir_path=dir_path,
            max_age_days=args.days,
            max_size_mb=args.max_size,
            max_files=args.max_files,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )

        total_stats["total_files"] += stats["total_files"]
        total_stats["deleted_files"] += stats["deleted_files"]
        total_stats["deleted_size_mb"] += stats["deleted_size_mb"]

        if not args.verbose and stats["deleted_files"] > 0:
            print(f"✓ {dir_path.name}: удалено {stats['deleted_files']} файлов")

    print()
    print("=" * 60)
    print(f"📊 Итого:")
    print(f"   Всего файлов: {total_stats['total_files']}")
    print(f"   Удалено файлов: {total_stats['deleted_files']}")
    print(f"   Освобождено: {total_stats['deleted_size_mb']:.1f} МБ")

    if args.dry_run:
        print()
        print("⚠️  Это был dry-run. Файлы не были удалены.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
