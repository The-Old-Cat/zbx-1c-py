"""
Базовый модуль для чтения логов технического журнала 1С.

Поддерживает форматы логов:
- Основной лог сервера (ATTN, EXCP, PROC, ADMIN, CLSTR)
- CALL (вызовы методов)
- LOCKS (блокировки: TLOCK, TDEADLOCK, TTOKEN)
- Zabbix логи (calls, locks, excps)
- Query логи (SDBL, DBMSSQL)
- ERROR_EXCP (полные исключения)

Формат строк техжурнала 1С:
<timestamp>|<event>|<property1>|<property2>|...
или
<timestamp> <event> <property1> <property2> ...
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator


@dataclass
class LogEvent:
    """Событие технического журнала 1С."""

    timestamp: datetime
    event_type: str  # EXCP, ATTN, TLOCK, CALL, SDBL и т.д.
    process_name: str
    user: str
    properties: dict[str, str] = field(default_factory=dict)
    raw_line: str = ""

    def to_dict(self) -> dict:
        """Преобразует событие в словарь."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "process_name": self.process_name,
            "user": self.user,
            **self.properties,
        }

    def to_json_line(self) -> str:
        """Преобразует событие в JSON-строку (одна строка)."""
        import json

        return json.dumps(self.to_dict(), ensure_ascii=False)


class TechLogReader:
    """
    Читатель логов технического журнала 1С.

    Поддерживает различные форматы техжурнала 1С.
    """

    # Форматы дат, используемые в техжурнале 1С
    DATE_FORMATS = [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y %H:%M:%S.%f",
        "%d.%m.%Y %H:%M:%S",
        "%Y%m%d%H%M%S%f",
        "%Y%m%d%H%M%S",
    ]

    # Сопоставление типов событий с путями к логам
    EVENT_TYPE_PATHS = {
        "EXCP": "zabbix/excps",
        "ATTN": "srv",
        "CALL": "CALL",
        "TLOCK": "zabbix/locks",
        "TDEADLOCK": "zabbix/locks",
        "TTIMEOUT": "zabbix/locks",
        "SDBL": "Query1c",
        "DBMSSQL": "Query1c",
    }

    def __init__(self, log_dir: str | Path):
        """
        Инициализация читателя логов.

        Args:
            log_dir: Путь к директории с логами
        """
        self.log_dir = Path(log_dir)
        if not self.log_dir.exists():
            raise FileNotFoundError(f"Директория логов не найдена: {log_dir}")

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        Парсит строку времени в datetime.

        Args:
            timestamp_str: Строка времени

        Returns:
            datetime объект
        """
        timestamp_str = timestamp_str.strip()

        # Пробуем разные форматы
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue

        # Если ни один формат не подошёл, пробуем ISO формат
        try:
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            pass

        # Возвращаем текущее время, если не смогли распарсить
        return datetime.now()

    def _parse_line(self, line: str) -> LogEvent | None:
        """
        Парсит одну строку лога.

        Поддерживаемые форматы:
        1. Разделитель |: timestamp|event|processName|user|prop1=value1|prop2=value2
        2. Разделитель ;: timestamp;event;processName;user;prop1;prop2
        3. Разделитель табуляция: timestamp\tevent\tprocessName\tuser\t...
        4. Фиксированная ширина (старый формат)

        Args:
            line: Строка лога

        Returns:
            LogEvent или None, если строка не распарсилась
        """
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            return None

        # Определяем разделитель и разбиваем строку
        parts = self._split_line(line)

        if len(parts) < 2:
            return None

        try:
            timestamp = self._parse_timestamp(parts[0])
            event_type = parts[1].strip().upper() if len(parts) > 1 else "UNKNOWN"

            # Извлекаем свойства
            properties = {}
            process_name = "unknown"
            user = "unknown"

            # Парсим оставшиеся части как свойства
            for i, part in enumerate(parts[2:], start=2):
                part = part.strip()
                if not part:
                    continue

                # Пробуем распарсить как key=value
                if "=" in part:
                    key, _, value = part.partition("=")
                    key = key.strip()
                    value = value.strip()

                    # Нормализуем имена ключей
                    if key.lower() in ("p:processname", "processname"):
                        process_name = value
                    elif key.lower() in ("t:usr", "usr", "user"):
                        user = value
                    else:
                        properties[key] = value
                else:
                    # Если нет =, пытаемся определить по позиции или контексту
                    if i == 2 and process_name == "unknown":
                        process_name = part
                    elif i == 3 and user == "unknown":
                        user = part
                    else:
                        properties[f"prop{i}"] = part

            return LogEvent(
                timestamp=timestamp,
                event_type=event_type,
                process_name=process_name,
                user=user,
                properties=properties,
                raw_line=line,
            )
        except (ValueError, IndexError):
            return None

    def _split_line(self, line: str) -> list[str]:
        """
        Разбивает строку лога на части.

        Args:
            line: Строка лога

        Returns:
            Список частей
        """
        # Пробуем формат с разделителем |
        if "|" in line:
            return line.split("|")

        # Пробуем формат с разделителем ;
        if ";" in line:
            return line.split(";")

        # Пробуем разделить по табуляции
        if "\t" in line:
            return line.split("\t")

        # Пробуем разделить по пробелам (для старого формата)
        # Но аккуратно — timestamp может содержать пробелы
        parts = re.split(r"\s{2,}", line)  # 2 или более пробела
        if len(parts) > 1:
            return parts

        # Если ничего не помогло, разбиваем по первому пробелу
        return line.split(None, 1)

    def read_file(
        self, file_path: Path, lines: int = 0, minutes: int = 0
    ) -> Iterator[LogEvent]:
        """
        Читает события из файла лога.

        Args:
            file_path: Путь к файлу лога
            lines: Читать последние N строк (0 — все)
            minutes: Читать события за последние N минут (0 — все)

        Yields:
            LogEvent объекты
        """
        if not file_path.exists():
            return

        # Определяем cutoff время для фильтрации по минутам
        cutoff_time = None
        if minutes > 0:
            from datetime import timedelta

            cutoff_time = datetime.now() - timedelta(minutes=minutes)

        # Читаем файл
        with file_path.open("r", encoding="utf-8", errors="replace") as f:
            if lines > 0:
                # Читаем последние N строк
                all_lines = f.readlines()
                target_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            else:
                # Читаем все строки
                target_lines = f.readlines()

            for line in target_lines:
                event = self._parse_line(line)
                if event:
                    # Фильтруем по времени, если указано
                    if cutoff_time and event.timestamp < cutoff_time:
                        continue
                    yield event

    def read_events(
        self,
        event_types: list[str] | None = None,
        lines: int = 0,
        minutes: int = 0,
    ) -> Iterator[LogEvent]:
        """
        Читает события из всех файлов в директории логов.

        Args:
            event_types: Список типов событий для фильтрации (None — все)
            lines: Читать последние N строк из каждого файла (0 — все)
            minutes: Читать события за последние N минут (0 — все)

        Yields:
            LogEvent объекты
        """
        # Получаем все файлы логов, сортируем по имени (новые последние)
        log_files = sorted(self.log_dir.glob("*.log"))

        for log_file in log_files:
            for event in self.read_file(log_file, lines=lines, minutes=minutes):
                # Фильтруем по типу события
                if event_types is None or event.event_type in event_types:
                    yield event

    def count_events(
        self,
        event_types: list[str] | None = None,
        minutes: int = 0,
    ) -> int:
        """
        Подсчитывает количество событий.

        Args:
            event_types: Список типов событий для фильтрации
            minutes: Считать события за последние N минут (0 — все)

        Returns:
            Количество событий
        """
        return sum(
            1 for _ in self.read_events(event_types=event_types, minutes=minutes)
        )

    def get_latest_events(
        self,
        count: int = 10,
        event_types: list[str] | None = None,
        minutes: int = 0,
    ) -> list[LogEvent]:
        """
        Получает последние N событий.

        Args:
            count: Количество событий
            event_types: Список типов событий для фильтрации
            minutes: Получать события за последние N минут

        Returns:
            Список LogEvent объектов
        """
        events = list(self.read_events(event_types=event_types, minutes=minutes))
        return events[-count:] if len(events) > count else events

    def get_events_by_context(
        self,
        context: str,
        minutes: int = 0,
    ) -> list[LogEvent]:
        """
        Получает события по контексту.

        Args:
            context: Строка контекста для поиска
            minutes: Получать события за последние N минут

        Returns:
            Список LogEvent объектов
        """
        events = []
        for event in self.read_events(minutes=minutes):
            if context.lower() in event.properties.get("context", "").lower():
                events.append(event)
        return events

    def get_duration_stats(
        self,
        event_types: list[str] | None = None,
        minutes: int = 0,
    ) -> dict:
        """
        Получает статистику по длительности событий.

        Args:
            event_types: Список типов событий
            minutes: Период анализа

        Returns:
            Статистика: count, min, max, avg, total
        """
        durations = []

        for event in self.read_events(event_types=event_types, minutes=minutes):
            # Пробуем получить длительность из разных свойств
            duration = None

            # duration (мс)
            if "duration" in event.properties:
                try:
                    duration = int(event.properties["duration"])
                except ValueError:
                    pass

            # Durationus (мкс)
            if duration is None and "Durationus" in event.properties:
                try:
                    duration = int(event.properties["Durationus"]) / 1000  # мкс → мс
                except ValueError:
                    pass

            # Duration (мкс для SQL)
            if duration is None and "Duration" in event.properties:
                try:
                    duration = int(event.properties["Duration"]) / 1000  # мкс → мс
                except ValueError:
                    pass

            # cputime (мс)
            if duration is None and "cputime" in event.properties:
                try:
                    duration = int(event.properties["cputime"])
                except ValueError:
                    pass

            if duration is not None:
                durations.append(duration)

        if not durations:
            return {
                "count": 0,
                "min": 0,
                "max": 0,
                "avg": 0,
                "total": 0,
            }

        return {
            "count": len(durations),
            "min": min(durations),
            "max": max(durations),
            "avg": sum(durations) / len(durations),
            "total": sum(durations),
        }
