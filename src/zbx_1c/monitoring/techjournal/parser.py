"""Парсер логов техжурнала 1С"""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator


@dataclass
class LogEntry:
    """Запись лога техжурнала"""

    timestamp: datetime
    process_name: str
    user: str
    event_name: str
    description: str = ""
    context: str = ""
    duration: int = 0  # в мкс или мс
    connect_id: str = ""
    regions: str = ""
    locks_count: int = 0
    sql_text: str = ""
    module: str = ""
    method: str = ""
    computer: str = ""

    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "process_name": self.process_name,
            "user": self.user,
            "event_name": self.event_name,
            "description": self.description,
            "context": self.context,
            "duration": self.duration,
            "connect_id": self.connect_id,
            "regions": self.regions,
            "locks_count": self.locks_count,
            "sql_text": self.sql_text,
            "module": self.module,
            "method": self.method,
            "computer": self.computer,
        }


class TechJournalParser:
    """
    Парсер файлов техжурнала 1С.

    Поддерживает два формата:
    1. Полный: {1CV8C.12345}  2024-01-15 10:30:00.123+0300  EXCP  User1  ...
    2. Краткий: MM:SS.микросекунды-соединение,ТИП,уровень,p:processName=...,t:computerName=...
    """

    # Регулярное выражение для разбора строки лога (полный формат)
    LOG_PATTERN = re.compile(
        r"^\{(?P<process>[^}]+)\}\s+"  # {process.pid}
        r"(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+[+-]\d{4})\s+"  # timestamp
        r"(?P<event>\w+)\s+"  # event name
        r"(?P<user>\S+)\s*"  # user
        r"(?P<rest>.*)$",  # остальное
        re.UNICODE,
    )

    # Паттерн для краткого формата (MM:SS.микросекунды-соединение,ТИП,уровень,...)
    SHORT_LOG_PATTERN = re.compile(
        r"^(?P<time>\d{2}:\d{2}\.\d+)-(?P<conn>\d+),(?P<event>\w+),(?P<level>\d+),"  # время, соединение, тип, уровень
        r"(?P<rest>.*)$",  # остальное
        re.UNICODE,
    )

    # Паттерны для извлечения полей из rest
    FIELD_PATTERNS = {
        "descr": re.compile(r"(?:^|\s)Descr=(?P<value>.*?)(?:\s+\w+=|$)", re.UNICODE),
        "context": re.compile(r"(?:^|\s)Context=(?P<value>.*?)(?:\s+\w+=|$)", re.UNICODE),
        "duration": re.compile(r"(?:^|\s)duration=(?P<value>\d+)", re.UNICODE),
        "Duration": re.compile(r"(?:^|\s)Duration=(?P<value>\d+)", re.UNICODE),
        "Durationus": re.compile(r"(?:^|\s)Durationus=(?P<value>\d+)", re.UNICODE),
        "connectID": re.compile(r"(?:^|\s)connectID=(?P<value>\S+)", re.UNICODE),
        "regions": re.compile(r"(?:^|\s)regions=(?P<value>.*?)(?:\s+\w+=|$)", re.UNICODE),
        "locks": re.compile(r"(?:^|\s)locks=(?P<value>\d+)", re.UNICODE),
        "Sql": re.compile(r"(?:^|\s)Sql=(?P<value>.*?)(?:\s+\w+=|$)", re.UNICODE),
        "module": re.compile(r"(?:^|\s)module=(?P<value>.*?)(?:\s+\w+=|$)", re.UNICODE),
        "method": re.compile(r"(?:^|\s)method=(?P<value>.*?)(?:\s+\w+=|$)", re.UNICODE),
        "computer": re.compile(r"(?:^|\s)computer=(?P<value>\S+)", re.UNICODE),
        "processName": re.compile(r"(?:^|\s)p:processName=(?P<value>[^,]+)", re.UNICODE),
    }

    def __init__(self, log_dir: str | Path):
        """
        Инициализация парсера.

        Args:
            log_dir: Директория с логами техжурнала
        """
        self.log_dir = Path(log_dir)

    def find_log_files(self, pattern: str = "*.log", recursive: bool = True) -> list[Path]:
        """
        Поиск файлов логов по маске.

        Args:
            pattern: Маска файлов (по умолчанию *.log)
            recursive: Искать рекурсивно во всех поддиректориях

        Returns:
            Список путей к файлам логов
        """
        if not self.log_dir.exists():
            return []
        
        if recursive:
            # Рекурсивный поиск во всех поддиректориях
            return sorted(self.log_dir.rglob(pattern))
        else:
            # Поиск только в текущей директории
            return sorted(self.log_dir.glob(pattern))

    def parse_file(self, file_path: Path) -> Iterator[LogEntry]:
        """
        Парсинг одного файла лога.

        Args:
            file_path: Путь к файлу лога

        Yields:
            Записи лога
        """
        try:
            # Извлекаем дату из имени файла (формат: 26022710.log -> 2026-02-27)
            file_date = self._extract_date_from_filename(file_path)

            # Пробуем разные кодировки
            encodings = ["utf-8", "cp1251", "cp866", "utf-16"]

            for encoding in encodings:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        for line_num, line in enumerate(f, 1):
                            entry = self.parse_line(line.strip(), line_num, file_date)
                            if entry:
                                yield entry
                    break  # Успешно прочитали
                except UnicodeDecodeError:
                    continue
            else:
                # Ни одна кодировка не подошла
                pass

        except (IOError, OSError) as e:
            raise RuntimeError(f"Ошибка чтения файла {file_path}: {e}") from e

    def _extract_date_from_filename(self, file_path: Path) -> datetime:
        """
        Извлечение даты из имени файла.

        Формат имени: 26022710.log -> YYMMDDHH (год, месяц, день, час)
        """
        name = file_path.stem  # имя без расширения
        try:
            # Пробуем формат YYMMDDHH
            if len(name) >= 8:
                year = 2000 + int(name[0:2])
                month = int(name[2:4])
                day = int(name[4:6])
                hour = int(name[6:8])
                return datetime(year, month, day, hour, 0, 0)
            elif len(name) >= 6:
                year = 2000 + int(name[0:2])
                month = int(name[2:4])
                day = int(name[4:6])
                return datetime(year, month, day)
        except (ValueError, IndexError):
            pass
        return datetime.now()

    def parse_line(self, line: str, line_num: int = 0, file_date: datetime | None = None) -> LogEntry | None:
        """
        Разбор одной строки лога.

        Args:
            line: Строка лога
            line_num: Номер строки (для отладки)
            file_date: Дата из имени файла (для краткого формата)

        Returns:
            LogEntry или None если строка не распознана
        """
        if not line:
            return None

        # Пробуем полный формат
        match = self.LOG_PATTERN.match(line)
        if match:
            try:
                timestamp_str = match.group("timestamp")
                timestamp = self._parse_timestamp(timestamp_str)
                rest = match.group("rest")
                fields = self._parse_fields(rest)

                return LogEntry(
                    timestamp=timestamp,
                    process_name=match.group("process"),
                    user=match.group("user"),
                    event_name=match.group("event"),
                    description=fields.get("descr", ""),
                    context=fields.get("context", ""),
                    duration=self._parse_duration(fields),
                    connect_id=fields.get("connectID", ""),
                    regions=fields.get("regions", ""),
                    locks_count=int(fields.get("locks", 0)),
                    sql_text=fields.get("Sql", ""),
                    module=fields.get("module", ""),
                    method=fields.get("method", ""),
                    computer=fields.get("computer", ""),
                )
            except (ValueError, IndexError) as e:
                return None

        # Пробуем краткий формат
        match = self.SHORT_LOG_PATTERN.match(line)
        if match:
            try:
                time_str = match.group("time")
                event = match.group("event")
                rest = match.group("rest")
                fields = self._parse_fields(rest)

                # Используем дату из имени файла или сегодня
                if file_date is None:
                    file_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

                # Парсим время MM:SS.микросекунды
                timestamp = self._parse_short_timestamp(time_str, file_date)

                return LogEntry(
                    timestamp=timestamp,
                    process_name=fields.get("processName", ""),
                    user="",
                    event_name=event,
                    description=fields.get("descr", ""),
                    context=fields.get("context", ""),
                    duration=self._parse_duration(fields),
                    connect_id=match.group("conn"),
                    regions=fields.get("regions", ""),
                    locks_count=int(fields.get("locks", 0)),
                    sql_text=fields.get("Sql", ""),
                    module=fields.get("module", ""),
                    method=fields.get("method", ""),
                    computer=fields.get("computer", ""),
                )
            except (ValueError, IndexError) as e:
                return None

        return None

    def _parse_short_timestamp(self, time_str: str, base_date: datetime) -> datetime:
        """
        Парсинг краткого времени в формате MM:SS.микросекунды.

        Args:
            time_str: Время в формате MM:SS.микросекунды
            base_date: Базовая дата (с установленным часом из имени файла)

        Returns:
            datetime с подставленной датой и временем
        """
        # Парсим MM:SS.микросекунды
        match = re.match(r"(\d{2}):(\d{2})\.(\d+)", time_str)
        if not match:
            return base_date

        minutes = int(match.group(1))
        seconds = int(match.group(2))
        microseconds = int(match.group(3)[:6])  # Обрезаем до 6 знаков

        # Добавляем минуты и секунды к базовой дате
        from datetime import timedelta
        result = base_date + timedelta(minutes=minutes, seconds=seconds, microseconds=microseconds)
        return result

    def _parse_fields(self, rest: str) -> dict[str, str]:
        """
        Извлечение полей из rest части строки.

        Args:
            rest: Остаток строки после основных полей

        Returns:
            Словарь с полями
        """
        fields = {}

        for field_name, pattern in self.FIELD_PATTERNS.items():
            match = pattern.search(rest)
            if match:
                fields[field_name] = match.group("value").strip()

        return fields

    def _parse_duration(self, fields: dict[str, str]) -> int:
        """
        Парсинг длительности из различных полей.

        Приоритет: Durationus > Duration > duration
        """
        for field in ["Durationus", "Duration", "duration"]:
            if field in fields:
                try:
                    return int(fields[field])
                except ValueError:
                    pass
        return 0

    def parse_directory(
        self,
        pattern: str = "*.log",
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> Iterator[LogEntry]:
        """
        Парсинг всех файлов в директории.

        Args:
            pattern: Маска файлов
            from_time: Начальное время фильтрации
            to_time: Конечное время фильтрации

        Yields:
            Записи лога
        """
        for log_file in self.find_log_files(pattern):
            for entry in self.parse_file(log_file):
                # Фильтрация по времени
                if from_time and entry.timestamp < from_time:
                    continue
                if to_time and entry.timestamp > to_time:
                    continue
                yield entry
