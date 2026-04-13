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

    # Память (суммарное потребление, учитывает отрицательные значения)
    total_memory: int = 0  # байты (сумма всех Memory)
    memory_samples: list[int] = field(default_factory=list)  # отдельные значения для анализа
    memory_by_process: dict[str, int] = field(
        default_factory=dict
    )  # {process_name: total_memory_bytes}

    # Сетевые ошибки (10054 и др.)
    network_errors: int = 0  # количество сетевых ошибок (10054, 10053, etc.)

    # Топ медленных методов (для long_calls)
    method_durations: dict[str, list[int]] = field(
        default_factory=dict
    )  # {method_name: [duration_us, ...]}

    # SQL-запросы (для slow_sql)
    sql_queries: list[str] = field(default_factory=list)  # первые 200 символов SQL-запросов

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

        # Агрегация памяти
        if entry.memory is not None:
            self.total_memory += entry.memory
            if len(self.memory_samples) < 50:
                self.memory_samples.append(entry.memory)

            # Агрегация по процессам
            if entry.process_name:
                current = self.memory_by_process.get(entry.process_name, 0)
                self.memory_by_process[entry.process_name] = current + entry.memory

        # Подсчёт сетевых ошибок (10054, 10053, 10060, 10061)
        if entry.description:
            import re

            if re.search(r"\b(10054|10053|10060|10061)\b", entry.description):
                self.network_errors += 1
            elif re.search(r"\b(10054|10053|10060|10061)\b", (entry.context or "")):
                self.network_errors += 1

        # Топ медленных методов (из поля method/context)
        method_name = entry.method or self._extract_method_from_context(entry.context)
        if method_name and entry.duration:
            if method_name not in self.method_durations:
                self.method_durations[method_name] = []
            self.method_durations[method_name].append(entry.duration)

        # Сбор SQL-запросов для slow_sql
        if entry.sql and len(self.sql_queries) < 10:
            # Берём первые 200 символов SQL-запроса
            sql_snippet = entry.sql[:200].strip()
            if sql_snippet not in self.sql_queries:
                self.sql_queries.append(sql_snippet)

    @staticmethod
    def _extract_method_from_context(context: Optional[str]) -> Optional[str]:
        """Извлечь имя метода из поля Context (последнее звено стека)

        Формат Context в ТЖ — многострочный стек вызовов:
            Форма.Вызов :
                Обработка.ОперацииЗакрытияМесяца.Форма.ЗакрытиеМесяца.Модуль.ТекущееСостояниеФоновогоЗадания : 46
            {ОбщийМодуль.ПроведениеДокументов.Провести}

        Логика извлечения (приоритет):
        1. Последняя строка в стеке (очищенная от номеров строк)
        2. Последний элемент в фигурных скобках {...}
        3. Полный путь к последнему методу (без обрезания)
        """
        if not context:
            return None
        import re

        # Разбиваем стек по переносам строк
        lines = [line.strip() for line in context.split("\n") if line.strip()]
        if not lines:
            return None

        # Берём последнюю значимую строку
        last_line = lines[-1]

        # Очищаем от номеров строк (формат "... : 46")
        clean_method = re.sub(r"\s*:\s*\d+$", "", last_line)

        # Убираем префиксы типа "Форма.Вызов :"
        clean_method = re.sub(r"^.*?:\s*", "", clean_method).strip()

        # Если пустой результат — пробуем извлечь из фигурных скобок
        if not clean_method:
            matches = re.findall(r"\{([^}]+)\}", context)
            if matches:
                clean_method = matches[-1].strip()

        if not clean_method:
            return None

        # Возвращаем полный путь метода (не обрезаем до последнего элемента)
        # Это даёт больше контекста: "ОбщийМодуль.ПроведениеДокументов.Провести"
        return clean_method

    @property
    def avg_duration(self) -> float:
        """Средняя длительность в мс"""
        if not self.count or not self.total_duration:
            return 0.0
        return round(self.total_duration / self.count / 1000, 2)

    @property
    def memory_usage_bytes(self) -> int:
        """Суммарное потребление памяти в байтах"""
        return self.total_memory

    @property
    def memory_by_process_top(self) -> list[dict]:
        """Топ-3 процесса по потреблению памяти"""
        if not self.memory_by_process:
            return []

        sorted_processes = sorted(
            self.memory_by_process.items(), key=lambda x: abs(x[1]), reverse=True
        )
        return [
            {"process": proc, "value": mem}
            for proc, mem in sorted_processes[:3]
            if mem != 0  # Исключаем процессы с нулевой памятью
        ]

    @property
    def top_slow_methods(self) -> list[dict]:
        """Топ-5 самых долгих методов по суммарной длительности"""
        if not self.method_durations:
            return []

        method_stats = {}
        for method, durations in self.method_durations.items():
            total_us = sum(durations)
            method_stats[method] = {
                "method": method,
                "count": len(durations),
                "total_duration_ms": round(total_us / 1000, 2),
                "avg_duration_ms": round(total_us / len(durations) / 1000, 2),
            }

        # Сортируем по суммарной длительности и берём топ-5
        sorted_methods = sorted(
            method_stats.values(), key=lambda x: x["total_duration_ms"], reverse=True
        )
        return sorted_methods[:5]


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
        result = {
            "timestamp": self.timestamp.isoformat(),
            "period_seconds": self.period_seconds,
            "logs_base_path": self.logs_base_path,
            "total_events": self.total_events,
            "critical_events": self.critical_events,
            "errors.count": self.errors.count,
            "errors.users": len(self.errors.users),
            "errors.avg_duration_ms": self.errors.avg_duration,
            "errors.memory_usage_bytes": self.errors.memory_usage_bytes,
            "errors.network_errors": self.errors.network_errors,
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

        # Добавляем топ медленных методов для long_calls
        if self.long_calls.top_slow_methods:
            result["long_calls.top_slow_methods"] = self.long_calls.top_slow_methods

        # Добавляем память по процессам для long_calls
        if self.long_calls.memory_by_process_top:
            result["long_calls.memory_by_process"] = self.long_calls.memory_by_process_top

        # Добавляем SQL-запросы для slow_sql
        if self.slow_sql.sql_queries:
            result["slow_sql.queries"] = self.slow_sql.sql_queries

        return result

    def to_zabbix_lld(self, host: str = "unknown") -> list[dict[str, Any]]:
        """Преобразование в плоский формат для Zabbix LLD

        Возвращает список метрик в формате:
        [
            {"host": "srv-pinavto01", "key": "1c.excp.count[pinavto_crm]", "value": 779},
            {"host": "srv-pinavto01", "key": "1c.mem.delta[ka_pin_test8]", "value": 120912},
            {"host": "srv-pinavto01", "key": "1c.network.error.10054", "value": 170}
        ]
        """
        metrics = []

        # Общие метрики
        metrics.append(
            {
                "host": host,
                "key": "1c.techjournal.total_events",
                "value": self.total_events,
            }
        )
        metrics.append(
            {
                "host": host,
                "key": "1c.techjournal.critical_events",
                "value": self.critical_events,
            }
        )

        # Метрики по категориям
        category_map = {
            "errors": "excp",
            "warnings": "warn",
            "deadlocks": "deadlock",
            "timeouts": "timeout",
            "long_locks": "long_lock",
            "long_calls": "long_call",
            "slow_sql": "slow_sql",
            "cluster_events": "cluster",
            "admin_events": "admin",
        }

        for attr_name, zabbix_key in category_map.items():
            stats = getattr(self, attr_name, None)
            if not stats:
                continue

            # Базовые метрики
            metrics.append(
                {
                    "host": host,
                    "key": f"1c.{zabbix_key}.count",
                    "value": stats.count,
                }
            )

            if stats.avg_duration > 0:
                metrics.append(
                    {
                        "host": host,
                        "key": f"1c.{zabbix_key}.avg_duration_ms",
                        "value": stats.avg_duration,
                    }
                )

            # Память (только если есть данные)
            if stats.memory_usage_bytes != 0:
                metrics.append(
                    {
                        "host": host,
                        "key": f"1c.{zabbix_key}.memory_delta_bytes",
                        "value": stats.memory_usage_bytes,
                    }
                )

            # Сетевые ошибки
            if stats.network_errors > 0:
                metrics.append(
                    {
                        "host": host,
                        "key": f"1c.network.error.{zabbix_key}",
                        "value": stats.network_errors,
                    }
                )

        # Метрики по базам данных (из processes)
        all_processes = set()
        for attr_name in category_map.keys():
            stats = getattr(self, attr_name, None)
            if stats:
                all_processes.update(stats.processes)

        for process in sorted(all_processes):
            # Считаем ошибки по каждой БД
            error_count = 0
            memory_delta = 0
            network_err_count = 0

            stats = self.errors
            if process in stats.processes:
                # Приблизительный подсчёт (нужно улучшить в будущем)
                error_count = stats.count  # упрощённо
                memory_delta = stats.memory_usage_bytes
                network_err_count = stats.network_errors

            if error_count > 0:
                metrics.append(
                    {
                        "host": host,
                        "key": f"1c.excp.count[{process}]",
                        "value": error_count,
                    }
                )

            if memory_delta != 0:
                metrics.append(
                    {
                        "host": host,
                        "key": f"1c.mem.delta[{process}]",
                        "value": memory_delta,
                    }
                )

            if network_err_count > 0:
                metrics.append(
                    {
                        "host": host,
                        "key": f"1c.network.error.10054[{process}]",
                        "value": network_err_count,
                    }
                )

        # Топ медленных методов (для long_calls)
        if self.long_calls.top_slow_methods:
            for i, method_info in enumerate(self.long_calls.top_slow_methods):
                method_name = method_info["method"]
                # Безопасное имя для Zabbix key
                safe_name = method_name.replace("[", "(").replace("]", ")")[:100]
                metrics.append(
                    {
                        "host": host,
                        "key": f"1c.long_call.method[{safe_name}]",
                        "value": method_info["total_duration_ms"],
                    }
                )

        return metrics


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

        # Парсим все найденные директории (исключаем 'root' — это служебная запись)
        directories = [
            d for d in self.get_log_directories() if not str(d) == str(self.log_base_path)
        ]

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
                f"  └─ Средняя длительность блокировок: {metrics.long_locks.avg_duration} мс"
            )

        if metrics.long_calls.count > 0:
            lines.append(f"  └─ Средняя длительность вызовов: {metrics.long_calls.avg_duration} мс")

        if metrics.slow_sql.count > 0:
            lines.append(f"  └─ Средняя длительность SQL: {metrics.slow_sql.avg_duration} мс")

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

    def get_processes_for_lld(
        self,
        period_minutes: int = 5,
    ) -> list[dict[str, str]]:
        """
        Получить список процессов для Zabbix LLD (Low Level Discovery).

        Возвращает список процессов, обнаруженных в логах за период,
        в формате для автообнаружения Zabbix.

        Args:
            period_minutes: Период сбора в минутах

        Returns:
            Список словарей в формате Zabbix LLD:
            [
                {"{#PROC_NAME}": "pinavto_crm"},
                {"{#PROC_NAME}": "ka_pin_test8"},
                {"{#PROC_NAME}": "pinavto_test10"}
            ]
        """
        metrics = self.collect(period_minutes=period_minutes)

        # Собираем все уникальные процессы из всех категорий
        all_processes = set()
        for attr_name in [
            "errors",
            "warnings",
            "deadlocks",
            "timeouts",
            "long_locks",
            "long_calls",
            "slow_sql",
            "cluster_events",
            "admin_events",
        ]:
            stats = getattr(metrics, attr_name, None)
            if stats:
                all_processes.update(stats.processes)

        # Формируем ответ в формате Zabbix LLD
        return [{"{#PROC_NAME}": proc} for proc in sorted(all_processes)]
