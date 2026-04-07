"""
Парсер логов техжурнала 1С.

Поддерживаемые форматы:
- 1c-techjournal-standard: 2024-01-15 10:30:00.123+0300 EXCP process-name computer user description
- 1c-techjournal-short: 15.01.2024 10:30:00 EXCP process-name computer user description
- iso8601: 2024-01-15T10:30:00.123Z EXCP ...
- 1c-csv: 50:30.440005-0,EXCP,2,Descr="..."
"""

import re
import os
import ctypes
import ctypes.wintypes
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Generator, List, Optional, Set


def _find_files_recursive(base_path: Path, pattern: str = "*.log") -> List[Path]:
    """
    Рекурсивный поиск файлов с использованием Windows API.
    Обходит блокировки 1С через FindFirstFile/FindNextFile.
    """
    result = []

    # Буфер для пути (MAX_PATH = 260)
    path_buffer = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
    ctypes.windll.kernel32.GetFullPathNameW(
        str(base_path), ctypes.wintypes.MAX_PATH, path_buffer, None
    )

    # Поиск файлов в текущей директории
    search_pattern = str(base_path / pattern)
    find_data = ctypes.wintypes.WIN32_FIND_DATAW()

    handle = ctypes.windll.kernel32.FindFirstFileW(search_pattern, ctypes.byref(find_data))
    if handle != -1 and handle != -2:  # INVALID_HANDLE_VALUE
        try:
            while True:
                file_name = find_data.cFileName
                if file_name and file_name not in (".", ".."):
                    file_path = base_path / file_name
                    # Проверяем, не директория ли это
                    if not (find_data.dwFileAttributes & 0x10):  # FILE_ATTRIBUTE_DIRECTORY = 0x10
                        result.append(file_path)

                if not ctypes.windll.kernel32.FindNextFileW(handle, ctypes.byref(find_data)):
                    break
        finally:
            ctypes.windll.kernel32.FindClose(handle)

    # Рекурсивный обход поддиректорий
    dir_pattern = str(base_path / "*")
    handle = ctypes.windll.kernel32.FindFirstFileW(dir_pattern, ctypes.byref(find_data))
    if handle != -1 and handle != -2:
        try:
            while True:
                dir_name = find_data.cFileName
                if dir_name and dir_name not in (".", ".."):
                    # Проверяем, директория ли это
                    if find_data.dwFileAttributes & 0x10:  # FILE_ATTRIBUTE_DIRECTORY
                        sub_dir = base_path / dir_name
                        try:
                            result.extend(_find_files_recursive(sub_dir, pattern))
                        except (OSError, PermissionError):
                            pass

                if not ctypes.windll.kernel32.FindNextFileW(handle, ctypes.byref(find_data)):
                    break
        finally:
            ctypes.windll.kernel32.FindClose(handle)

    return result


def _open_file_shared(file_path: Path, encoding: str = "utf-8"):
    """
    Открыть файл с共享 доступом (как Блокнот).

    Windows блокирует файлы, открытые 1С. Используем CreateFile с FILE_SHARE_READ | FILE_SHARE_WRITE.
    """
    # Windows API константы
    GENERIC_READ = 0x80000000
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    OPEN_EXISTING = 3

    # Открываем файл с共享 доступом
    handle = ctypes.windll.kernel32.CreateFileW(
        str(file_path),
        GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        0,
        None,
    )

    if handle == -1 or handle == ctypes.c_void_p(0):
        raise IOError(f"Не удалось открыть файл: {file_path}")

    try:
        # Получаем размер файла
        file_size = ctypes.windll.kernel32.GetFileSize(handle, None)

        # Читаем всё содержимое
        buffer = ctypes.create_string_buffer(file_size)
        bytes_read = ctypes.c_ulong(0)
        ctypes.windll.kernel32.ReadFile(handle, buffer, file_size, ctypes.byref(bytes_read), None)

        # Декодируем в строку
        content = buffer.raw[: bytes_read.value].decode(encoding, errors="replace")
        return content.splitlines()
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


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
    format: str = "unknown"  # Формат лога
    source_file: Optional[str] = None  # Исходный файл

    @classmethod
    def from_line(
        cls,
        line: str,
        source_file: Optional[str] = None,
        base_date: Optional[datetime] = None,
        file_mtime: Optional[float] = None,
    ) -> Optional["LogEntry"]:
        """
        Создать запись из строки лога.

        Args:
            line: Строка лога.
            source_file: Путь к исходному файлу.
            base_date: Базовая дата для форматов без даты.
            file_mtime: Время модификации файла (timestamp).

        Returns:
            LogEntry или None если строка не распознана.
        """
        line = line.strip()
        if not line:
            return None

        # Определяем формат и парсим
        result = (
            cls._parse_standard(line, base_date)
            or cls._parse_short(line, base_date)
            or cls._parse_iso8601(line, base_date)
            or cls._parse_csv_format(line, source_file, base_date, file_mtime)
        )

        if result:
            result.source_file = source_file

        return result

    @classmethod
    def _parse_standard(
        cls, line: str, base_date: Optional[datetime] = None
    ) -> Optional["LogEntry"]:
        """
        Парсинг формата: 2024-01-15 10:30:00.123+0300 EXCP process-name ...

        Returns:
            LogEntry или None.
        """
        pattern = (
            r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{4})?)\s+(\w+)\s+(.+)$"
        )
        match = re.match(pattern, line)

        if not match:
            return None

        timestamp_str = match.group(1)
        event_name = match.group(2)
        rest = match.group(3)

        timestamp = cls._parse_timestamp(timestamp_str)
        if not timestamp:
            return None

        parts = rest.split(None, 3)
        process_name = parts[0] if len(parts) > 0 else None
        computer_name = parts[1] if len(parts) > 1 else None
        user = parts[2] if len(parts) > 2 else None
        description = parts[3] if len(parts) > 3 else None

        duration = cls._extract_duration(description)

        return cls(
            timestamp=timestamp,
            event_name=event_name,
            process_name=process_name,
            computer_name=computer_name,
            user=user,
            description=description,
            duration=duration,
            format="1c-techjournal-standard",
        )

    @classmethod
    def _parse_short(cls, line: str, base_date: Optional[datetime] = None) -> Optional["LogEntry"]:
        """
        Парсинг формата: 15.01.2024 10:30:00 EXCP process-name ...

        Returns:
            LogEntry или None.
        """
        pattern = r"^(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2})\s+(\w+)\s+(.+)$"
        match = re.match(pattern, line)

        if not match:
            return None

        timestamp_str = match.group(1)
        event_name = match.group(2)
        rest = match.group(3)

        try:
            timestamp = datetime.strptime(timestamp_str, "%d.%m.%Y %H:%M:%S")
        except ValueError:
            return None

        parts = rest.split(None, 3)
        process_name = parts[0] if len(parts) > 0 else None
        computer_name = parts[1] if len(parts) > 1 else None
        user = parts[2] if len(parts) > 2 else None
        description = parts[3] if len(parts) > 3 else None

        duration = cls._extract_duration(description)

        return cls(
            timestamp=timestamp,
            event_name=event_name,
            process_name=process_name,
            computer_name=computer_name,
            user=user,
            description=description,
            duration=duration,
            format="1c-techjournal-short",
        )

    @classmethod
    def _parse_iso8601(
        cls, line: str, base_date: Optional[datetime] = None
    ) -> Optional["LogEntry"]:
        """
        Парсинг формата: 2024-01-15T10:30:00.123Z EXCP ...

        Returns:
            LogEntry или None.
        """
        pattern = r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+(\w+)\s+(.+)$"
        match = re.match(pattern, line)

        if not match:
            return None

        timestamp_str = match.group(1)
        event_name = match.group(2)
        rest = match.group(3)

        # Упрощаем парсинг ISO8601
        ts_clean = timestamp_str.replace("Z", "").replace("T", " ")
        ts_clean = re.sub(r"[+-]\d{2}:?\d{2}$", "", ts_clean)

        try:
            timestamp = datetime.strptime(ts_clean, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            try:
                timestamp = datetime.strptime(ts_clean, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None

        parts = rest.split(None, 3)
        process_name = parts[0] if len(parts) > 0 else None
        computer_name = parts[1] if len(parts) > 1 else None
        user = parts[2] if len(parts) > 2 else None
        description = parts[3] if len(parts) > 3 else None

        duration = cls._extract_duration(description)

        return cls(
            timestamp=timestamp,
            event_name=event_name,
            process_name=process_name,
            computer_name=computer_name,
            user=user,
            description=description,
            duration=duration,
            format="iso8601",
        )

    @classmethod
    def _parse_csv_format(
        cls,
        line: str,
        source_file: Optional[str],
        base_date: Optional[datetime] = None,
        file_mtime: Optional[float] = None,
    ) -> Optional["LogEntry"]:
        """
        Парсинг формата 1С CSV: HH:MM:SS.ffffff-N,CALL,flag,key=value,...

        Пример: 00:00.035002-1,CALL,1,p:processName=DebugQueryTargets,...

        Args:
            line: Строка лога.
            source_file: Путь к файлу (для извлечения даты).
            base_date: Базовая дата.
            file_mtime: Время модификации файла (timestamp).

        Returns:
            LogEntry или None.
        """
        # Формат: время,событие,флаг,параметры
        parts = line.split(",", 3)
        if len(parts) < 3:
            return None

        time_str = parts[0]
        event_name = parts[1]

        # Парсим время (HH:MM:SS.ffffff или HH:MM:SS.ffffff-N или MM:SS.ffffff-N)
        time_match = re.match(r"(\d{1,2}:\d{2}(?:\.\d+)?)(?:-\d+)?", time_str)
        if not time_match:
            return None

        time_only = time_match.group(1)

        # Определяем дату из имени файла (приоритет) или из времени модификации
        log_date = base_date
        if source_file:
            # Извлекаем дату из имени файла (формат: ГГММДДЧЧ.log или 26032222.log)
            file_name = Path(source_file).name
            date_match = re.match(r"(\d{2})(\d{2})(\d{2})(\d{2})\.log$", file_name)
            if date_match:
                year, month, day, hour = date_match.groups()
                # 26032222.log -> 2026-03-22 (ГГ=26, ММ=03, ДД=22 -> 2026-03-22)
                try:
                    log_date = datetime(2000 + int(year), int(month), int(day))
                except ValueError:
                    log_date = None

        # Fallback: если не удалось извлечь из имени файла, используем mtime
        if log_date is None and file_mtime is not None:
            log_date = datetime.fromtimestamp(file_mtime)

        if not log_date:
            log_date = datetime.now()

        # Извлекаем час из имени файла (формат ГГММДДЧЧ.log)
        file_hour = None
        if source_file:
            file_name = Path(source_file).name
            date_match = re.match(r"(\d{2})(\d{2})(\d{2})(\d{2})\.log$", file_name)
            if date_match:
                try:
                    file_hour = int(date_match.group(4))
                except ValueError:
                    pass

        # Парсим время (MM:SS.ffffff или HH:MM:SS.ffffff)
        try:
            if time_only.count(":") == 2:
                # HH:MM:SS.ffffff - используем как есть
                if "." in time_only:
                    time_obj = datetime.strptime(time_only, "%H:%M:%S.%f")
                else:
                    time_obj = datetime.strptime(time_only, "%H:%M:%S")
            else:
                # MM:SS.ffffff - используем час из имени файла или 00
                hour_to_use = file_hour if file_hour is not None else 0
                if "." in time_only:
                    time_obj = datetime.strptime(time_only, "%M:%S.%f")
                    time_obj = time_obj.replace(hour=hour_to_use)
                else:
                    time_obj = datetime.strptime(time_only, "%M:%S")
                    time_obj = time_obj.replace(hour=hour_to_use)

            timestamp = log_date.replace(
                hour=time_obj.hour,
                minute=time_obj.minute,
                second=time_obj.second,
                microsecond=time_obj.microsecond if hasattr(time_obj, "microsecond") else 0,
            )
        except ValueError:
            return None

        # Парсим параметры (key=value)
        params_str = parts[3] if len(parts) > 3 else ""
        params = {}
        for param in params_str.split(","):
            if "=" in param:
                key, value = param.split("=", 1)
                params[key.strip()] = value.strip()

        # Извлекаем известные поля
        process_name = params.get("p:processName")
        computer_name = params.get("t:computerName")
        user = params.get("t:Usr")
        description = params.get("Descr") or params.get("descr")

        # Длительность
        duration = None
        if "Duration" in params:
            try:
                duration = int(params["Duration"])
            except ValueError:
                pass

        return cls(
            timestamp=timestamp,
            event_name=event_name,
            process_name=process_name,
            computer_name=computer_name,
            user=user,
            description=description,
            duration=duration,
            format="1c-csv",
        )

    @staticmethod
    def _parse_timestamp(ts: str) -> Optional[datetime]:
        """Парсинг timestamp с различными форматами"""
        formats = [
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
        ]

        # Удаляем timezone
        ts_clean = re.sub(r"[+-]\d{4}$", "", ts)

        for fmt in formats:
            try:
                return datetime.strptime(ts_clean, fmt)
            except ValueError:
                continue

        return None

    @staticmethod
    def _extract_duration(description: Optional[str]) -> Optional[int]:
        """Извлечь длительность из описания (в мкс)"""
        if not description:
            return None

        patterns = [
            r"Duration[:\s]+(\d+)",
            r"Длительность[:\s]+(\d+)",
            r"(\d+)\s*мкс",
            r"(\d+)\s*us\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None


@dataclass
class ParserStats:
    """Статистика парсинга"""

    total_lines: int = 0
    parsed_lines: int = 0
    failed_lines: int = 0
    formats: Set[str] = field(default_factory=set)
    event_types: Set[str] = field(default_factory=set)

    def add_entry(self, entry: LogEntry) -> None:
        """Добавить запись в статистику"""
        self.parsed_lines += 1
        self.formats.add(entry.format)
        self.event_types.add(entry.event_name)

    def add_failed(self) -> None:
        """Добавить неудачную попытку парсинга"""
        self.failed_lines += 1


class TechJournalParser:
    """
    Парсер файлов техжурнала 1С.

    Автоматически определяет формат логов и парсит их.

    Args:
        log_dir: Директория с логами техжурнала.
    """

    def __init__(self, log_dir: str | Path):
        self.log_dir = Path(log_dir)
        self.stats = ParserStats()

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

        # Получаем время модификации файла для корректного определения даты
        file_mtime = file_path.stat().st_mtime

        # Пытаемся открыть файл с共享 доступом (как Блокнот)
        try:
            lines = _open_file_shared(file_path, encoding="cp1251")
            for line in lines:
                self.stats.total_lines += 1
                entry = LogEntry.from_line(line, source_file=str(file_path), file_mtime=file_mtime)
                if entry:
                    self.stats.add_entry(entry)
                    yield entry
                else:
                    self.stats.add_failed()
            return
        except (IOError, OSError, PermissionError):
            # Fallback на стандартное открытие с перебором кодировок
            encodings = ["utf-8", "cp1251", "cp866", "latin-1"]
            for encoding in encodings:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        for line in f:
                            self.stats.total_lines += 1
                            entry = LogEntry.from_line(
                                line, source_file=str(file_path), file_mtime=file_mtime
                            )
                            if entry:
                                self.stats.add_entry(entry)
                                yield entry
                            else:
                                self.stats.add_failed()
                    return  # Успешно прочитали
                except UnicodeDecodeError:
                    continue
                except Exception:
                    break

    def parse_directory(
        self,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        recursive: bool = True,
        min_mtime: Optional[float] = None,
        limit_files: Optional[int] = None,
    ) -> Generator[LogEntry, None, None]:
        """
        Парсинг всех файлов в директории.

        Args:
            from_time: Фильтр по времени (начало).
            to_time: Фильтр по времени (конец).
            recursive: Рекурсивно обходить поддиректории.
            min_mtime: Минимальное время модификации файла (timestamp).
                       Файлы старше этого времени не читаются для оптимизации.
            limit_files: Ограничить количество читаемых файлов (последние по mtime).

        Yields:
            LogEntry для каждой записи.
        """
        if not self.log_dir.exists():
            return

        # Получаем все файлы логов с их mtime
        log_files_with_mtime = []

        # Используем Windows API для обхода заблокированных 1С директорий
        try:
            file_paths = _find_files_recursive(self.log_dir, "*.log")
        except Exception:
            # Fallback на pathlib если Windows API не работает
            if recursive:
                file_paths = list(self.log_dir.rglob("*.log"))
            else:
                file_paths = list(self.log_dir.glob("*.log"))

        for file_path in file_paths:
            if self._is_log_file(file_path):
                try:
                    mtime = file_path.stat().st_mtime
                    size = file_path.stat().st_size
                    # Пропускаем пустые файлы для оптимизации
                    if size > 0:
                        log_files_with_mtime.append((file_path, mtime))
                except (OSError, PermissionError):
                    continue

        # Фильтруем по времени модификации
        if min_mtime is not None:
            log_files_with_mtime = [(f, m) for f, m in log_files_with_mtime if m >= min_mtime]

        # Сортируем по времени модификации (новые первые)
        log_files_with_mtime.sort(key=lambda x: x[1], reverse=True)

        # Ограничиваем количество файлов для чтения
        if limit_files is not None:
            log_files_with_mtime = log_files_with_mtime[:limit_files]

        # Извлекаем только пути
        log_files = [f for f, m in log_files_with_mtime]

        for log_file in log_files:
            for entry in self.parse_file(log_file):
                # Фильтрация по времени
                if from_time and entry.timestamp < from_time:
                    continue
                if to_time and entry.timestamp > to_time:
                    continue

                yield entry

    def _is_log_file(self, file_path: Path) -> bool:
        """
        Проверить, является ли файл файлом лога техжурнала 1С.

        Args:
            file_path: Путь к файлу.

        Returns:
            True если файл является логом.
        """
        import re

        name = file_path.name

        # Файлы с расширением .log
        if file_path.suffix.lower() == ".log":
            return True

        # Файлы техжурнала 1С без расширения (1CV8C_24940, rac_1000, etc.)
        patterns = [
            r"^\d+[A-Z]*_\d+$",  # 1CV8C_24940, rac_1000
            r"^[A-Z]+_\d+$",  # RAGENT_7336, RMNGR_6884
            r"^\d{8}$",  # 20240115
            r"^1cv8.*",  # 1cv8_*
            r"^rac_.*",  # rac_*
            r"^rmngr_.*",  # rmngr_*
            r"^rphost_.*",  # rphost_*
            r"^ragent_.*",  # ragent_*
            r"^ras_.*",  # ras_*
        ]

        name_lower = name.lower()
        for pattern in patterns:
            if re.match(pattern, name_lower):
                return True

        return False

    def get_stats(self) -> ParserStats:
        """Получить статистику парсинга"""
        return self.stats
