"""
Парсер логов техжурнала 1С.

Поддерживаемые форматы:
- 1c-techjournal-standard: 2024-01-15 10:30:00.123+0300 EXCP process-name computer user description
- 1c-techjournal-short: 15.01.2024 10:30:00 EXCP process-name computer user description
- iso8601: 2024-01-15T10:30:00.123Z EXCP ...
- 1c-csv: 50:30.440005-0,EXCP,2,Descr="..."
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Generator, List, Optional, Set


def _find_files_recursive(base_path: Path, pattern: str = "*.log") -> List[Path]:
    """
    Рекурсивный поиск файлов с использованием pathlib.
    """
    try:
        return list(base_path.rglob(pattern))
    except (OSError, PermissionError):
        return []


def _open_file_shared(file_path: Path, encoding: str = "utf-8"):
    """
    Открыть файл с использованием стандартного открытия.
    """
    try:
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            return f.readlines()
    except (IOError, OSError, PermissionError) as e:
        raise IOError(f"Не удалось открыть файл: {file_path}: {e}")


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

    # Дополнительные поля из документации
    client_id: Optional[str] = None  # T:clientID — ID клиентского соединения
    application_name: Optional[str] = None  # T:applicationName — тип клиента
    connect_id: Optional[str] = None  # T:connectID — ID соединения с ИБ
    session_id: Optional[str] = None  # SessionID — GUID сеанса
    module: Optional[str] = None  # module — имя модуля
    method: Optional[str] = None  # method — имя метода
    regions: Optional[str] = None  # regions — области блокировок
    locks: Optional[str] = None  # locks — заблокированные ресурсы
    sql: Optional[str] = None  # sql — текст SQL-запроса
    rows: Optional[int] = None  # rows — кол-во строк результата
    rows_affected: Optional[int] = None  # rowsaffected — кол-во изменённых строк
    memory: Optional[int] = None  # Memory — потребление памяти в байтах (может быть отриц.)

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
            # Если computer_name пустой, пробуем извлечь из пути к файлу
            if not result.computer_name and source_file:
                result.computer_name = cls._extract_server_name_from_path(source_file)

        return result

    @staticmethod
    def _extract_server_name_from_path(file_path: str) -> Optional[str]:
        """
        Извлечь имя сервера из пути к файлу лога.

        Примеры путей:
        - /logs/srv-pinavto02/core/26032222.log -> srv-pinavto02
        - C:\\Logs\\1C\\srv-rdm01\\core\\... -> srv-rdm01
        - /logs/1c-techjournal/core/... -> None (нет имени сервера)

        Ищем паттерн: директория с именем вида srv-XXXX или хост в пути
        """
        import re

        # Ищем имя сервера в пути (srv-XXXX, host-XXXX, или просто хост)
        patterns = [
            r"[\\/](srv-[^\\/]+)[\\/]",  # srv-XXXX
            r"[\\/](host-[^\\/]+)[\\/]",  # host-XXXX
            r"[\\/](rdp[^\\/]+)[\\/]",  # rdpXXXX
        ]

        for pattern in patterns:
            match = re.search(pattern, file_path, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    @staticmethod
    def _extract_key_value_fields(params: dict) -> dict:
        """
        Извлечь все известные поля из словаря key=value.

        Args:
            params: Словарь параметров из строки лога.

        Returns:
            Словарь с известными полями LogEntry.
        """
        fields: dict = {}

        # Основные поля (без префиксов)
        fields["computer_name"] = params.get("computerName")
        fields["user"] = params.get("Usr")
        fields["description"] = params.get("Descr") or params.get("descr")
        fields["context"] = params.get("context") or params.get("Context")
        fields["duration"] = None
        fields["client_id"] = params.get("T:clientID")
        fields["application_name"] = params.get("T:applicationName")
        fields["connect_id"] = params.get("T:connectID")
        fields["session_id"] = params.get("SessionID")
        fields["module"] = params.get("module")
        fields["method"] = params.get("method")
        fields["regions"] = params.get("regions")
        fields["locks"] = params.get("locks")
        fields["sql"] = params.get("Sql") or params.get("sql")
        fields["rows"] = None
        fields["rows_affected"] = None
        fields["memory"] = None

        # processName — проверяем оба варианта
        fields["process_name"] = (
            params.get("p:processName") or params.get("t:processName") or params.get("processName")
        )

        # Длительность
        if "duration" in params:
            try:
                fields["duration"] = int(params["duration"])
            except ValueError:
                pass
        elif "Duration" in params:
            try:
                fields["duration"] = int(params["Duration"])
            except ValueError:
                pass

        # Числовые поля
        if "rows" in params:
            try:
                fields["rows"] = int(params["rows"])
            except ValueError:
                pass

        if "rowsaffected" in params:
            try:
                fields["rows_affected"] = int(params["rowsaffected"])
            except ValueError:
                pass

        # Memory — может быть отрицательным (освобождение памяти)
        if "Memory" in params:
            try:
                fields["memory"] = int(params["Memory"])
            except ValueError:
                pass

        return fields

    @classmethod
    def _parse_standard(
        cls, line: str, base_date: Optional[datetime] = None
    ) -> Optional["LogEntry"]:
        """
        Парсинг формата: 2024-01-15 10:30:00.123+0300 EXCP process-name ...
        Или: 2024-01-15 10:30:00.123+0300 EXCP,p:processName=korp,Usr=Иванов,...

        Returns:
            LogEntry или None.
        """
        pattern = r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{4})?)\s+(\w+)\s*,?\s*(.+)?$"
        match = re.match(pattern, line)

        if not match:
            return None

        timestamp_str = match.group(1)
        event_name = match.group(2)
        rest = match.group(3) or ""

        timestamp = cls._parse_timestamp(timestamp_str)
        if not timestamp:
            return None

        rest = rest.strip()
        if not rest:
            return cls(
                timestamp=timestamp,
                event_name=event_name,
                format="1c-techjournal-standard",
            )

        # Проверяем, key=value формат (через запятую)
        if "," in rest and "=" in rest:
            params = {}
            for param in rest.split(","):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key.strip()] = value.strip().strip("'\"")

            fields = cls._extract_key_value_fields(params)
            return cls(
                timestamp=timestamp,
                event_name=event_name,
                process_name=fields["process_name"],
                computer_name=fields["computer_name"],
                user=fields["user"],
                description=fields["description"],
                duration=fields["duration"],
                context=fields["context"],
                client_id=fields["client_id"],
                application_name=fields["application_name"],
                connect_id=fields["connect_id"],
                session_id=fields["session_id"],
                module=fields["module"],
                method=fields["method"],
                regions=fields["regions"],
                locks=fields["locks"],
                sql=fields["sql"],
                rows=fields["rows"],
                rows_affected=fields["rows_affected"],
                memory=fields["memory"],
                format="1c-techjournal-standard",
            )

        # Позиционный формат: process-name computer user description
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
        Или: 15.01.2024 10:30:00 EXCP,p:processName=korp,Usr=Иванов,...

        Returns:
            LogEntry или None.
        """
        pattern = r"^(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2})\s+(\w+)\s*,?\s*(.+)?$"
        match = re.match(pattern, line)

        if not match:
            return None

        timestamp_str = match.group(1)
        event_name = match.group(2)
        rest = match.group(3) or ""

        try:
            timestamp = datetime.strptime(timestamp_str, "%d.%m.%Y %H:%M:%S")
        except ValueError:
            return None

        rest = rest.strip()
        if not rest:
            return cls(
                timestamp=timestamp,
                event_name=event_name,
                format="1c-techjournal-short",
            )

        # Проверяем, key=value формат (через запятую)
        if "," in rest and "=" in rest:
            params = {}
            for param in rest.split(","):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key.strip()] = value.strip().strip("'\"")

            fields = cls._extract_key_value_fields(params)
            return cls(
                timestamp=timestamp,
                event_name=event_name,
                process_name=fields["process_name"],
                computer_name=fields["computer_name"],
                user=fields["user"],
                description=fields["description"],
                duration=fields["duration"],
                context=fields["context"],
                client_id=fields["client_id"],
                application_name=fields["application_name"],
                connect_id=fields["connect_id"],
                session_id=fields["session_id"],
                module=fields["module"],
                method=fields["method"],
                regions=fields["regions"],
                locks=fields["locks"],
                sql=fields["sql"],
                rows=fields["rows"],
                rows_affected=fields["rows_affected"],
                memory=fields["memory"],
                format="1c-techjournal-short",
            )

        # Позиционный формат: process-name computer user description
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
        Или: 2024-01-15T10:30:00.123Z EXCP,p:processName=korp,Usr=Иванов,...

        Returns:
            LogEntry или None.
        """
        pattern = r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+(\w+)\s*,?\s*(.+)?$"
        match = re.match(pattern, line)

        if not match:
            return None

        timestamp_str = match.group(1)
        event_name = match.group(2)
        rest = match.group(3) or ""

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

        rest = rest.strip()
        if not rest:
            return cls(
                timestamp=timestamp,
                event_name=event_name,
                format="iso8601",
            )

        # Проверяем, key=value формат (через запятую)
        if "," in rest and "=" in rest:
            params = {}
            for param in rest.split(","):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key.strip()] = value.strip().strip("'\"")

            fields = cls._extract_key_value_fields(params)
            return cls(
                timestamp=timestamp,
                event_name=event_name,
                process_name=fields["process_name"],
                computer_name=fields["computer_name"],
                user=fields["user"],
                description=fields["description"],
                duration=fields["duration"],
                context=fields["context"],
                client_id=fields["client_id"],
                application_name=fields["application_name"],
                connect_id=fields["connect_id"],
                session_id=fields["session_id"],
                module=fields["module"],
                method=fields["method"],
                regions=fields["regions"],
                locks=fields["locks"],
                sql=fields["sql"],
                rows=fields["rows"],
                rows_affected=fields["rows_affected"],
                memory=fields["memory"],
                format="iso8601",
            )

        # Позиционный формат: process-name computer user description
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

        # Извлекаем duration из CSV формата: HH:MM:SS.ffffff-N или MM:SS.ffffff-N
        # Число после дефиса — это длительность в микросекундах
        csv_duration = cls._extract_csv_duration(time_str)

        # Парсим параметры (key=value)
        params_str = parts[3] if len(parts) > 3 else ""
        params = {}
        for param in params_str.split(","):
            if "=" in param:
                key, value = param.split("=", 1)
                params[key.strip()] = value.strip().strip("'\"")

        # Используем универсальную функцию извлечения полей
        fields = cls._extract_key_value_fields(params)

        return cls(
            timestamp=timestamp,
            event_name=event_name,
            process_name=fields["process_name"],
            computer_name=fields["computer_name"],
            user=fields["user"],
            description=fields["description"],
            duration=fields["duration"] or csv_duration,
            context=fields["context"],
            client_id=fields["client_id"],
            application_name=fields["application_name"],
            connect_id=fields["connect_id"],
            session_id=fields["session_id"],
            module=fields["module"],
            method=fields["method"],
            regions=fields["regions"],
            locks=fields["locks"],
            sql=fields["sql"],
            rows=fields["rows"],
            rows_affected=fields["rows_affected"],
            memory=fields["memory"],
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
        """Извлечь длительность из описания (в мкс)

        1С записывает длительность в микросекундах (мкс).
        Примеры форматов:
        - Duration: 1250000
        - Длительность: 1250000
        - 1250000 мкс
        - 1250000us
        """
        if not description:
            return None

        patterns = [
            # Именованные паттерны (приоритет)
            r"Duration[:\s]+(\d+)",
            r"Длительность[:\s]+(\d+)",
            r"(\d+)\s*мкс",
            r"(\d+)\s*us\b",
            r"(\d+)\s*микросекунд",
            # Паттерн для SQL: большое число (>= 5 цифр) в контексте
            r"(?:^|[\s,;])(\d{5,})(?:\s|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                value = int(match.group(1))
                # Защита от неверных значений: если число слишком маленькое
                # для микросекунд (< 1000), это скорее всего не длительность
                if value >= 1000:
                    return value

        return None

    @staticmethod
    def _extract_csv_duration(time_str: str) -> Optional[int]:
        """Извлечь длительность из CSV формата времени: HH:MM:SS.ffffff-N

        Формат 1С CSV: время-длительность, где длительность в микросекундах.
        Примеры:
        - 00:01.365009-1 → 1 мкс
        - 00:00.035002-500000 → 500000 мкс = 500 мс
        - 50:30.440005-0 → 0 мкс

        Args:
            time_str: Строка времени из CSV лога.

        Returns:
            Длительность в микросекундах или None.
        """
        import re

        match = re.search(r"-(\d+)$", time_str)
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
        # Пробуем разные кодировки: UTF-8 -> CP1251 -> CP866
        encodings_shared = ["utf-8", "cp1251", "cp866"]
        for encoding in encodings_shared:
            try:
                lines = _open_file_shared(file_path, encoding=encoding)
                for line in lines:
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
            except (UnicodeDecodeError, UnicodeError):
                continue
            except (IOError, OSError, PermissionError):
                break

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
