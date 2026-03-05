"""
Парсер логов техжурнала 1С.

Формат файлов техжурнала:
<datetime> <level> <event-name> <process-name> <computer> <user> <description>
"""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Generator, List, Optional


@dataclass
class LogEntry:
    """Запись лога техжурнала"""

    timestamp: datetime
    event_name: str
    process_name: Optional[str] = None
    computer_name: Optional[str] = None
    user: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None  # в мкс
    context: Optional[str] = None

    @classmethod
    def from_line(cls, line: str) -> Optional["LogEntry"]:
        """
        Создать запись из строки лога.

        Формат строки:
        2024-01-15 10:30:00.123+0300 EXCP process-name computer user description

        Args:
            line: Строка лога.

        Returns:
            LogEntry или None если строка не распознана.
        """
        line = line.strip()
        if not line:
            return None

        # Паттерн для парсинга: дата время уровень процесс компьютер пользователь описание
        pattern = r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{4})?)\s+(\w+)\s+(.+)$"
        match = re.match(pattern, line)

        if not match:
            return None

        timestamp_str = match.group(1)
        event_name = match.group(2)
        rest = match.group(3)

        # Парсим timestamp
        try:
            # Пробуем с timezone
            if "+" in timestamp_str or timestamp_str.count("-") > 2:
                # Есть timezone
                timestamp = cls._parse_timestamp_with_tz(timestamp_str)
            else:
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None

        # Парсим остальную часть (процесс, компьютер, пользователь, описание)
        parts = rest.split(None, 3)

        process_name = parts[0] if len(parts) > 0 else None
        computer_name = parts[1] if len(parts) > 1 else None
        user = parts[2] if len(parts) > 2 else None
        description = parts[3] if len(parts) > 3 else None

        # Извлекаем длительность из описания если есть
        duration = None
        if description:
            duration_match = re.search(r"Duration[:\s]+(\d+)", description, re.IGNORECASE)
            if duration_match:
                duration = int(duration_match.group(1))

        return cls(
            timestamp=timestamp,
            event_name=event_name,
            process_name=process_name,
            computer_name=computer_name,
            user=user,
            description=description,
            duration=duration,
        )

    @staticmethod
    def _parse_timestamp_with_tz(ts: str) -> datetime:
        """Парсинг timestamp с timezone"""
        # Удаляем timezone для простоты
        ts_clean = re.sub(r"[+-]\d{4}$", "", ts)
        try:
            return datetime.strptime(ts_clean, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            return datetime.strptime(ts_clean, "%Y-%m-%d %H:%M:%S")


class TechJournalParser:
    """
    Парсер файлов техжурнала 1С.

    Args:
        log_dir: Директория с логами техжурнала.
    """

    def __init__(self, log_dir: str | Path):
        self.log_dir = Path(log_dir)

    def parse_file(self, file_path: Path) -> Generator[LogEntry, None, None]:
        """
        Парсинг одного файла лога.

        Args:
            file_path: Путь к файлу лога.

        Yields:
            LogEntry для каждой записи.
        """
        if not file_path.exists():
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    entry = LogEntry.from_line(line)
                    if entry:
                        yield entry
        except UnicodeDecodeError:
            # Пробуем другую кодировку
            try:
                with open(file_path, "r", encoding="cp1251") as f:
                    for line in f:
                        entry = LogEntry.from_line(line)
                        if entry:
                            yield entry
            except Exception:
                pass
        except Exception:
            pass

    def parse_directory(
        self,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
    ) -> Generator[LogEntry, None, None]:
        """
        Парсинг всех файлов в директории.

        Args:
            from_time: Фильтр по времени (начало).
            to_time: Фильтр по времени (конец).

        Yields:
            LogEntry для каждой записи.
        """
        if not self.log_dir.exists():
            return

        # Получаем все .log файлы
        log_files = sorted(self.log_dir.glob("*.log"), key=lambda f: f.stat().st_mtime)

        for log_file in log_files:
            for entry in self.parse_file(log_file):
                # Фильтрация по времени
                if from_time and entry.timestamp < from_time:
                    continue
                if to_time and entry.timestamp > to_time:
                    continue

                yield entry
