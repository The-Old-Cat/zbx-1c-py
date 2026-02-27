#!/usr/bin/env python3
"""
Чтение ошибок из технического журнала 1С.

Выводит события EXCP (ошибки) и ATTN (предупреждения) в формате JSON.
"""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from zbx_1c.techlog.reader import TechLogReader

# Загружаем переменные окружения
load_dotenv()


def get_log_base() -> Path:
    """Получает базовый путь для логов из переменных окружения."""
    import os

    log_base = os.getenv("1C_LOG_BASE", "G:/1c_log/zabbix")
    return Path(log_base.replace("/", "\\") if sys.platform == "win32" else log_base)


def main() -> int:
    """Точка входа."""
    parser = argparse.ArgumentParser(
        description="Чтение ошибок из технического журнала 1С",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  %(prog)s                      # Все ошибки за последние 5 минут
  %(prog)s --minutes 60         # Ошибки за последний час
  %(prog)s --lines 100          # Последние 100 ошибок
  %(prog)s --count              # Только количество ошибок
  %(prog)s --format text        # Текстовый формат вывода
        """,
    )

    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help="Путь к директории логов (по умолчанию: 1C_LOG_BASE/errors)",
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
        "--include-att",
        action="store_true",
        help="Включить предупреждения (ATTN)",
    )

    args = parser.parse_args()

    # Определяем директорию логов
    log_dir = args.log_dir or (get_log_base() / "errors")

    if not log_dir.exists():
        print(f"❌ Директория логов не найдена: {log_dir}", file=sys.stderr)
        return 1

    # Создаём читатель
    reader = TechLogReader(log_dir)

    # Типы событий
    event_types = ["EXCP"]
    if args.include_att:
        event_types.append("ATTN")

    # Получаем события
    if args.count:
        count = reader.count_events(event_types=event_types, minutes=args.minutes)
        print(count)
    else:
        events = reader.get_latest_events(
            count=0,  # Без лимита
            event_types=event_types,
            minutes=args.minutes,
        )

        if args.output_format == "json":
            # JSON массив
            output = [e.to_dict() for e in events]
            print(json.dumps(output, ensure_ascii=False, indent=2))
        elif args.output_format == "text":
            # Текстовый формат
            for event in events:
                descr = event.properties.get("descr", "")
                context = event.properties.get("context", "")
                computer = event.properties.get("t:computerName", "")
                
                print(
                    f"{event.timestamp} | {event.event_type} | "
                    f"{event.process_name} | {event.user} | "
                    f"{descr[:50] if descr else 'N/A'}"
                )
        elif args.output_format == "line":
            # JSON построчно (для Zabbix)
            for event in events:
                print(event.to_json_line())

    return 0


if __name__ == "__main__":
    sys.exit(main())
