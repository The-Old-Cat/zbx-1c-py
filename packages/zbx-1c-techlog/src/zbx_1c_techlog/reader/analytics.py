"""Аналитический модуль для техжурнала 1С

Генерирует аналитические выводы на основе собранных метрик:
- Оценка стабильности системы
- Проблемы конкурентности (deadlocks, timeouts)
- Производительность СУБД
- Нагрузка на кластер
- Пользовательская аналитика
- Раннее предупреждение (тренды)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from ..reader.collector import EventStats, MetricsCollector, MetricsResult
from ..reader.parser import LogEntry, TechJournalParser


@dataclass
class ProblemGroup:
    """Сгруппированная группа однотипных проблем."""

    problem_type: str  # "error", "deadlock", "timeout", "slow_sql", "long_lock", "long_call"
    error_signature: str  # сигнатура ошибки (descr_XXXX, file_XXX, hash_XXX)
    severity: str  # "critical", "warning", "info"
    count: int
    unique_users: list[str]
    unique_processes: list[str]
    unique_computers: list[str]
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]
    avg_duration_ms: Optional[float]
    max_duration_ms: Optional[float] = None  # максимальная длительность
    min_duration_ms: Optional[float] = None  # минимальная длительность
    event_samples: list[dict] = field(
        default_factory=list
    )  # {"timestamp", "user", "process", "computer", "description", "duration_ms", "sql"}

    # Обогащённые поля
    impact_score: float = 0.0  # 0-1, насколько мешает работе
    possible_root_cause: Optional[str] = None  # предполагаемая причина
    database_context: list[str] = field(default_factory=list)  # имена затронутых БД
    merged_from: list[str] = field(default_factory=list)  # сигнатуры, объединённые в эту проблему

    # Агрегация по компонентам 1С
    component_layer: Optional[str] = None  # "backend", "vrs", "network", "common"

    # Человекочитаемое описание для отчётов
    human_description: Optional[str] = None  # "Network Timeout (10054)" вместо "descr_10054"

    # Zabbix-friendly ключ триггера
    trigger_key: Optional[str] = None  # Стабильный ключ для Zabbix: "error_10054", "sql_slow"


@dataclass
class Insight:
    """Отдельный аналитический вывод"""

    severity: str  # "critical", "warning", "info"
    category: str  # "stability", "locks", "sql", "load", "users", "trend"
    title: str
    description: str
    metric_value: Optional[str] = None
    recommendation: str = ""


@dataclass
class UserImpact:
    """Влияние конкретного пользователя/процесса"""

    entity: str  # имя пользователя или процесса
    entity_type: str  # "user" | "process"
    errors: int = 0
    deadlocks: int = 0
    timeouts: int = 0
    slow_sql: int = 0
    total_events: int = 0
    error_rate: float = 0.0  # процент ошибок (errors / total_events * 100)


@dataclass
class AnalyticsResult:
    """Полный результат аналитики"""

    timestamp: str
    period_minutes: int

    # Общая оценка здоровья
    health_score: int  # 0-100
    health_status: str  # "healthy", "degraded", "critical"

    # Выводы
    insights: list[Insight] = field(default_factory=list)

    # Топ проблемных пользователей и процессов
    top_impacted_users: list[UserImpact] = field(default_factory=list)
    top_impacted_processes: list[UserImpact] = field(default_factory=list)

    # Сводные текстовые рекомендации
    recommendations: list[str] = field(default_factory=list)


class TechJournalAnalyzer:
    """
    Генератор аналитических выводов на основе метрик техжурнала.

    Анализирует собранные метрики и формирует:
    - Инсайты (конкретные выводы с оценкой критичности)
    - Топ проблемных пользователей/процессов
    - Общую оценку здоровья системы
    - Рекомендации
    """

    # Пороги для оценки здоровья
    HEALTH_THRESHOLDS = {
        "critical_errors": 50,  # >50 ошибок = critical
        "warning_errors": 10,  # >10 ошибок = warning
        "critical_deadlocks": 10,  # >10 дедлоков = critical
        "warning_deadlocks": 3,  # >3 дедлоков = warning
        "critical_timeouts": 30,  # >30 таймаутов = critical
        "warning_timeouts": 10,  # >10 таймаутов = warning
        "critical_slow_sql": 100,  # >100 медленных SQL = critical
        "warning_slow_sql": 20,  # >20 медленных SQL = warning
        "slow_sql_avg_ms": 5000,  # средний SQL >5с = warning
        "long_locks_avg_ms": 3000,  # средняя блокировка >3с = warning
    }

    def __init__(self, collector: MetricsCollector):
        """
        Args:
            collector: Сборщик метрик, через который получаем данные.
        """
        self._collector = collector

    def analyze(
        self,
        period_minutes: int = 5,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> AnalyticsResult:
        """
        Сгенерировать аналитические выводы за период.

        Args:
            period_minutes: Период анализа в минутах.
            from_time: Начало периода (override).
            to_time: Конец периода (override).

        Returns:
            AnalyticsResult с инсайтами и рекомендациями.
        """
        metrics = self._collector.collect(
            period_minutes=period_minutes, from_time=from_time, to_time=to_time
        )

        insights: list[Insight] = []
        impacted_users: dict[str, UserImpact] = {}
        impacted_processes: dict[str, UserImpact] = {}

        # 1. Анализ стабильности (ошибки)
        self._analyze_stability(metrics, insights)

        # 2. Анализ блокировок
        self._analyze_locks(metrics, insights)

        # 3. Анализ SQL-производительности
        self._analyze_sql_performance(metrics, insights)

        # 4. Анализ нагрузки на кластер
        self._analyze_cluster_load(metrics, insights)

        # 5. Сбор данных по пользователям и процессам
        self._gather_entity_impact(metrics, impacted_users, impacted_processes)

        # 6. Оценка здоровья
        health_score, health_status = self._calculate_health(metrics)

        now = to_time or datetime.now()
        result = AnalyticsResult(
            timestamp=now.isoformat(),
            period_minutes=period_minutes,
            health_score=health_score,
            health_status=health_status,
            insights=insights,
            top_impacted_users=self._top_entities(impacted_users, limit=10),
            top_impacted_processes=self._top_entities(impacted_processes, limit=10),
        )

        # 7. Генерация рекомендаций
        result.recommendations = self._generate_recommendations(insights)

        return result

    # ------------------------------------------------------------------
    # Группировка проблем из сырых событий
    # ------------------------------------------------------------------

    def analyze_problems(
        self,
        period_minutes: int = 5,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        max_events: int = 2000,
    ) -> list[ProblemGroup]:
        """
        Собрать и сгруппировать проблемы из сырых событий техжурнала.

        Args:
            period_minutes: Период анализа.
            from_time: Начало периода (override).
            to_time: Конец периода (override).
            max_events: Макс. количество обрабатываемых событий.

        Returns:
            Список сгруппированных ProblemGroup, отсортированный по критичности.
        """
        if to_time is None:
            to_time = datetime.now()
        if from_time is None:
            from_time = to_time - timedelta(minutes=period_minutes)

        if from_time.tzinfo is not None:
            from_time = from_time.replace(tzinfo=None)
        if to_time.tzinfo is not None:
            to_time = to_time.replace(tzinfo=None)

        min_mtime = from_time.timestamp() - 900

        # Структура: {group_key: {...}}
        problem_groups: dict[str, dict] = {}
        events_processed = 0

        # Получаем директории через коллектор (без привязки к путям в эндпоинте)
        directories = self._collector.get_log_directories()
        if not directories and self._collector.log_base_path.exists():
            for subdir in ["core", "perf", "locks", "sql", "zabbix"]:
                dir_path = self._collector.log_base_path / subdir
                if dir_path.exists():
                    directories.append(dir_path)

        for log_dir in directories:
            if events_processed >= max_events:
                break

            parser = TechJournalParser(log_dir)
            for entry in parser.parse_directory(
                from_time=from_time,
                to_time=to_time,
                min_mtime=min_mtime,
                limit_files=500,
            ):
                events_processed += 1
                event_upper = entry.event_name.upper()
                problem_type = None
                severity = "info"

                if event_upper in ("EXCP", "EXCEPTION", "RPHOST"):
                    problem_type = "error"
                    severity = "critical"
                elif event_upper in ("TDEADLOCK", "DEADLOCK"):
                    problem_type = "deadlock"
                    severity = "critical"
                elif event_upper in ("TTIMEOUT", "TIMEOUT"):
                    problem_type = "timeout"
                    severity = "warning"
                elif event_upper in ("SDBL", "SQL", "DBMSSQL", "DBMSPOSTGRE", "DBMSORACLE"):
                    if entry.duration and entry.duration > 1000000:
                        problem_type = "slow_sql"
                        severity = "warning"
                elif event_upper in ("TLOCK", "LOCK"):
                    problem_type = "long_lock"
                    severity = "info"
                elif event_upper == "CALL":
                    if entry.duration and entry.duration > 5000000:
                        problem_type = "long_call"
                        severity = "info"

                if problem_type:
                    error_signature = self._extract_error_signature(entry.description)
                    group_key = f"{problem_type}::{error_signature}"

                    if group_key not in problem_groups:
                        problem_groups[group_key] = {
                            "problem_type": problem_type,
                            "error_signature": error_signature,
                            "severity": severity,
                            "count": 0,
                            "users": set(),
                            "processes": set(),
                            "computers": set(),
                            "durations": [],
                            "timestamps": [],
                            "event_samples": [],
                            "_seen_examples": set(),
                            "merged_from": [],
                        }

                    group = problem_groups[group_key]
                    group["count"] += 1

                    if entry.user:
                        group["users"].add(entry.user)
                    if entry.process_name:
                        group["processes"].add(entry.process_name)
                    if entry.computer_name:
                        group["computers"].add(entry.computer_name)
                    if entry.duration:
                        group["durations"].append(entry.duration)

                    group["timestamps"].append(entry.timestamp)

                    # Дедупликация примеров
                    if len(group["event_samples"]) < 3:
                        example_key = (entry.description, entry.process_name, entry.user)
                        if example_key not in group["_seen_examples"]:
                            group["_seen_examples"].add(example_key)
                            example = {
                                "timestamp": entry.timestamp.isoformat(),
                                "user": entry.user,
                                "process": entry.process_name,
                                "computer": entry.computer_name,
                                "description": (
                                    entry.description[:300] if entry.description else None
                                ),
                                "duration_ms": (
                                    round(entry.duration / 1000, 2) if entry.duration else None
                                ),
                                "sql": None,  # заполним ниже для SQL-событий
                            }
                            # Для SQL-событий сохраняем текст запроса
                            if problem_type == "slow_sql" and entry.sql:
                                example["sql"] = entry.sql[:500]
                            group["event_samples"].append(example)

        # Интеллектуальная дедупликация: объединяем проблемы с одинаковым
        # процессом/компьютером и близким временем (например, 10054 + файл cpp)
        problem_groups = self._merge_related_problems(problem_groups)

        # Формируем результат с обогащением
        problems = []
        for group_data in problem_groups.values():
            timestamps = group_data["timestamps"]
            durations = group_data["durations"]

            # Расчёт impact_score
            impact_score = self._calculate_impact_score(
                count=group_data["count"],
                severity=group_data["severity"],
                unique_processes=len(group_data["processes"]),
                unique_users=len(group_data["users"]),
                problem_type=group_data["problem_type"],
            )

            # Предполагаемая причина
            possible_root_cause = self._guess_root_cause(
                group_data["error_signature"],
                group_data["problem_type"],
                group_data.get("merged_from", []),
            )

            # Для hash-сигнатур пробуем обогатить контекстом
            if possible_root_cause is None and group_data["event_samples"]:
                possible_root_cause = self._enrich_root_cause_with_context(
                    group_data["error_signature"],
                    group_data["problem_type"],
                    group_data["event_samples"][0].get("description"),
                )

            # Определяем компонент
            component_layer = self._detect_component(
                group_data["error_signature"],
                (
                    group_data["event_samples"][0].get("description")
                    if group_data["event_samples"]
                    else None
                ),
            )

            # Человекочитаемое описание
            human_description = self._generate_human_description(
                group_data["error_signature"],
                group_data["problem_type"],
                group_data["count"],
                group_data.get("merged_from", []),
            )

            # Zabbix-friendly ключ триггера
            trigger_key = self._generate_trigger_key(
                group_data["error_signature"],
                group_data["problem_type"],
            )

            problems.append(
                ProblemGroup(
                    problem_type=group_data["problem_type"],
                    error_signature=group_data["error_signature"],
                    severity=group_data["severity"],
                    count=group_data["count"],
                    unique_users=sorted(group_data["users"]),
                    unique_processes=sorted(group_data["processes"]),
                    unique_computers=sorted(group_data["computers"]),
                    first_seen=min(timestamps) if timestamps else None,
                    last_seen=max(timestamps) if timestamps else None,
                    avg_duration_ms=(
                        round(sum(durations) / len(durations) / 1000, 2) if durations else None
                    ),
                    max_duration_ms=(round(max(durations) / 1000, 2) if durations else None),
                    min_duration_ms=(round(min(durations) / 1000, 2) if durations else None),
                    event_samples=group_data["event_samples"],
                    impact_score=impact_score,
                    possible_root_cause=possible_root_cause,
                    database_context=sorted(group_data["processes"]),  # процесс = БД
                    merged_from=group_data.get("merged_from", []),
                    component_layer=component_layer,
                    human_description=human_description,
                    trigger_key=trigger_key,
                )
            )

        # Сортируем по критичности и количеству
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        problems.sort(key=lambda p: (severity_order.get(p.severity, 3), -p.count))

        return problems

    # ------------------------------------------------------------------
    # Вспомогательные методы обогащения
    # ------------------------------------------------------------------

    # Маппинг известных хэшей → человекочитаемое описание
    # Заполняется автоматически при анализе и сохраняется между запусками
    KNOWN_HASH_DESCRIPTIONS: dict[str, str] = {}

    # Маппинг путей к компонентам 1С (расширенный)
    COMPONENT_PATH_MAP = {
        # --- Сервер приложений (Core) ---
        r"src[\\/]backend": "backend",
        r"src[\\/]srvline": "backend",
        r"src[\\/]rphost": "backend",
        r"src[\\/]rmngr": "backend",
        r"src[\\/]rctr": "backend",
        r"src[\\/]commn": "backend",
        # --- Работа с данными и SQL ---
        r"src[\\/]data": "database",
        r"src[\\/]storage": "database",
        r"src[\\/]dbms": "database",
        r"src[\\/]sql": "database",
        # --- Веб-сервисы и интеграции ---
        r"src[\\/]vrsbase": "vrs",
        r"src[\\/]vrs": "vrs",
        r"src[\\/]ws": "vrs",
        r"src[\\/]http": "vrs",
        r"src[\\/]web": "vrs",
        # --- Сетевой транспорт (Тут твои 10054) ---
        r"src[\\/]rtrsrvc": "network",
        r"src[\\/]net": "network",
        r"src[\\/]tcp": "network",
        r"src[\\/]ipc": "network",
        r"src[\\/]sock": "network",
        # --- Файловые операции (Важно для диска G:) ---
        r"src[\\/]file": "filesystem",
        r"src[\\/]folder": "filesystem",
        r"src[\\/]archive": "filesystem",
        # --- Кластер и управление ---
        r"src[\\/]clstr": "cluster",
        r"src[\\/]cluster": "cluster",
        r"src[\\/]admin": "cluster",
        r"src[\\/]mgr": "cluster",
        # --- Безопасность и Криптография ---
        r"src[\\/]crypto": "security",
        r"src[\\/]backbas[\\/]src[\\/]Crypto": "security",
        r"src[\\/]auth": "security",
        # --- Отладка (Debug) ---
        r"src[\\/]debug": "debug",
        r"src[\\/]debugger": "debug",
    }

    # Карта действий по слоям — для генерации "человеческих" рекомендаций
    LAYER_ACTION_MAP = {
        "backend": (
            "Ошибка бизнес-логики или кэша 1С. Рекомендуется проверить сеансы в консоли кластера "
            "или очистить кэш на диске."
        ),
        "vrs": (
            "Проблема в публикации веб-сервисов/OData. Проверьте настройки IIS/Apache "
            "и пул приложений."
        ),
        "network": ("Проверьте сетевые настройки."),
        "cluster": (
            "Нестабильность службы кластера (rmngr). Проверьте распределение rphost "
            "по рабочим серверам."
        ),
        "database": (
            "SQL Server долго отвечал. Проверьте нагрузку на диски или наличие блокировок. "
            "Выполните обновление статистики и переиндексацию СУБД."
        ),
        "filesystem": (
            "Проверьте свободное место и права доступа на диске. "
            "Возможны проблемы с файловым хранилищем или кэшем."
        ),
        "security": (
            "Ошибка проверки прав. Проверьте настройки аутентификации или лицензии. "
            "Возможны проблемы с сертификатами или криптографией."
        ),
        "debug": (
            "События отладки. Если они генерируют ошибки — это скорее всего "
            "«мусор» от конфигуратора, а не реальная проблема пользователей."
        ),
        "common": (
            "Общая системная ошибка. Проверьте свободное место на диске и права доступа службы 1С."
        ),
    }

    # Подсказки для расшифровки конкретных файлов в человекочитаемые описания
    SOURCE_HINTS = {
        "DataExchangeServerImpl.cpp": "Обмен данными / РИБ",
        "RemoteCallListenerImpl.cpp": "Взаимодействие клиент-сервер (RSCALL)",
        "DataSeparationService.cpp": "Разделение данных (Облачные механизмы/Fresh)",
        "FolderFilesImpl.cpp": "Работа с файловым хранилищем",
        "FileHostImpl.cpp": "Файловый хост (диск G:)",
        "ClientFileCacheImpl.cpp": "Кэш клиента 1С",
        "DBMSSQL.cpp": "Взаимодействие с MS SQL Server",
        "DBMSPostgreSQL.cpp": "Взаимодействие с PostgreSQL",
        "RemoteCall.cpp": "Удалённый вызов (RPC)",
        "TcpConnection.cpp": "TCP-соединение",
        "LockManager.cpp": "Менеджер блокировок",
        "WorkingProcess.cpp": "Рабочий процесс сервера 1С",
    }

    @staticmethod
    def _generate_human_description(
        signature: str,
        problem_type: str,
        count: int,
        merged_from: list[str],
    ) -> str:
        """
        Сгенерировать человекочитаемое описание проблемы.

        Args:
            signature: Сигнатура ошибки
            problem_type: Тип проблемы
            count: Количество повторений
            merged_from: Объединённые сигнатуры

        Returns:
            Человекочитаемое описание
        """
        # Для descr_XXXX используем известные коды ошибок
        if signature.startswith("descr_"):
            code = signature.replace("descr_", "")
            known_names = {
                "10054": "Network Timeout (TCP RST)",
                "10053": "Connection Aborted (OS)",
                "10060": "Connection Timed Out",
                "10061": "Connection Refused",
                "80": "General Error",
            }
            name = known_names.get(code, f"Error #{code}")
            base = f"{name} [{count}x]"
            # Добавляем информацию об объединённых сигнатурах
            if merged_from:
                merged_parts = []
                for src in merged_from[:2]:
                    if src.startswith("file_"):
                        nm = src.replace("file_", "").rsplit(".", 1)[0]
                        merged_parts.append(nm)
                if merged_parts:
                    base += f" (+ {', '.join(merged_parts)})"
            return base

        # Для file_XXX — имя модуля с SOURCE_HINT
        if signature.startswith("file_"):
            file_name = signature.replace("file_", "")
            # Проверяем SOURCE_HINTS
            if file_name in TechJournalAnalyzer.SOURCE_HINTS:
                hint = TechJournalAnalyzer.SOURCE_HINTS[file_name]
                return f"{hint}: ошибка [{count}x]"
            # Убираем расширение
            base_name = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
            return f"Module error: {base_name} [{count}x]"

        # Для hash_XXX — сначала проверяем merged, потом известные описания
        if signature.startswith("hash_"):
            hash_val = signature.replace("hash_", "")
            # Если есть объединённые сигнатуры — показываем их
            if merged_from:
                merged_names = []
                for src in merged_from[:3]:
                    if src.startswith("descr_"):
                        code = src.replace("descr_", "")
                        known_names = {
                            "10054": "NetTimeout",
                            "10053": "ConnAbort",
                            "10060": "ConnTimeout",
                            "10061": "ConnRefused",
                        }
                        merged_names.append(known_names.get(code, f"#{code}"))
                    elif src.startswith("file_"):
                        name = src.replace("file_", "").rsplit(".", 1)[0]
                        merged_names.append(name)
                    else:
                        merged_names.append(src[:12])
                return f"Combined: {' + '.join(merged_names)} [{count}x]"
            if hash_val in TechJournalAnalyzer.KNOWN_HASH_DESCRIPTIONS:
                desc = TechJournalAnalyzer.KNOWN_HASH_DESCRIPTIONS[hash_val]
                return f"{desc} [{count}x]"
            return f"Recurring issue [{count}x]"

        # Для объединённых проблем
        if merged_from:
            merged_names = []
            for src in merged_from[:2]:
                if src.startswith("descr_"):
                    code = src.replace("descr_", "")
                    merged_names.append(f"#{code}")
                elif src.startswith("file_"):
                    name = src.replace("file_", "").rsplit(".", 1)[0]
                    merged_names.append(name)
            return f"Combined: {' + '.join(merged_names)} [{count}x]"

        return f"Unclassified {problem_type} [{count}x]"

    @staticmethod
    def _generate_trigger_key(
        signature: str,
        problem_type: str,
    ) -> str:
        """
        Сгенерировать стабильный Zabbix-friendly ключ триггера.

        Ключ не меняется между анализами, если проблема та же.
        Идеально для Zabbix trigger expression.

        Примеры:
        - error_descr_10054
        - error_file_rphost_cpp
        - deadlock
        - timeout
        - sql_slow
        - long_lock
        - long_call
        """
        # Для известных сигнатур — стабильный ключ
        if signature.startswith("descr_"):
            code = signature.replace("descr_", "")
            return f"error_descr_{code}"

        if signature.startswith("file_"):
            file_name = signature.replace("file_", "")
            # Убираем расширение для стабильности
            base_name = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
            return f"error_file_{base_name}"

        # Для хэшей — используем тип проблемы + хэш
        if signature.startswith("hash_"):
            hash_short = signature.replace("hash_", "")[:8]  # Первые 8 символов
            return f"{problem_type}_hash_{hash_short}"

        # Для типовых проблем без специфичной сигнатуры
        return problem_type

    @staticmethod
    def _detect_component(signature: str, description: Optional[str] = None) -> str:
        """
        Определить компонент 1С по сигнатуре ошибки и описанию.

        Args:
            signature: Сигнатура ошибки (file_XXX.cpp, descr_XXX, hash_XXX)
            description: Полное описание события

        Returns:
            Название компонента: "backend", "vrs", "network", "cluster", "database",
                               "filesystem", "security", "debug", "common"
        """
        import re

        # Проверяем сигнатуру file_XXX
        if signature.startswith("file_"):
            file_name = signature.replace("file_", "").lower()

            # Сервер приложений
            if any(
                kw in file_name
                for kw in [
                    "backend",
                    "srvline",
                    "rphost",
                    "rmngr",
                    "rctr",
                    "commn",
                ]
            ):
                return "backend"

            # Веб-сервисы
            if any(kw in file_name for kw in ["vrs", "ws", "http", "web"]):
                return "vrs"

            # Сеть
            if any(kw in file_name for kw in ["rtrsrvc", "net", "tcp", "ipc", "sock", "conn"]):
                return "network"

            # Кластер
            if any(kw in file_name for kw in ["clstr", "cluster", "admin", "mgr"]):
                return "cluster"

            # База данных
            if any(kw in file_name for kw in ["data", "storage", "dbms", "sql", "db"]):
                return "database"

            # Файловые операции
            if any(kw in file_name for kw in ["file", "folder", "archive", "temp"]):
                return "filesystem"

            # Безопасность
            if any(kw in file_name for kw in ["crypto", "auth", "cert", "sign"]):
                return "security"

            # Отладка
            if any(kw in file_name for kw in ["debug"]):
                return "debug"

        # Проверяем полное описание (там может быть путь к файлу)
        if description:
            for pattern, component in TechJournalAnalyzer.COMPONENT_PATH_MAP.items():
                if re.search(pattern, description, re.IGNORECASE):
                    return component

        return "common"

    @staticmethod
    def _generate_human_recommendation(problem: ProblemGroup) -> str:
        """
        Сгенерировать человекочитаемую рекомендацию на основе проблемы.

        Использует COMPONENT_PATH_MAP и LAYER_ACTION_MAP для привязки
        к конкретному компоненту и формирования осмысленного совета.

        Args:
            problem: Сгруппированная проблема с обогащёнными полями.

        Returns:
            Человекочитаемая рекомендация.
        """
        layer = problem.component_layer or "common"
        count = problem.count
        signature = problem.error_signature
        human_desc = problem.human_description or signature

        # Определяем контекст базы данных
        db_context = ""
        if problem.database_context:
            db_list = ", ".join(problem.database_context[:3])
            db_context = f" БД: {db_list}."

        # 1. Специфичные рекомендации по кодам ошибок
        if "10054" in signature or "10054" in (human_desc or ""):
            return (
                f"❌ Сеть: Обнаружено {count} разрывов (10054). "
                f"{TechJournalAnalyzer.LAYER_ACTION_MAP['network']}{db_context}"
            )

        if "10053" in signature or "10053" in (human_desc or ""):
            return (
                f"❌ Сеть: {count} обрывов соединения (10053). "
                f"Проверьте сетевые настройки.{db_context}"
            )

        if "10060" in signature or "10060" in (human_desc or ""):
            return (
                f"❌ Сеть: {count} таймаутов подключения (10060). "
                f"Проверьте сетевые настройки.{db_context}"
            )

        # 2. Специфичные рекомендации по типам проблем
        if problem.problem_type == "deadlock":
            return (
                f"🔒 Блокировки: {count} дедлоков. "
                f"{TechJournalAnalyzer.LAYER_ACTION_MAP.get(layer, TechJournalAnalyzer.LAYER_ACTION_MAP['common'])}"
                f"Проверьте расписание фоновых заданий и конкурентный доступ к данным.{db_context}"
            )

        if problem.problem_type == "timeout":
            return (
                f"⏱️ Таймауты: {count} случаев. "
                f"Возможные причины: перегрузка сервера, проблемы с сетью или СУБД. "
                f"Проверьте загрузку CPU и памяти на сервере 1С.{db_context}"
            )

        if problem.problem_type == "slow_sql":
            avg_ms = problem.avg_duration_ms or 0
            return (
                f"🐌 Медленный SQL: {count} запросов (средняя длительность: {avg_ms:.0f} мс). "
                f"Выполните обновление статистики и переиндексацию СУБД. "
                f"Проверьте планы запросов через технологический журнал.{db_context}"
            )

        if problem.problem_type == "long_lock":
            return (
                f"🔐 Блокировки: {count} длительных захватов. "
                f"Проверьте транзакции и конкурентный доступ к регистрам накопления.{db_context}"
            )

        if problem.problem_type == "long_call":
            avg_ms = problem.avg_duration_ms or 0
            return (
                f"⏳ Долгие вызовы: {count} случаев (средняя длительность: {avg_ms:.0f} мс). "
                f"Проанализируйте код конфигурации — оптимизируйте узкие места.{db_context}"
            )

        # 3. Специфичные рекомендации по описаниям
        if problem.event_samples:
            sample_desc = (problem.event_samples[0].description or "").lower()
            if any(kw in sample_desc for kw in ["data separation", "dataseparation", "разделени"]):
                return (
                    f"❌ Кэш: Проблема разделения данных ({count} раз). "
                    f"Проверьте целостность базы {problem.database_context}."
                )
            if any(kw in sample_desc for kw in ["file cache", "clientfilecache", "файловый кеш"]):
                return (
                    f"❌ Кэш: Ошибки файлового кэша ({count} раз). "
                    f"Очистите кэш клиента 1С и проверьте права доступа к каталогу кэша.{db_context}"
                )

        # 4. Универсальный вывод по слою
        layer_label = {
            "backend": "Backend",
            "vrs": "Веб-сервисы",
            "network": "Сеть",
            "cluster": "Кластер",
            "common": "Система",
        }.get(layer, layer.capitalize())

        base_advice = TechJournalAnalyzer.LAYER_ACTION_MAP.get(
            layer, TechJournalAnalyzer.LAYER_ACTION_MAP["common"]
        )
        return f"❌ {layer_label}: {human_desc} ({count} раз). {base_advice}{db_context}"

    @staticmethod
    def _merge_related_problems(
        groups: dict[str, dict],
    ) -> dict[str, dict]:
        """
        Объединяет проблемы с одинаковым процессом и близким временем.

        Например: descr_10054 + file_RemoteCallListenerImpl.cpp из одного процесса
        → объединяются в descr_10054 с merged_from.
        """
        # Группируем по процессам
        process_sigs: dict[str, list[str]] = {}  # process -> [signatures]
        for key, grp in groups.items():
            for proc in grp["processes"]:
                process_sigs.setdefault(proc, []).append(key)

        merged_keys: set[str] = set()
        for proc, sigs in process_sigs.items():
            if len(sigs) < 2:
                continue
            # Ищем пары: descr_XXXX + file_XXX или hash_XXX
            descr_keys = [s for s in sigs if "descr_" in s.split("::")[1]]
            hash_keys = [s for s in sigs if "::hash_" in s]
            file_keys = [s for s in sigs if "::file_" in s]

            if descr_keys and (hash_keys or file_keys):
                # Объединяем hash/file в descr
                target = descr_keys[0]
                for src in hash_keys + file_keys:
                    if src == target or src in merged_keys:
                        continue
                    # Проверяем временнýю близость (пересечение по timestamps)
                    target_ts = set(groups[target].get("timestamps", []))
                    src_ts = set(groups[src].get("timestamps", []))
                    if target_ts and src_ts:
                        # Если хотя бы 50% событий src в пределах ±60с от target
                        close = 0
                        for ts in src_ts:
                            for t in target_ts:
                                if abs((ts - t).total_seconds()) < 60:
                                    close += 1
                                    break
                        if close < len(src_ts) * 0.3:
                            continue  # не достаточно близки

                    merged_keys.add(src)
                    groups[target]["merged_from"].append(groups[src]["error_signature"])
                    groups[target]["count"] += groups[src]["count"]
                    groups[target]["users"].update(groups[src]["users"])
                    groups[target]["processes"].update(groups[src]["processes"])
                    groups[target]["computers"].update(groups[src]["computers"])
                    groups[target]["durations"].extend(groups[src]["durations"])
                    groups[target]["timestamps"].extend(groups[src]["timestamps"])
                    # Добавляем примеры из src, если есть место
                    remaining = 3 - len(groups[target]["event_samples"])
                    if remaining > 0:
                        for ex in groups[src]["event_samples"][:remaining]:
                            ex_key = (ex.get("description"), ex.get("process"), ex.get("user"))
                            if ex_key not in groups[target].get("_seen_examples", set()):
                                groups[target].setdefault("_seen_examples", set()).add(ex_key)
                                groups[target]["event_samples"].append(ex)

        # Удаляем поглощённые группы
        for key in merged_keys:
            groups.pop(key, None)

        return groups

    @staticmethod
    def _calculate_impact_score(
        count: int,
        severity: str,
        unique_processes: int,
        unique_users: int,
        problem_type: str,
    ) -> float:
        """
        Рассчитывает score влияния проблемы (0-1).

        Факторы:
        - severity weight
        - количество событий (log-шкала)
        - количество затронутых процессов/пользователей
        """
        severity_weights = {"critical": 0.4, "warning": 0.2, "info": 0.05}
        weight = severity_weights.get(severity, 0.1)

        import math

        count_score = min(math.log10(max(count, 1)) / 3, 1.0)  # log-шкала до ~1000
        process_score = min(unique_processes / 5, 1.0)
        user_score = min(unique_users / 10, 1.0)

        score = weight * (0.4 * count_score + 0.3 * process_score + 0.3 * user_score)
        return round(min(score, 1.0), 2)

    @staticmethod
    def _guess_root_cause(
        signature: str,
        problem_type: str,
        merged_from: list[str],
    ) -> str | None:
        """
        Предполагаемая причина на основе сигнатуры.
        """
        if signature.startswith("descr_"):
            code = signature.replace("descr_", "")
            known_causes = {
                "10054": "Network Timeout / Firewall TCP RST — удалённый хост разорвал подключение",
                "10053": "Software caused connection abort — обрыв на уровне ОС",
                "10060": "Connection timed out — таймаут сетевого подключения",
                "10061": "Connection refused — целевой сервис недоступен",
            }
            if code in known_causes:
                return known_causes[code]
            return f"Ошибка платформы (код {code}) — проверьте журнал сервера 1С"

        if signature.startswith("file_"):
            file_name = signature.replace("file_", "")
            base_name = (
                file_name.rsplit(".", 1)[0].lower() if "." in file_name else file_name.lower()
            )

            # Маппинг известных модулей → вероятные причины
            known_module_causes = {
                # ===== Файловый кеш =====
                "clientfilecacheimpl": "Ошибка файлового кеша клиента — проверьте целостность и очистите кеш 1С",
                "filecache": "Ошибка кэширования файлов — возможна фрагментация или нехватка места на диске",
                "filecacheimpl": "Ошибка реализации файлового кеша — проверьте права доступа к каталогу кеша",
                "tempstorage": "Ошибка временного хранилища — проверьте свободное место на диске и TEMP-каталог",
                "tempfilemanager": "Ошибка управления временными файлами — возможна утечка дискового пространства",
                # ===== Сетевые вызовы =====
                "remotecalllistenerimpl": "Ошибка удалённого вызова — разрыв сетевого соединения или таймаут",
                "remotecall": "Ошибка RPC-вызова между компонентами кластера",
                "tcpconnection": "Ошибка TCP-соединения — проверьте сетевую связность и фаервол",
                "httpcall": "Ошибка HTTP-вызова — проверьте доступность веб-сервиса",
                "sockimpl": "Ошибка сокетного соединения — проверьте сетевую инфраструктуру",
                "netpacketimpl": "Ошибка сетевого пакета — возможна фрагментация или потеря данных",
                "httpprotocol": "Ошибка HTTP-протокола — проверьте заголовки и формат запроса",
                "socksproxyimpl": "Ошибка SOCKS-прокси — проверьте настройки прокси-сервера",
                "internetclientproxyimpl": "Ошибка интернет-прокси клиента — проверьте настройки подключения",
                # ===== СУБД =====
                "dbconnection": "Ошибка подключения к СУБД — проверьте доступность сервера БД",
                "dbms": "Ошибка взаимодействия с СУБД — возможна проблема драйвера или сети",
                "sqlquery": "Ошибка выполнения SQL-запроса — проверьте план запроса и индексы",
                "dbengine": "Ошибка движка СУБД — проверьте логи сервера базы данных",
                "dbmssqldriver": "Ошибка драйвера MS SQL — проверьте версию и совместимость",
                "dbpostgresqldriver": "Ошибка драйвера PostgreSQL — проверьте версию и совместимость",
                "dboracledriver": "Ошибка драйвера Oracle — проверьте версию и совместимость",
                "cursordbms": "Ошибка курсора СУБД — возможна проблема с транзакцией",
                "connectpool": "Ошибка пула соединений — проверьте лимиты подключений к СУБД",
                "sqlquerybuilder": "Ошибка построения SQL-запроса — возможна проблема конфигурации",
                # ===== Блокировки =====
                "lockmanager": "Ошибка менеджера блокировок — возможна конкуренция за ресурсы",
                "deadlockdetector": "Обнаружена взаимная блокировка транзакций",
                "tlockimpl": "Ошибка управляемой блокировки — проверьте код конфигурации на конкуренцию",
                "exclusivelock": "Ошибка эксклюзивной блокировки — возможен длительный захват ресурса",
                "sharedlock": "Ошибка разделяемой блокировки — множественный доступ к ресурсу",
                "lockmap": "Ошибка карты блокировок — возможна утечка блокировок",
                # ===== Платформа / ядро =====
                "processmain": "Ошибка основного процесса сервера 1С",
                "rphostmain": "Ошибка рабочего процесса сервера 1С — возможен сбой при обработке запроса",
                "rmngrmain": "Ошибка менеджера кластера — проверьте конфигурацию кластера",
                "rphost": "Ошибка рабочего процесса rphost — проверьте нагрузку и журналы",
                "rmngr": "Ошибка менеджера кластера rmngr — возможна проблема управления сессиями",
                "rphostclusterimpl": "Ошибка кластера рабочих процессов — проверьте масштабирование",
                "servercall": "Ошибка серверного вызова — проверьте доступность сервера",
                "workingprocess": "Ошибка рабочего процесса — возможна перегрузка",
                # ===== Веб-сервисы / VRS =====
                "vrsconnection": "Ошибка соединения VRS — проверьте доступность веб-сервера",
                "wsdefinition": "Ошибка определения веб-сервиса — проверьте WSDL и публикацию",
                "vrshttp": "Ошибка HTTP-обработки VRS — проверьте публикацию на веб-сервере",
                "vrsauth": "Ошибка аутентификации VRS — проверьте учётные данные",
                "wsproxyimpl": "Ошибка прокси веб-сервиса — проверьте маршрут и публикацию",
                # ===== Транзакции =====
                "transaction": "Ошибка транзакции — возможен конфликт параллельного доступа",
                "transimpl": "Ошибка реализации транзакции — проверьте логику начала/завершения",
                "isolatedtransaction": "Ошибка изолированной транзакции — возможна блокировка",
                # ===== Параллелизм / фоновые задания =====
                "threadpool": "Ошибка пула потоков — возможна перегрузка сервера",
                "backgroundjob": "Ошибка фонового задания — проверьте расписание и логику выполнения",
                "backgroundjobimpl": "Ошибка реализации фонового задания — проверьте код обработки",
                "scheduledjob": "Ошибка регламентного задания — проверьте расписание и параметры",
                "jobqueue": "Ошибка очереди заданий — возможна перегрузка или затор",
                "parallelimpl": "Ошибка параллельного выполнения — проверьте распределение нагрузки",
                # ===== Криптография / ЭП =====
                "crypto": "Ошибка криптографии — проверьте сертификаты и ключи",
                "signature": "Ошибка электронной подписи — проверьте срок действия сертификата",
                "cryptimpl": "Ошибка реализации криптографии — проверьте провайдер криптографии",
                "certificatestore": "Ошибка хранилища сертификатов — проверьте наличие и срок действия",
                "certstore": "Ошибка хранилища сертификатов — проверьте наличие и срок действия",
                "signimpl": "Ошибка реализации подписи — проверьте алгоритм и ключ",
                "envelopimpl": "Ошибка шифрования/расшифрования — проверьте ключ и алгоритм",
                "hashimpl": "Ошибка вычисления хэша — проверьте целостность данных",
                # ===== Данные / хранилище =====
                "memory": "Ошибка управления памятью — возможна утечка или нехватка RAM",
                "storage": "Ошибка хранилища данных — проверьте диск и права доступа",
                "dataexchange": "Ошибка обмена данными — проверьте совместимость форматов",
                "datastorage": "Ошибка хранения данных — проверьте целостность БД",
                "indexmanager": "Ошибка индексации — проверьте индексы и статистику СУБД",
                "tableimpl": "Ошибка работы с таблицами — проверьте структуру и индексы",
                # ===== COM / внешние соединения =====
                "comconnection": "Ошибка COM-соединения — проверьте регистрацию COM-объекта",
                "addin": "Ошибка внешней обработки/расширения — проверьте версию и совместимость",
                "addinmanager": "Ошибка менеджера внешних обработок — проверьте наличие и права",
                "addinimpl": "Ошибка реализации внешней обработки — проверьте код и зависимости",
                "comcntr": "Ошибка COM-коннектора — проверьте регистрацию компонента",
                "wsclient": "Ошибка WS-клиента — проверьте endpoint и аутентификацию",
                "httpclient": "Ошибка HTTP-клиента — проверьте доступность целевого сервера",
                "smtpclient": "Ошибка SMTP-клиента — проверьте настройки почтового сервера",
                # ===== Планировщик =====
                "scheduler": "Ошибка планировщика заданий — проверьте расписание",
                "schedulerimpl": "Ошибка реализации планировщика — проверьте конфигурацию расписания",
                # ===== События / логирование =====
                "eventlog": "Ошибка журнала событий — проверьте права записи и свободное место",
                "eventlogimpl": "Ошибка реализации журнала событий — проверьте конфигурацию логирования",
                # ===== Сессии / подключения =====
                "session": "Ошибка сеанса — возможно истечение таймаута",
                "sessionimpl": "Ошибка реализации сеанса — проверьте настройки таймаутов",
                "connection": "Ошибка подключения — проверьте доступность и лимиты",
                "connectionpool": "Ошибка пула подключений — проверьте максимальное количество",
                "auth": "Ошибка аутентификации — проверьте учётные данные и права доступа",
                "authimpl": "Ошибка реализации аутентификации — проверьте провайдер авторизации",
                # ===== Конфигурация =====
                "config": "Ошибка конфигурации — проверьте параметры запуска",
                "configimpl": "Ошибка реализации конфигурации — проверьте целостность конфигурации",
                "infobase": "Ошибка информационной базы — проверьте подключение и целостность",
                "infobaseimpl": "Ошибка реализации ИБ — проверьте параметры подключения",
                # ===== Прочее =====
                "xmlparser": "Ошибка разбора XML — проверьте формат и кодировку документа",
                "jsonparser": "Ошибка разбора JSON — проверьте формат данных",
                "stringtable": "Ошибка строковых ресурсов — проверьте локализацию",
                "file": "Ошибка файловой операции — проверьте права доступа и путь",
                "fileimpl": "Ошибка реализации файловой операции — проверьте путь и права",
                "stream": "Ошибка потока данных — проверьте целостность источника данных",
                "streamimpl": "Ошибка реализации потока — проверьте источник и буфер",
            }

            cause = known_module_causes.get(base_name)
            if cause:
                return f"{cause} [{file_name}]"
            return f"Ошибка в модуле платформы {file_name} — возможна проблема версии платформы"

        if signature.startswith("hash_"):
            hash_val = signature.replace("hash_", "")
            if hash_val in TechJournalAnalyzer.KNOWN_HASH_DESCRIPTIONS:
                return TechJournalAnalyzer.KNOWN_HASH_DESCRIPTIONS[hash_val]
            return None

        if merged_from:
            return f"Комбинированная проблема: {', '.join(merged_from[:2])}"

        return None

    @staticmethod
    def _enrich_root_cause_with_context(
        signature: str, problem_type: str, description: str | None
    ) -> str | None:
        """
        Дополняет possible_root_cause контекстом для hash-сигнатур.

        Анализирует текст описания и возвращает человекочитаемую причину,
        если удалось определить контекст.
        """
        import re

        if not description:
            return None

        desc_lower = description.lower()

        # HTTP-коды (самые специфичные — проверяем первыми)
        import re

        http_match = re.search(r"\b(4\d{2}|5\d{2})\b", description)
        if http_match:
            code = http_match.group(1)
            http_errors = {
                "400": "HTTP 400 Bad Request — неверный формат запроса",
                "401": "HTTP 401 Unauthorized — ошибка аутентификации",
                "403": "HTTP 403 Forbidden — нет доступа к ресурсу",
                "404": "HTTP 404 Not Found — ресурс не найден",
                "408": "HTTP 408 Request Timeout — таймаут запроса",
                "500": "HTTP 500 Internal Server Error — ошибка сервера",
                "502": "HTTP 502 Bad Gateway — ошибка шлюза/прокси",
                "503": "HTTP 503 Service Unavailable — сервис недоступен",
                "504": "HTTP 504 Gateway Timeout — таймаут шлюза",
            }
            return http_errors.get(code, f"HTTP ошибка {code}")

        # СУБД (до таймаутов — более специфично)
        if any(
            kw in desc_lower for kw in ["sql", "запрос", "query", "select", "insert", "update "]
        ):
            if any(kw in desc_lower for kw in ["timeout", "timed out", "превышен"]):
                return "Таймаут SQL-запроса — проверьте план запроса, индексы и статистику СУБД"
            if any(kw in desc_lower for kw in ["deadlock", "взаимн"]):
                return "Взаимная блокировка СУБД — проверьте транзакции и конкурентный доступ"
            if any(kw in desc_lower for kw in ["connection pool", "пул соедин", "max connect"]):
                return "Исчерпан пул соединений СУБД — проверьте лимиты подключений"
            return "Ошибка SQL-запроса — проверьте план запроса, индексы и статистику"
        if any(kw in desc_lower for kw in ["deadlock", "взаимн", "блокировк"]):
            return "Блокировка СУБД — проверьте транзакции и конкурентный доступ"

        # Сетевые ошибки
        if any(kw in desc_lower for kw in ["10054", "tcp rst", "connection reset", "wrp"]):
            return "Сетевая ошибка — разрыв TCP-соединения (TCP RST)"
        if any(kw in desc_lower for kw in ["timeout", "timed out", "превышен"]):
            return "Таймаут соединения — проверьте сетевую связность и фаервол"
        if any(kw in desc_lower for kw in ["refused", "отказ"]):
            return "Подключение отклонено — целевой сервис недоступен"
        if any(kw in desc_lower for kw in ["ssl", "tls", "certificate", "сертификат"]):
            return "Ошибка SSL/TLS — проверьте сертификат и протокол шифрования"

        # Файловые ошибки
        if any(kw in desc_lower for kw in ["file", "файл", "access denied", "доступ"]):
            return "Ошибка файловой операции — проверьте права доступа к файлу/каталогу"
        if any(kw in desc_lower for kw in ["disk", "диск", "no space", "мест"]):
            return "Нехватка дискового пространства — проверьте свободное место"

        # Память
        if any(kw in desc_lower for kw in ["memory", "памят", "out of memory", "нехватк"]):
            return "Нехватка памяти — проверьте утечки и лимиты RAM"

        # Аутентификация
        if any(kw in desc_lower for kw in ["auth", "аутентифик", "password", "парол", "логин"]):
            return "Ошибка аутентификации — проверьте учётные данные"

        # Конфигурация
        if any(kw in desc_lower for kw in ["config", "конфигур", "настройк", "parameter"]):
            return "Ошибка конфигурации — проверьте параметры запуска"

        # COM / внешние
        if any(kw in desc_lower for kw in ["com", "ole", "activex", "внешн"]):
            return "Ошибка COM/OLE-объекта — проверьте регистрацию компонента"

        # Веб-сервисы
        if any(kw in desc_lower for kw in ["http", "web", "webservices", "веб-сервис", "soap"]):
            return "Ошибка веб-сервиса — проверьте публикацию и endpoint"

        return None

    @staticmethod
    def _extract_error_signature(description: str | None) -> str:
        """
        Извлекает сигнатуру ошибки из описания для группировки.

        Приоритет:
        1. Код ошибки descr=XXXXX
        2. Путь к файлу file=src\\...
        3. Хеш первых 80 символов описания
        """
        import re

        if not description:
            return "unknown"

        # 1. Код ошибки: descr=10054
        descr_match = re.search(r"descr=(\d+)", description)
        if descr_match:
            return f"descr_{descr_match.group(1)}"

        # 2. Файл: line=XXXX file=... или file=...
        line_file_match = re.search(r"line=(\d+)\s+file=(.+?)(?:\s|$)", description)
        if line_file_match:
            file_path = line_file_match.group(2)
            file_name = file_path.split("\\")[-1].split("/")[-1]
            return f"file_{file_name}"

        file_match = re.search(r"file=(.+?)(?:\s|$)", description)
        if file_match:
            file_path = file_match.group(1)
            file_name = file_path.split("\\")[-1].split("/")[-1]
            return f"file_{file_name}"

        # 3. Хеш первых 80 символов
        snippet = description[:80].strip()
        snippet_hash = hash(snippet) & 0xFFFFFFFF
        return f"hash_{snippet_hash}"

    # ------------------------------------------------------------------
    # Анализ по категориям
    # ------------------------------------------------------------------

    def _analyze_stability(self, metrics: MetricsResult, insights: list[Insight]) -> None:
        """Анализ стабильности: ошибки и предупреждения."""
        errs = metrics.errors
        if errs.count == 0:
            insights.append(
                Insight(
                    severity="info",
                    category="stability",
                    title="Ошибки отсутствуют",
                    description=f"За период не зафиксировано ошибок (EXCP/RPHOST).",
                )
            )
            return

        t = self.HEALTH_THRESHOLDS
        if errs.count >= t["critical_errors"]:
            insights.append(
                Insight(
                    severity="critical",
                    category="stability",
                    title="Критическое количество ошибок",
                    description=f"Зафиксировано {errs.count} ошибок (EXCP/RPHOST). "
                    f"Затронуто пользователей: {len(errs.users)}, процессов: {len(errs.processes)}.",
                    metric_value=str(errs.count),
                    recommendation="Необходимо срочно проанализировать описания ошибок и определить корневую причину.",
                )
            )
        elif errs.count >= t["warning_errors"]:
            insights.append(
                Insight(
                    severity="warning",
                    category="stability",
                    title="Повышенное количество ошибок",
                    description=f"Зафиксировано {errs.count} ошибок. Затронуто {len(errs.users)} пользователей.",
                    metric_value=str(errs.count),
                    recommendation="Проанализируйте повторяющиеся ошибки в описаниях.",
                )
            )
        else:
            insights.append(
                Insight(
                    severity="info",
                    category="stability",
                    title="Единичные ошибки",
                    description=f"Зафиксировано {errs.count} ошибок — в пределах нормы.",
                    metric_value=str(errs.count),
                )
            )

        # Предупреждения ATTN
        if metrics.warnings.count > 0:
            insights.append(
                Insight(
                    severity="info",
                    category="stability",
                    title="Предупреждения мониторинга",
                    description=f"Зафиксировано {metrics.warnings.count} предупреждений (ATTN).",
                    metric_value=str(metrics.warnings.count),
                )
            )

    def _analyze_locks(self, metrics: MetricsResult, insights: list[Insight]) -> None:
        """Анализ проблем конкурентности: deadlocks, timeouts, long locks."""
        t = self.HEALTH_THRESHOLDS

        # Deadlocks
        if metrics.deadlocks.count > 0:
            if metrics.deadlocks.count >= t["critical_deadlocks"]:
                insights.append(
                    Insight(
                        severity="critical",
                        category="locks",
                        title="Множественные взаимные блокировки",
                        description=f"Зафиксировано {metrics.deadlocks.count} deadlock'ов. "
                        f"Процессы: {', '.join(list(metrics.deadlocks.processes)[:5])}.",
                        metric_value=str(metrics.deadlocks.count),
                        recommendation="Проверьте транзакции на предмет конкуренции за одни и те же таблицы. "
                        "Рассмотрите разнесение по времени фоновых задач.",
                    )
                )
            else:
                insights.append(
                    Insight(
                        severity="warning",
                        category="locks",
                        title="Обнаружены дедлоки",
                        description=f"Зафиксировано {metrics.deadlocks.count} deadlock'ов.",
                        metric_value=str(metrics.deadlocks.count),
                        recommendation="Проанализируйте процессы, создающие блокировки.",
                    )
                )

        # Timeouts
        if metrics.timeouts.count > 0:
            if metrics.timeouts.count >= t["critical_timeouts"]:
                insights.append(
                    Insight(
                        severity="critical",
                        category="locks",
                        title="Массовые таймауты блокировок",
                        description=f"Зафиксировано {metrics.timeouts.count} таймаутов ожидания блокировок.",
                        metric_value=str(metrics.timeouts.count),
                        recommendation="Возможна блокировка ключевого ресурса. Проверьте долгие транзакции.",
                    )
                )
            else:
                insights.append(
                    Insight(
                        severity="warning",
                        category="locks",
                        title="Таймауты блокировок",
                        description=f"Зафиксировано {metrics.timeouts.count} таймаутов.",
                        metric_value=str(metrics.timeouts.count),
                    )
                )

        # Long locks avg duration
        if metrics.long_locks.count > 0:
            avg_ms = metrics.long_locks.avg_duration
            if avg_ms > t["long_locks_avg_ms"]:
                insights.append(
                    Insight(
                        severity="warning",
                        category="locks",
                        title="Длительные управляемые блокировки",
                        description=f"Средняя длительность блокировок: {avg_ms:.0f} мс "
                        f"({metrics.long_locks.count} случаев).",
                        metric_value=f"{avg_ms:.0f} мс",
                        recommendation="Оптимизируйте код, удерживающий блокировки.",
                    )
                )

    def _analyze_sql_performance(self, metrics: MetricsResult, insights: list[Insight]) -> None:
        """Анализ производительности СУБД."""
        t = self.HEALTH_THRESHOLDS

        if metrics.slow_sql.count == 0:
            return

        count = metrics.slow_sql.count
        avg_ms = metrics.slow_sql.avg_duration

        if count >= t["critical_slow_sql"]:
            insights.append(
                Insight(
                    severity="critical",
                    category="sql",
                    title="Критическое количество медленных SQL-запросов",
                    description=f"Зафиксировано {count} медленных SQL-запросов. "
                    f"Средняя длительность: {avg_ms:.0f} мс.",
                    metric_value=str(count),
                    recommendation="Проверьте планы запросов, индексы и актуальность статистики СУБД.",
                )
            )
        elif count >= t["warning_slow_sql"]:
            insights.append(
                Insight(
                    severity="warning",
                    category="sql",
                    title="Повышенное количество медленных SQL-запросов",
                    description=f"Зафиксировано {count} медленных SQL. Средняя длительность: {avg_ms:.0f} мс.",
                    metric_value=str(count),
                    recommendation="Проанализируйте топ запросов по описаниям.",
                )
            )
        else:
            insights.append(
                Insight(
                    severity="info",
                    category="sql",
                    title="Единичные медленные SQL-запросы",
                    description=f"Зафиксировано {count} медленных SQL. Средняя длительность: {avg_ms:.0f} мс.",
                    metric_value=str(count),
                )
            )

        if avg_ms > t["slow_sql_avg_ms"]:
            insights.append(
                Insight(
                    severity="warning",
                    category="sql",
                    title="Высокая средняя длительность SQL",
                    description=f"Среднее время SQL-запроса: {avg_ms:.0f} мс (порог: {t['slow_sql_avg_ms']} мс).",
                    metric_value=f"{avg_ms:.0f} мс",
                    recommendation="Возможна деградация индексов или статистики СУБД.",
                )
            )

    def _analyze_cluster_load(self, metrics: MetricsResult, insights: list[Insight]) -> None:
        """Анализ нагрузки на кластер."""
        # Long calls
        if metrics.long_calls.count > 0:
            avg_ms = metrics.long_calls.avg_duration
            if avg_ms > 10000:  # >10 секунд
                insights.append(
                    Insight(
                        severity="warning",
                        category="load",
                        title="Длительные вызовы кластера",
                        description=f"Средняя длительность RPC-вызовов: {avg_ms:.0f} мс "
                        f"({metrics.long_calls.count} случаев).",
                        metric_value=f"{avg_ms:.0f} мс",
                        recommendation="Кластер может не справляться с нагрузкой. Рассмотрите масштабирование.",
                    )
                )

        # Cluster events
        if metrics.cluster_events.count > 0:
            insights.append(
                Insight(
                    severity="info",
                    category="load",
                    title="События кластера",
                    description=f"Зафиксировано {metrics.cluster_events.count} событий управления кластером.",
                    metric_value=str(metrics.cluster_events.count),
                )
            )

    # ------------------------------------------------------------------
    # Влияние сущностей (пользователи, процессы)
    # ------------------------------------------------------------------

    def _gather_entity_impact(
        self,
        metrics: MetricsResult,
        users: dict[str, UserImpact],
        processes: dict[str, UserImpact],
    ) -> None:
        """
        Собрать детальную статистиву по каждому пользователю и процессу.

        Перечитывает события за период и группирует по сущностям.
        """
        to_time = datetime.now()
        from_time = to_time - timedelta(minutes=5)  # используем период из collect

        # Получаем сырые события через collector
        directories = self._collector.get_log_directories()
        if not directories and self._collector.log_base_path.exists():
            for subdir in ["core", "perf", "locks", "sql", "zabbix"]:
                dir_path = self._collector.log_base_path / subdir
                if dir_path.exists():
                    directories.append(dir_path)

        min_mtime = from_time.timestamp() - 900

        for log_dir in directories:
            parser = TechJournalParser(log_dir)
            for entry in parser.parse_directory(
                from_time=from_time,
                to_time=to_time,
                min_mtime=min_mtime,
                recursive=True,
                limit_files=None,
            ):
                entry_time = entry.timestamp
                if entry_time.tzinfo is not None:
                    entry_time = entry_time.replace(tzinfo=None)
                if entry_time < from_time or entry_time > to_time:
                    continue

                event_upper = entry.event_name.upper()

                for entity_name, entity_type, storage in [
                    (entry.user, "user", users),
                    (entry.process_name, "process", processes),
                ]:
                    if not entity_name:
                        continue
                    if entity_name not in storage:
                        storage[entity_name] = UserImpact(
                            entity=entity_name, entity_type=entity_type
                        )
                    impact = storage[entity_name]
                    impact.total_events += 1

                    if event_upper in ("EXCP", "EXCEPTION", "RPHOST"):
                        impact.errors += 1
                    elif event_upper in ("TDEADLOCK", "DEADLOCK"):
                        impact.deadlocks += 1
                    elif event_upper in ("TTIMEOUT", "TIMEOUT"):
                        impact.timeouts += 1
                    elif event_upper in ("SDBL", "SQL", "DBMSSQL", "DBMSPOSTGRE", "DBMSORACLE"):
                        if entry.duration and entry.duration > 1000000:
                            impact.slow_sql += 1

                    # Пересчитаем error_rate для текущей сущности
                    if impact.total_events > 0:
                        impact.error_rate = round(
                            (impact.errors + impact.deadlocks + impact.timeouts)
                            / impact.total_events
                            * 100,
                            1,
                        )

    @staticmethod
    def _top_entities(entities: dict[str, UserImpact], limit: int) -> list[UserImpact]:
        """Вернуть топ сущностей по суммарному количеству проблемных событий."""

        def severity_score(ui: UserImpact) -> int:
            return ui.errors * 3 + ui.deadlocks * 5 + ui.timeouts * 2 + ui.slow_sql

        sorted_entities = sorted(entities.values(), key=severity_score, reverse=True)
        return sorted_entities[:limit]

    # ------------------------------------------------------------------
    # Оценка здоровья
    # ------------------------------------------------------------------

    def _calculate_health(self, metrics: MetricsResult) -> tuple[int, str]:
        """
        Рассчитать score 0-100 и статус.

        100 = идеально, 0 = катастрофа.
        """
        score = 100
        t = self.HEALTH_THRESHOLDS

        # Ошибки (макс -40 баллов)
        if metrics.errors.count >= t["critical_errors"]:
            score -= 40
        elif metrics.errors.count >= t["warning_errors"]:
            score -= 20
        elif metrics.errors.count > 0:
            score -= 5

        # Дедлоки (макс -25 баллов)
        if metrics.deadlocks.count >= t["critical_deadlocks"]:
            score -= 25
        elif metrics.deadlocks.count >= t["warning_deadlocks"]:
            score -= 12
        elif metrics.deadlocks.count > 0:
            score -= 5

        # Таймауты (макс -20 баллов)
        if metrics.timeouts.count >= t["critical_timeouts"]:
            score -= 20
        elif metrics.timeouts.count >= t["warning_timeouts"]:
            score -= 10

        # Медленный SQL (макс -15 баллов)
        if metrics.slow_sql.count >= t["critical_slow_sql"]:
            score -= 15
        elif metrics.slow_sql.count >= t["warning_slow_sql"]:
            score -= 8

        score = max(0, score)

        if score < 40:
            status = "critical"
        elif score < 70:
            status = "degraded"
        else:
            status = "healthy"

        return score, status

    # ------------------------------------------------------------------
    # Рекомендации
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_recommendations(insights: list[Insight]) -> list[str]:
        """Сформировать список практических рекомендаций."""
        recommendations: list[str] = []

        critical_count = sum(1 for i in insights if i.severity == "critical")
        warning_count = sum(1 for i in insights if i.severity == "warning")

        if critical_count > 0:
            recommendations.append(
                f"⚠️ ОБНАРУЖЕНО {critical_count} критичных проблем(ы). Требуется немедленное вмешательство."
            )

        # Категориальные рекомендации
        categories_seen = {i.category for i in insights if i.severity in ("critical", "warning")}

        if "stability" in categories_seen:
            recommendations.append(
                "📋 Проанализируйте описания ошибок (endpoint /api/events?event_type=EXCP) "
                "для определения корневой причины."
            )

        if "locks" in categories_seen:
            recommendations.append(
                "🔒 Проверьте расписание фоновых заданий — дедлоки часто возникают "
                "при одновременном доступе к одним данным."
            )

        if "sql" in categories_seen:
            recommendations.append(
                "🐬 Выполните обновление статистики и переиндексацию СУБД. "
                "Проверьте планы тяжёлых запросов через технологический журнал SQL."
            )

        if "load" in categories_seen:
            recommendations.append(
                "📈 Рассмотрите горизонтальное масштабирование кластера 1С "
                "или распределение нагрузки по времени."
            )

        if warning_count > 3 and critical_count == 0:
            recommendations.append(
                "📊 Множественные предупреждения могут указывать на системную проблему. "
                "Проверьте недавние изменения в конфигурации или инфраструктуре."
            )

        if not recommendations:
            recommendations.append("✅ Система работает в штатном режиме.")

        return recommendations
