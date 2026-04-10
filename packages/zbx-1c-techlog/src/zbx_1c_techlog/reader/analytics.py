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
        "critical_errors": 50,       # >50 ошибок = critical
        "warning_errors": 10,        # >10 ошибок = warning
        "critical_deadlocks": 10,    # >10 дедлоков = critical
        "warning_deadlocks": 3,      # >3 дедлоков = warning
        "critical_timeouts": 30,     # >30 таймаутов = critical
        "warning_timeouts": 10,      # >10 таймаутов = warning
        "critical_slow_sql": 100,    # >100 медленных SQL = critical
        "warning_slow_sql": 20,      # >20 медленных SQL = warning
        "slow_sql_avg_ms": 5000,     # средний SQL >5с = warning
        "long_locks_avg_ms": 3000,   # средняя блокировка >3с = warning
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
        metrics = self._collector.collect(period_minutes=period_minutes, from_time=from_time, to_time=to_time)

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
    # Анализ по категориям
    # ------------------------------------------------------------------

    def _analyze_stability(self, metrics: MetricsResult, insights: list[Insight]) -> None:
        """Анализ стабильности: ошибки и предупреждения."""
        errs = metrics.errors
        if errs.count == 0:
            insights.append(Insight(
                severity="info",
                category="stability",
                title="Ошибки отсутствуют",
                description=f"За период не зафиксировано ошибок (EXCP/RPHOST).",
            ))
            return

        t = self.HEALTH_THRESHOLDS
        if errs.count >= t["critical_errors"]:
            insights.append(Insight(
                severity="critical",
                category="stability",
                title="Критическое количество ошибок",
                description=f"Зафиксировано {errs.count} ошибок (EXCP/RPHOST). "
                            f"Затронуто пользователей: {len(errs.users)}, процессов: {len(errs.processes)}.",
                metric_value=str(errs.count),
                recommendation="Необходимо срочно проанализировать описания ошибок и определить корневую причину.",
            ))
        elif errs.count >= t["warning_errors"]:
            insights.append(Insight(
                severity="warning",
                category="stability",
                title="Повышенное количество ошибок",
                description=f"Зафиксировано {errs.count} ошибок. Затронуто {len(errs.users)} пользователей.",
                metric_value=str(errs.count),
                recommendation="Проанализируйте повторяющиеся ошибки в описаниях.",
            ))
        else:
            insights.append(Insight(
                severity="info",
                category="stability",
                title="Единичные ошибки",
                description=f"Зафиксировано {errs.count} ошибок — в пределах нормы.",
                metric_value=str(errs.count),
            ))

        # Предупреждения ATTN
        if metrics.warnings.count > 0:
            insights.append(Insight(
                severity="info",
                category="stability",
                title="Предупреждения мониторинга",
                description=f"Зафиксировано {metrics.warnings.count} предупреждений (ATTN).",
                metric_value=str(metrics.warnings.count),
            ))

    def _analyze_locks(self, metrics: MetricsResult, insights: list[Insight]) -> None:
        """Анализ проблем конкурентности: deadlocks, timeouts, long locks."""
        t = self.HEALTH_THRESHOLDS

        # Deadlocks
        if metrics.deadlocks.count > 0:
            if metrics.deadlocks.count >= t["critical_deadlocks"]:
                insights.append(Insight(
                    severity="critical",
                    category="locks",
                    title="Множественные взаимные блокировки",
                    description=f"Зафиксировано {metrics.deadlocks.count} deadlock'ов. "
                                f"Процессы: {', '.join(list(metrics.deadlocks.processes)[:5])}.",
                    metric_value=str(metrics.deadlocks.count),
                    recommendation="Проверьте транзакции на предмет конкуренции за одни и те же таблицы. "
                                   "Рассмотрите разнесение по времени фоновых задач.",
                ))
            else:
                insights.append(Insight(
                    severity="warning",
                    category="locks",
                    title="Обнаружены дедлоки",
                    description=f"Зафиксировано {metrics.deadlocks.count} deadlock'ов.",
                    metric_value=str(metrics.deadlocks.count),
                    recommendation="Проанализируйте процессы, создающие блокировки.",
                ))

        # Timeouts
        if metrics.timeouts.count > 0:
            if metrics.timeouts.count >= t["critical_timeouts"]:
                insights.append(Insight(
                    severity="critical",
                    category="locks",
                    title="Массовые таймауты блокировок",
                    description=f"Зафиксировано {metrics.timeouts.count} таймаутов ожидания блокировок.",
                    metric_value=str(metrics.timeouts.count),
                    recommendation="Возможна блокировка ключевого ресурса. Проверьте долгие транзакции.",
                ))
            else:
                insights.append(Insight(
                    severity="warning",
                    category="locks",
                    title="Таймауты блокировок",
                    description=f"Зафиксировано {metrics.timeouts.count} таймаутов.",
                    metric_value=str(metrics.timeouts.count),
                ))

        # Long locks avg duration
        if metrics.long_locks.count > 0:
            avg_ms = metrics.long_locks.avg_duration
            if avg_ms > t["long_locks_avg_ms"]:
                insights.append(Insight(
                    severity="warning",
                    category="locks",
                    title="Длительные управляемые блокировки",
                    description=f"Средняя длительность блокировок: {avg_ms:.0f} мс "
                                f"({metrics.long_locks.count} случаев).",
                    metric_value=f"{avg_ms:.0f} мс",
                    recommendation="Оптимизируйте код, удерживающий блокировки.",
                ))

    def _analyze_sql_performance(self, metrics: MetricsResult, insights: list[Insight]) -> None:
        """Анализ производительности СУБД."""
        t = self.HEALTH_THRESHOLDS

        if metrics.slow_sql.count == 0:
            return

        count = metrics.slow_sql.count
        avg_ms = metrics.slow_sql.avg_duration

        if count >= t["critical_slow_sql"]:
            insights.append(Insight(
                severity="critical",
                category="sql",
                title="Критическое количество медленных SQL-запросов",
                description=f"Зафиксировано {count} медленных SQL-запросов. "
                            f"Средняя длительность: {avg_ms:.0f} мс.",
                metric_value=str(count),
                recommendation="Проверьте планы запросов, индексы и актуальность статистики СУБД.",
            ))
        elif count >= t["warning_slow_sql"]:
            insights.append(Insight(
                severity="warning",
                category="sql",
                title="Повышенное количество медленных SQL-запросов",
                description=f"Зафиксировано {count} медленных SQL. Средняя длительность: {avg_ms:.0f} мс.",
                metric_value=str(count),
                recommendation="Проанализируйте топ запросов по описаниям.",
            ))
        else:
            insights.append(Insight(
                severity="info",
                category="sql",
                title="Единичные медленные SQL-запросы",
                description=f"Зафиксировано {count} медленных SQL. Средняя длительность: {avg_ms:.0f} мс.",
                metric_value=str(count),
            ))

        if avg_ms > t["slow_sql_avg_ms"]:
            insights.append(Insight(
                severity="warning",
                category="sql",
                title="Высокая средняя длительность SQL",
                description=f"Среднее время SQL-запроса: {avg_ms:.0f} мс (порог: {t['slow_sql_avg_ms']} мс).",
                metric_value=f"{avg_ms:.0f} мс",
                recommendation="Возможна деградация индексов или статистики СУБД.",
            ))

    def _analyze_cluster_load(self, metrics: MetricsResult, insights: list[Insight]) -> None:
        """Анализ нагрузки на кластер."""
        # Long calls
        if metrics.long_calls.count > 0:
            avg_ms = metrics.long_calls.avg_duration
            if avg_ms > 10000:  # >10 секунд
                insights.append(Insight(
                    severity="warning",
                    category="load",
                    title="Длительные вызовы кластера",
                    description=f"Средняя длительность RPC-вызовов: {avg_ms:.0f} мс "
                                f"({metrics.long_calls.count} случаев).",
                    metric_value=f"{avg_ms:.0f} мс",
                    recommendation="Кластер может не справляться с нагрузкой. Рассмотрите масштабирование.",
                ))

        # Cluster events
        if metrics.cluster_events.count > 0:
            insights.append(Insight(
                severity="info",
                category="load",
                title="События кластера",
                description=f"Зафиксировано {metrics.cluster_events.count} событий управления кластером.",
                metric_value=str(metrics.cluster_events.count),
            ))

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
                        impact.slow_sql += 1

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
