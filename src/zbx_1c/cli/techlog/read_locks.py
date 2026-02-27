#!/usr/bin/env python3
"""
Чтение блокировок из технического журнала 1С.

Выводит события TLOCK (блокировки), TDEADLOCK (взаимные блокировки),
TTIMEOUT (таймауты блокировок) в формате JSON.
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
        description="Чтение блокировок из технического журнала 1С",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  %(prog)s                      # Блокировки за последние 5 минут
  %(prog)s --minutes 60         # Блокировки за последний час
  %(prog)s --deadlocks          # Только взаимные блокировки
  %(prog)s --count              # Только количество блокировок
  %(prog)s --format line        # JSON построчно (для Zabbix)
        """,
    )

    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help="Путь к директории логов (по умолчанию: 1C_LOG_BASE/locks)",
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
        "--deadlocks",
        action="store_true",
        help="Только взаимные блокировки (TDEADLOCK)",
    )
    parser.add_argument(
        "--timeouts",
        action="store_true",
        help="Только таймауты (TTIMEOUT)",
    )
    parser.add_argument(
        "--min-duration",
        type=int,
        default=0,
        help="Минимальная длительность в мс (0 — без фильтра)",
    )

    args = parser.parse_args()

    # Определяем директорию логов
    log_dir = args.log_dir or (get_log_base() / "locks")

    if not log_dir.exists():
        print(f"❌ Директория логов не найдена: {log_dir}", file=sys.stderr)
        return 1

    # Создаём читатель
    reader = TechLogReader(log_dir)

    # Типы событий
    if args.deadlocks:
        event_types = ["TDEADLOCK"]
    elif args.timeouts:
        event_types = ["TTIMEOUT"]
    else:
        event_types = ["TLOCK", "TDEADLOCK", "TTIMEOUT"]

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

        # Фильтр по длительности (для TLOCK из LOCKS_05sec)
        if args.min_duration > 0:
            filtered_events = []
            for event in events:
                # Пробуем получить длительность из разных свойств
                duration_ms = 0
                
                # Durationus (мкс) - из TLOCK
                if "Durationus" in event.properties:
                    try:
                        duration_ms = int(event.properties["Durationus"]) / 1000
                    except ValueError:
                        pass
                
                # Если нет Durationus, пропускаем фильтр
                if duration_ms > 0 and duration_ms >= args.min_duration:
                    filtered_events.append(event)
                elif duration_ms == 0:
                    # Если длительность не указана, включаем событие
                    filtered_events.append(event)
            events = filtered_events

        if args.output_format == "json":
            # JSON массив
            output = [e.to_dict() for e in events]
            print(json.dumps(output, ensure_ascii=False, indent=2))
        elif args.output_format == "text":
            # Текстовый формат
            for event in events:
                # Пробуем получить длительность
                duration_ms = 0
                if "Durationus" in event.properties:
                    try:
                        duration_ms = int(event.properties["Durationus"]) / 1000
                    except ValueError:
                        duration_ms = 0
                
                connect_id = event.properties.get("t:connectID", "")
                wait_connections = event.properties.get("waitconnections", "")
                regions = event.properties.get("regions", "")
                locks = event.properties.get("locks", "")
                
                print(
                    f"{event.timestamp} | {event.event_type} | "
                    f"{event.process_name} | {event.user} | "
                    f"Duration: {duration_ms:.0f} мс | "
                    f"ConnectID: {connect_id} | "
                    f"Wait: {wait_connections} | "
                    f"Regions: {regions}"
                )
        elif args.output_format == "line":
            # JSON построчно (для Zabbix)
            for event in events:
                print(event.to_json_line())

    return 0


if __name__ == "__main__":
    sys.exit(main())
