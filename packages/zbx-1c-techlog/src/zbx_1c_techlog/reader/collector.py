"""Сборщик метрик из техжурнала 1С"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .parser import LogEntry, TechJournalParser


@dataclass
class EventStats:
    """Статистика по событию"""

    count: int = 0
    users: set[str] = field(default_factory=set)
    processes: set[str] = field(default_factory=set)
    total_duration: int = 0  # мкс
    descriptions: list[str] = field(default_factory=list)

    def add(self, entry: LogEntry) -> None:
        """Добавить запись в статистику"""
        self.count += 1
        if entry.user:
            self.users.add(entry.user)
        if entry.process_name:
            self.processes.add(entry.process_name)
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
    Сборщик метрик из техжурнала.
    """

    EVENT_TYPES = {
        "EXCP": "errors",
        "ATTN": "warnings",
        "TDEADLOCK": "deadlocks",
        "TTIMEOUT": "timeouts",
        "TLOCK": "long_locks",
        "CALL": "long_calls",
        "SDBL": "slow_sql",
        "DBMSSQL": "slow_sql",
        "CLSTR": "cluster_events",
        "ADMIN": "admin_events",
    }

    CRITICAL_EVENTS = {"EXCP", "TDEADLOCK", "TTIMEOUT"}

    def __init__(self, log_base_path: str | Path):
        """
        Инициализация сборщика.

        Args:
            log_base_path: Базовый путь к логам техжурнала
        """
        self.log_base_path = Path(log_base_path)

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
        )

        stats: dict[str, EventStats] = defaultdict(EventStats)

        # Нормализуем время
        if from_time.tzinfo is not None:
            from_time = from_time.replace(tzinfo=None)
        if to_time.tzinfo is not None:
            to_time = to_time.replace(tzinfo=None)

        # Парсим все поддиректории
        for subdir in ["core", "perf", "locks", "sql", "zabbix"]:
            log_dir = self.log_base_path / subdir
            if not log_dir.exists():
                continue

            parser = TechJournalParser(log_dir)

            for entry in parser.parse_directory():
                entry_time = entry.timestamp
                if entry_time.tzinfo is not None:
                    entry_time = entry_time.replace(tzinfo=None)

                if entry_time < from_time or entry_time > to_time:
                    continue

                event_type = entry.event_name
                metric_name = self.EVENT_TYPES.get(event_type)

                if metric_name:
                    stats[metric_name].add(entry)
                    result.total_events += 1

                    if event_type in self.CRITICAL_EVENTS:
                        result.critical_events += 1

        result.errors = stats.get("errors", EventStats())
        result.warnings = stats.get("warnings", EventStats())
        result.deadlocks = stats.get("deadlocks", EventStats())
        result.timeouts = stats.get("timeouts", EventStats())
        result.long_locks = stats.get("long_locks", EventStats())
        result.long_calls = stats.get("long_calls", EventStats())
        result.slow_sql = stats.get("slow_sql", EventStats())
        result.cluster_events = stats.get("cluster_events", EventStats())
        result.admin_events = stats.get("admin_events", EventStats())

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
            "-" * 60,
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

        if metrics.long_locks.count > 0:
            lines.append(f"  └─ Средняя длительность блокировок: {metrics.long_locks.avg_duration_ms} мс")

        if metrics.long_calls.count > 0:
            lines.append(f"  └─ Средняя длительность вызовов: {metrics.long_calls.avg_duration_ms} мс")

        if metrics.slow_sql.count > 0:
            lines.append(f"  └─ Средняя длительность SQL: {metrics.slow_sql.avg_duration_ms} мс")

        lines.append("=" * 60)

        return "\n".join(lines)
