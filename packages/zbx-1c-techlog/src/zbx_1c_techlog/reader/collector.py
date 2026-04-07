"""Сборщик метрик из техжурнала 1С с автообнаружением структуры логов"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .discovery import LogStructureDiscovery, LogStructure
from .parser import LogEntry, TechJournalParser, ParserStats


@dataclass
class EventStats:
    """Статистика по событию"""

    count: int = 0
    users: set[str] = field(default_factory=set)
    processes: set[str] = field(default_factory=set)
    total_duration: int = 0  # мкс
    descriptions: list[str] = field(default_factory=list)
    computers: set[str] = field(default_factory=set)

    def add(self, entry: LogEntry) -> None:
        """Добавить запись в статистику"""
        self.count += 1
        if entry.user:
            self.users.add(entry.user)
        if entry.process_name:
            self.processes.add(entry.process_name)
        if entry.computer_name:
            self.computers.add(entry.computer_name)
        if entry.duration:
            self.total_duration += entry.duration
        if entry.description and len(self.descriptions) < 10:
            self.descriptions.append(entry.description[:200])

    @property
    def avg_duration(self) -> float:
        """Средняя длительность в мс"""
        if not self.count or not self.total_duration:
            return 0.0
        return round(self.total_duration / self.count / 1000, 2)


@dataclass
class MetricsResult:
    """Результат сбора метрик"""

    timestamp: datetime
    period_seconds: int
    logs_base_path: str
    log_structure: Optional[Dict] = None  # Информация о найденной структуре

    # События по типам
    errors: EventStats = field(default_factory=EventStats)
    warnings: EventStats = field(default_factory=EventStats)
    deadlocks: EventStats = field(default_factory=EventStats)
    timeouts: EventStats = field(default_factory=EventStats)
    long_locks: EventStats = field(default_factory=EventStats)
    long_calls: EventStats = field(default_factory=EventStats)
    slow_sql: EventStats = field(default_factory=EventStats)
    cluster_events: EventStats = field(default_factory=EventStats)
    admin_events: EventStats = field(default_factory=EventStats)

    # Сводные метрики
    total_events: int = 0
    critical_events: int = 0

    # Статистика парсинга
    parser_stats: Dict[str, ParserStats] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Преобразование в словарь для Zabbix"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "period_seconds": self.period_seconds,
            "logs_base_path": self.logs_base_path,
            "total_events": self.total_events,
            "critical_events": self.critical_events,
            "errors.count": self.errors.count,
            "errors.users": len(self.errors.users),
            "errors.avg_duration_ms": self.errors.avg_duration,
            "warnings.count": self.warnings.count,
            "deadlocks.count": self.deadlocks.count,
            "timeouts.count": self.timeouts.count,
            "long_locks.count": self.long_locks.count,
            "long_locks.avg_duration_ms": self.long_locks.avg_duration,
            "long_calls.count": self.long_calls.count,
            "long_calls.avg_duration_ms": self.long_calls.avg_duration,
            "slow_sql.count": self.slow_sql.count,
            "slow_sql.avg_duration_ms": self.slow_sql.avg_duration,
            "cluster_events.count": self.cluster_events.count,
            "admin_events.count": self.admin_events.count,
        }


class MetricsCollector:
    """
    Сборщик метрик из техжурнала с автообнаружением структуры.

    Автоматически находит:
    - Стандартные поддиректории (core, perf, locks, sql, zabbix)
    - Пользовательские поддиректории с логами
    - Разные форматы логов
    """

    EVENT_TYPES = {
        "EXCP": "errors",
        "EXCEPTION": "errors",
        "ATTN": "warnings",
        "ATTENTION": "warnings",
        "TDEADLOCK": "deadlocks",
        "DEADLOCK": "deadlocks",
        "TTIMEOUT": "timeouts",
        "TIMEOUT": "timeouts",
        "TLOCK": "long_locks",
        "LOCK": "long_locks",
        "CALL": "long_calls",
        "SDBL": "slow_sql",
        "SQL": "slow_sql",
        "DBMSSQL": "slow_sql",
        "DBMSPOSTGRE": "slow_sql",
        "DBMSORACLE": "slow_sql",
        "CLSTR": "cluster_events",
        "CLUSTER": "cluster_events",
        "ADMIN": "admin_events",
        "SRVR": "cluster_events",
        "RMNGR": "cluster_events",
        "RPHOST": "errors",
    }

    CRITICAL_EVENTS = {"EXCP", "EXCEPTION", "TDEADLOCK", "DEADLOCK", "TTIMEOUT", "TIMEOUT"}

    def __init__(self, log_base_path: str | Path):
        """
        Инициализация сборщика.

        Args:
            log_base_path: Базовый путь к логам техжурнала
        """
        self.log_base_path = Path(log_base_path)
        self.log_structure: Optional[LogStructure] = None
        self._discover_structure()

    def _discover_structure(self) -> None:
        """Обнаружить структуру логов"""
        discovery = LogStructureDiscovery()
        self.log_structure = discovery.discover(self.log_base_path)

    def get_log_directories(self, log_type: Optional[str] = None) -> List[Path]:
        """
        Получить директории с логами.

        Args:
            log_type: Тип логов (core, perf, locks, sql, zabbix) или None для всех.

        Returns:
            Список путей к директориям.
        """
        if not self.log_structure:
            return []

        if log_type:
            return [
                dir_info.path
                for name, dir_info in self.log_structure.directories.items()
                if log_type in name or name in log_type
            ]

        return [dir_info.path for dir_info in self.log_structure.directories.values()]

    def collect(
        self,
        period_minutes: int = 5,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> MetricsResult:
        """
        Сбор метрик за период.

        Args:
            period_minutes: Период сбора в минутах
            from_time: Начало периода
            to_time: Конец периода

        Returns:
            MetricsResult с собранными метриками
        """
        if to_time is None:
            to_time = datetime.now()

        if from_time is None:
            from_time = to_time - timedelta(minutes=period_minutes)

        result = MetricsResult(
            timestamp=to_time,
            period_seconds=int(period_minutes * 60),
            logs_base_path=str(self.log_base_path),
            log_structure=self.log_structure.to_dict() if self.log_structure else None,
        )

        stats: dict[str, EventStats] = defaultdict(EventStats)
        parser_stats: dict[str, ParserStats] = {}

        # Нормализуем время
        if from_time.tzinfo is not None:
            from_time = from_time.replace(tzinfo=None)
        if to_time.tzinfo is not None:
            to_time = to_time.replace(tzinfo=None)

        # Парсим все найденные директории
        directories = self.get_log_directories() if self.log_structure else []

        # Если ничего не найдено, пробуем стандартные имена
        if not directories and self.log_base_path.exists():
            for subdir in ["core", "perf", "locks", "sql", "zabbix", "db", "srvinfo"]:
                dir_path = self.log_base_path / subdir
                if dir_path.exists():
                    directories.append(dir_path)

        # Оптимизация: читаем только файлы, измененные за последние period_minutes + буфер 15 мин
        # Увеличенный буфер критичен для вложенных каталогов с логами 1С
        min_mtime = from_time.timestamp() - 900  # 15 минут буфера

        for log_dir in directories:
            parser = TechJournalParser(log_dir)
            dir_parser_stats = ParserStats()

            # Рекурсивный обход всех вложенных каталогов без ограничения количества файлов
            for entry in parser.parse_directory(
                from_time=from_time,
                to_time=to_time,
                min_mtime=min_mtime,
                recursive=True,
                limit_files=None,  # Без ограничений для полного обхода
            ):
                entry_time = entry.timestamp
                if entry_time.tzinfo is not None:
                    entry_time = entry_time.replace(tzinfo=None)

                if entry_time < from_time or entry_time > to_time:
                    continue

                event_type = entry.event_name.upper()
                metric_name = self.EVENT_TYPES.get(event_type)

                if metric_name:
                    stats[metric_name].add(entry)
                    result.total_events += 1

                    if event_type in self.CRITICAL_EVENTS:
                        result.critical_events += 1

            dir_parser_stats = parser.get_stats()
            parser_stats[str(log_dir)] = dir_parser_stats

        result.errors = stats.get("errors", EventStats())
        result.warnings = stats.get("warnings", EventStats())
        result.deadlocks = stats.get("deadlocks", EventStats())
        result.timeouts = stats.get("timeouts", EventStats())
        result.long_locks = stats.get("long_locks", EventStats())
        result.long_calls = stats.get("long_calls", EventStats())
        result.slow_sql = stats.get("slow_sql", EventStats())
        result.cluster_events = stats.get("cluster_events", EventStats())
        result.admin_events = stats.get("admin_events", EventStats())
        result.parser_stats = parser_stats

        return result

    def collect_for_zabbix(
        self,
        period_minutes: int = 5,
        host: str | None = None,
    ) -> list[tuple[str, Any]]:
        """
        Сбор метрик в формате для Zabbix sender.

        Args:
            period_minutes: Период сбора в минутах
            host: Имя хоста Zabbix

        Returns:
            Список кортежей (key, value) для отправки
        """
        import socket

        if host is None:
            host = socket.gethostname()

        metrics = self.collect(period_minutes=period_minutes)
        result = []

        for key, value in metrics.to_dict().items():
            zabbix_key = f"zbx1cpy.techjournal.{key}"

            if isinstance(value, float):
                formatted_value = round(value, 2)
            elif isinstance(value, int):
                formatted_value = value
            else:
                formatted_value = str(value)

            result.append((zabbix_key, formatted_value))

        return result

    def get_summary(self, period_minutes: int = 5) -> str:
        """
        Получение текстовой сводки по метрикам.

        Args:
            period_minutes: Период сбора в минутах

        Returns:
            Текстовая сводка
        """
        metrics = self.collect(period_minutes=period_minutes)

        lines = [
            "=" * 60,
            "МОНИТОРИНГ ТЕХЖУРНАЛА 1С",
            "=" * 60,
            f"Период: {period_minutes} мин",
            f"Время сбора: {metrics.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Путь к логам: {metrics.logs_base_path}",
            "-" * 60,
        ]

        # Информация о структуре логов
        if metrics.log_structure:
            lines.append("НАЙДЕННЫЕ ДИРЕКТОРИИ:")
            for dir_name, dir_info in metrics.log_structure.get("directories", {}).items():
                lines.append(
                    f"  {dir_name}: {dir_info['file_count']} файлов ({dir_info['total_size_mb']} MB)"
                )
            lines.append(f"Всего файлов: {metrics.log_structure.get('total_files', 0)}")
            lines.append(f"Общий размер: {metrics.log_structure.get('total_size_mb', 0)} MB")
            lines.append("-" * 60)

        lines.extend(
            [
                f"Всего событий: {metrics.total_events}",
                f"Критичные события: {metrics.critical_events}",
                "-" * 60,
                "СОБЫТИЯ:",
                f"  Ошибки (EXCP):        {metrics.errors.count}",
                f"  Предупреждения (ATTN): {metrics.warnings.count}",
                f"  Deadlock (TDEADLOCK): {metrics.deadlocks.count}",
                f"  Timeout (TTIMEOUT):   {metrics.timeouts.count}",
                f"  Блокировки (TLOCK):   {metrics.long_locks.count}",
                f"  Долгие вызовы (CALL): {metrics.long_calls.count}",
                f"  Медленный SQL:        {metrics.slow_sql.count}",
                f"  События кластера:     {metrics.cluster_events.count}",
                f"  Админ.события:        {metrics.admin_events.count}",
            ]
        )

        if metrics.long_locks.count > 0:
            lines.append(
                f"  └─ Средняя длительность блокировок: {metrics.long_locks.avg_duration_ms} мс"
            )

        if metrics.long_calls.count > 0:
            lines.append(
                f"  └─ Средняя длительность вызовов: {metrics.long_calls.avg_duration_ms} мс"
            )

        if metrics.slow_sql.count > 0:
            lines.append(f"  └─ Средняя длительность SQL: {metrics.slow_sql.avg_duration_ms} мс")

        lines.append("=" * 60)

        return "\n".join(lines)

    def get_structure_info(self) -> str:
        """
        Получить информацию о найденной структуре логов.

        Returns:
            Текстовое описание структуры.
        """
        if not self.log_structure:
            return "Структура логов не найдена"

        lines = [
            "=" * 60,
            "СТРУКТУРА ТЕХЖУРНАЛА 1С",
            "=" * 60,
            f"Базовый путь: {self.log_structure.base_path}",
            "-" * 60,
        ]

        for dir_name, dir_info in self.log_structure.directories.items():
            size_mb = round(dir_info.total_size_bytes / 1024 / 1024, 2)
            lines.append(f"  {dir_name}:")
            lines.append(f"    Путь: {dir_info.path}")
            lines.append(f"    Файлов: {dir_info.file_count}")
            lines.append(f"    Размер: {size_mb} MB")
            if dir_info.files:
                lines.append(f"    Примеры:")
                for f in dir_info.files[:3]:
                    lines.append(f"      - {f.name}")

        lines.append("-" * 60)
        lines.append(f"Всего файлов: {self.log_structure.total_files}")
        lines.append(
            f"Общий размер: {round(self.log_structure.total_size_bytes / 1024 / 1024, 2)} MB"
        )
        lines.append(
            f"Форматы: {', '.join(self.log_structure.detected_formats) or 'не определены'}"
        )
        lines.append("=" * 60)

        return "\n".join(lines)
