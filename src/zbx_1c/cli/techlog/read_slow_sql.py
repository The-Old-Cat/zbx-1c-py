#!/usr/bin/env python3
"""
Чтение медленного SQL из технического журнала 1С.

Выводит события SDBL (медленные SQL-запросы) с длительностью больше порога.
"""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from zbx_1c.techlog.reader import TechLogReader


def get_log_base() -> Path:
    """Получает базовый путь для логов из переменных окружения."""
    import os

    log_base = os.getenv("1C_LOG_BASE", "G:/1c_log/zabbix")
    return Path(log_base.replace("/", "\\") if sys.platform == "win32" else log_base)


def main() -> int:
    """Точка входа."""
    parser = argparse.ArgumentParser(
        description="Чтение медленного SQL из технического журнала 1С",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  %(prog)s                      # SQL >100 мс за последние 5 минут
  %(prog)s --threshold 500      # SQL >500 мс
  %(prog)s --minutes 60         # SQL за последний час
  %(prog)s --count              # Только количество запросов
  %(prog)s --format line        # JSON построчно (для Zabbix)
        """,
    )

    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help="Путь к директории логов (по умолчанию: 1C_LOG_BASE/slow_sql)",
    )
    parser.add_argument(
        "--minutes",
        type=int,
        default=5,
        help="Период выборки в минутах (0 — все, по умолчанию: 5)",
    )
    parser.add_argument(
        "--lines",
        type=int,
        default=0,
        help="Читать последние N строк (0 — все, по умолчанию: 0)",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="Выводить только количество событий",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["json", "text", "line"],
        default="json",
        help="Формат вывода (по умолчанию: json)",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=100,
        help="Порог длительности в мс (по умолчанию: 100)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=0,
        help="Только топ N самых долгих запросов (0 — все)",
    )

    args = parser.parse_args()

    # Определяем директорию логов
    log_dir = args.log_dir or (get_log_base() / "slow_sql")

    if not log_dir.exists():
        print(f"❌ Директория логов не найдена: {log_dir}", file=sys.stderr)
        return 1

    # Создаём читатель
    reader = TechLogReader(log_dir)

    # Получаем события
    event_types = ["SDBL"]

    if args.count:
        count = reader.count_events(event_types=event_types, minutes=args.minutes)
        print(count)
    else:
        events = reader.get_latest_events(
            count=0,  # Без лимита
            event_types=event_types,
            minutes=args.minutes,
        )

        # Фильтр по порогу длительности
        filtered_events = []
        for event in events:
            duration = event.properties.get("Duration", "0")
            try:
                duration_ms = int(duration)
                if duration_ms >= args.threshold:
                    filtered_events.append(event)
            except ValueError:
                filtered_events.append(event)
        events = filtered_events

        # Сортировка по длительности и топ N
        events.sort(
            key=lambda e: int(e.properties.get("Duration", 0)),
            reverse=True,
        )
        if args.top > 0:
            events = events[: args.top]

        if args.output_format == "json":
            # JSON массив
            output = [e.to_dict() for e in events]
            print(json.dumps(output, ensure_ascii=False, indent=2))
        elif args.output_format == "text":
            # Текстовый формат
            for event in events:
                duration = event.properties.get("Duration", "N/A")
                print(
                    f"{event.timestamp} | {duration} мс | "
                    f"{event.process_name} | {event.user}"
                )
        elif args.output_format == "line":
            # JSON построчно (для Zabbix)
            for event in events:
                print(event.to_json_line())

    return 0


if __name__ == "__main__":
    sys.exit(main())
