"""
Автоматическое обнаружение структуры логов техжурнала 1С.

Пользователь указывает только базовый путь, а этот модуль сам находит:
- Поддиректории с логами (core, perf, locks, sql, zabbix и др.)
- Файлы логов (.log, .txt)
- Форматы логов (разные версии 1С)
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class LogDirectory:
    """Информация о найденной директории с логами"""

    path: Path
    log_type: str  # core, perf, locks, sql, zabbix, custom
    file_count: int = 0
    total_size_bytes: int = 0
    latest_mtime: float = 0
    files: List[Path] = field(default_factory=list)


@dataclass
class LogStructure:
    """Структура найденных логов"""

    base_path: Path
    directories: Dict[str, LogDirectory] = field(default_factory=dict)
    total_files: int = 0
    total_size_bytes: int = 0
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    detected_formats: Set[str] = field(default_factory=set)

    def add_directory(self, dir_info: LogDirectory) -> None:
        """Добавить директорию в структуру"""
        self.directories[dir_info.log_type] = dir_info
        self.total_files += dir_info.file_count
        self.total_size_bytes += dir_info.total_size_bytes

    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        return {
            "base_path": str(self.base_path),
            "directories": {
                name: {
                    "path": str(dir.path),
                    "log_type": dir.log_type,
                    "file_count": dir.file_count,
                    "total_size_mb": round(dir.total_size_bytes / 1024 / 1024, 2),
                    "latest_mtime": dir.latest_mtime,
                    "files": [str(f) for f in dir.files[:10]],  # Первые 10 файлов
                }
                for name, dir in self.directories.items()
            },
            "total_files": self.total_files,
            "total_size_mb": round(self.total_size_bytes / 1024 / 1024, 2),
            "date_range_start": self.date_range_start,
            "date_range_end": self.date_range_end,
            "detected_formats": list(self.detected_formats),
        }


class LogStructureDiscovery:
    """
    Обнаружение структуры логов техжурнала 1С.

    Автоматически находит:
    - Стандартные поддиректории (core, perf, locks, sql, zabbix)
    - Пользовательские поддиректории с .log файлами
    - Форматы логов (по первым строкам файлов)
    """

    # Стандартные имена поддиректорий техжурнала
    STANDARD_SUBDIRS = {
        "core": "Основные события",
        "perf": "Производительность",
        "locks": "Блокировки",
        "sql": "SQL запросы",
        "zabbix": "Zabbix события",
        "db": "События СУБД",
        "srvinfo": "Информация о сервере",
        "rphost": "Рабочие процессы",
        "cluster": "Кластер",
        "sessions": "Сеансы",
        "connections": "Соединения",
    }

    # Паттерны для определения типа лога по имени файла
    FILE_PATTERNS = {
        "core": [r".*\.log$", r"^[0-9]{8}\.log$"],
        "perf": [r".*perf.*\.log$", r"^[0-9]{8}_perf\.log$"],
        "locks": [r".*lock.*\.log$", r"^[0-9]{8}_locks?\.log$"],
        "sql": [r".*sql.*\.log$", r".*sdbl.*\.log$", r"^[0-9]{8}_sql\.log$"],
        "zabbix": [r".*zabbix.*\.log$"],
        "db": [r".*dbms.*\.log$", r".*mssql.*\.log$", r".*postgres.*\.log$"],
    }

    # Расширения файлов логов
    LOG_EXTENSIONS = {".log", ".txt", ".log.*", ""}  # Пустое расширение для файлов без расширения

    # Паттерны для файлов без расширения (1С техжурнал)
    LOG_NAME_PATTERNS = [
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

    def discover(self, base_path: Path) -> LogStructure:
        """
        Обнаружить структуру логов.

        Args:
            base_path: Базовый путь для поиска.

        Returns:
            LogStructure с найденными директориями и файлами.
        """
        structure = LogStructure(base_path=base_path)

        if not base_path.exists():
            return structure

        # 1. Ищем стандартные поддиректории
        for subdir_name in self.STANDARD_SUBDIRS:
            dir_path = base_path / subdir_name
            if dir_path.exists() and dir_path.is_dir():
                dir_info = self._scan_directory(dir_path, subdir_name)
                if dir_info.file_count > 0:
                    structure.add_directory(dir_info)

        # 2. Ищем другие поддиректории с .log файлами
        for child in base_path.iterdir():
            if child.is_dir() and child.name not in structure.directories:
                dir_info = self._scan_directory(child, child.name)
                if dir_info.file_count > 0:
                    structure.add_directory(dir_info)

        # 3. Ищем .log файлы в корневой директории (только в корне, без рекурсии)
        root_logs = self._scan_directory(base_path, "root", recursive=False)
        if root_logs.file_count > 0:
            structure.add_directory(root_logs)

        # 4. Определяем форматы логов
        self._detect_formats(structure)

        return structure

    def _scan_directory(
        self, dir_path: Path, log_type: str, recursive: bool = True
    ) -> LogDirectory:
        """
        Сканировать директорию на наличие файлов логов.

        Args:
            dir_path: Путь к директории.
            log_type: Тип логов.
            recursive: Рекурсивно обходить вложенные поддиректории.
                       Для корневой директории следует использовать False.

        Returns:
            LogDirectory с информацией о директории.
        """
        dir_info = LogDirectory(path=dir_path, log_type=log_type)

        try:
            # Ищем .log файлы (рекурсивно или только в корне)
            if recursive:
                log_files = dir_path.rglob("*.log")
            else:
                log_files = dir_path.glob("*.log")

            for file_path in log_files:
                # Пропускаем директории, проверяем только файлы
                if not file_path.is_file():
                    continue

                if self._is_log_file(file_path):
                    dir_info.files.append(file_path)
                    dir_info.file_count += 1

                    try:
                        stat = file_path.stat()
                        dir_info.total_size_bytes += stat.st_size
                        if stat.st_mtime > dir_info.latest_mtime:
                            dir_info.latest_mtime = stat.st_mtime
                    except Exception:
                        pass
        except PermissionError:
            pass
        except Exception:
            pass

        return dir_info

    def _is_log_file(self, file_path: Path) -> bool:
        """
        Проверить, является ли файл файлом лога.

        Args:
            file_path: Путь к файлу.

        Returns:
            True если файл является логом.
        """
        # Проверяем расширение
        suffix = file_path.suffix.lower()
        if suffix in self.LOG_EXTENSIONS:
            return True

        # Проверяем имя файла по паттернам (для файлов без расширения)
        name = file_path.name.lower()

        # Паттерны для файлов техжурнала 1С
        for pattern in self.LOG_NAME_PATTERNS:
            if re.match(pattern, name):
                return True

        # Паттерны для обычных .log файлов
        for patterns in self.FILE_PATTERNS.values():
            for pattern in patterns:
                if re.match(pattern, name):
                    return True

        return False

    def _detect_formats(self, structure: LogStructure) -> None:
        """
        Определить форматы логов по первым строкам.

        Args:
            structure: Структура логов для анализа.
        """
        for dir_info in structure.directories.values():
            for file_path in dir_info.files[:3]:  # Проверяем первые 3 файла
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        first_line = f.readline().strip()
                        if first_line:
                            fmt = self._identify_format(first_line)
                            if fmt:
                                structure.detected_formats.add(fmt)
                except Exception:
                    pass

    def _identify_format(self, line: str) -> Optional[str]:
        """
        Идентифицировать формат лога по первой строке.

        Args:
            line: Первая строка файла.

        Returns:
            Название формата или None.
        """
        # Формат 1С: 2024-01-15 10:30:00.123+0300 EXCP process-name ...
        if re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", line):
            return "1c-techjournal-standard"

        # Формат 1С (короткий): 15.01.2024 10:30:00 EXCP ...
        if re.match(r"^\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2}", line):
            return "1c-techjournal-short"

        # Формат с разделителями: 2024-01-15T10:30:00.123Z ...
        if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", line):
            return "iso8601"

        return None

    def get_log_dirs_for_type(
        self,
        structure: LogStructure,
        log_type: str,
    ) -> List[Path]:
        """
        Получить список директорий для указанного типа логов.

        Args:
            structure: Структура логов.
            log_type: Тип логов (core, perf, locks, sql, zabbix).

        Returns:
            Список путей к директориям.
        """
        result = []

        # Точное совпадение
        if log_type in structure.directories:
            result.append(structure.directories[log_type].path)

        # Ищем похожие типы
        for dir_name, dir_info in structure.directories.items():
            if log_type in dir_name or dir_name in log_type:
                if dir_info.path not in result:
                    result.append(dir_info.path)

        return result
