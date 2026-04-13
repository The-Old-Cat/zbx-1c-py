#!/usr/bin/env python3
"""FastAPI приложение для мониторинга техжурнала 1С"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from ..core.config import get_config, TechlogConfig
from ..reader.collector import MetricsCollector
from ..reader.discovery import LogStructureDiscovery
from ..reader.analytics import TechJournalAnalyzer

from .schemas import (
    LogStructureResponse,
    LogStructureDir,
    MetricsResponse,
    EventStatsResponse,
    CheckResponse,
    HealthResponse,
    ErrorResponse,
    AnalyticsResponse,
    InsightResponse,
    UserImpactResponse,
    ProblemGroupResponse,
    ProblemExampleResponse,
    ZabbixLldResponse,
    ZabbixLldMetric,
    ProcessesLldResponse,
    ProcessDiscoveryItem,
)

app = FastAPI(
    title="Zabbix 1C TechJournal Monitoring API",
    description="REST API для мониторинга техжурнала 1С",
    version="0.1.0",
)


def get_collector() -> MetricsCollector:
    """Получить сборщик метрик"""
    cfg = get_config()
    return MetricsCollector(cfg.logs_base_path)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Проверка работоспособности API"""
    return HealthResponse(status="ok")


@app.get("/api/structure", response_model=LogStructureResponse)
async def get_structure():
    """
    Получить структуру логов техжурнала

    Автоматически находит все поддиректории с логами.
    """
    collector = get_collector()

    if not collector.log_structure:
        raise HTTPException(status_code=404, detail="Log structure not found")

    directories = {}
    for name, dir_info in collector.log_structure.directories.items():
        directories[name] = LogStructureDir(
            path=str(dir_info.path),
            log_type=dir_info.log_type,
            file_count=dir_info.file_count,
            total_size_mb=round(dir_info.total_size_bytes / 1024 / 1024, 2),
            files=[str(f) for f in dir_info.files[:10]],
        )

    return LogStructureResponse(
        base_path=str(collector.log_structure.base_path),
        directories=directories,
        total_files=collector.log_structure.total_files,
        total_size_mb=round(collector.log_structure.total_size_bytes / 1024 / 1024, 2),
        detected_formats=list(collector.log_structure.detected_formats),
    )


@app.get("/api/metrics", response_model=MetricsResponse)
async def get_metrics(
    period_minutes: int = Query(default=5, ge=1, le=1440, description="Период сбора в минутах")
):
    """
    Получить метрики техжурнала за период

    - **period_minutes**: Период сбора метрик (1-1440 минут)
    """
    collector = get_collector()
    metrics = collector.collect(period_minutes=period_minutes)

    def make_event_stats(stats):
        return EventStatsResponse(
            count=stats.count,
            users=list(stats.users),
            processes=list(stats.processes),
            computers=list(stats.computers),
            avg_duration_ms=stats.avg_duration,
            descriptions=stats.descriptions[:5],  # Первые 5 описаний
            memory_usage_bytes=stats.memory_usage_bytes,
            memory_by_process=stats.memory_by_process_top,
            network_errors=stats.network_errors,
            top_slow_methods=stats.top_slow_methods,
            sql_queries=stats.sql_queries,
        )

    return MetricsResponse(
        timestamp=metrics.timestamp.isoformat(),
        period_seconds=metrics.period_seconds,
        logs_base_path=metrics.logs_base_path,
        total_events=metrics.total_events,
        critical_events=metrics.critical_events,
        errors=make_event_stats(metrics.errors),
        warnings=make_event_stats(metrics.warnings),
        deadlocks=make_event_stats(metrics.deadlocks),
        timeouts=make_event_stats(metrics.timeouts),
        long_locks=make_event_stats(metrics.long_locks),
        long_calls=make_event_stats(metrics.long_calls),
        slow_sql=make_event_stats(metrics.slow_sql),
        cluster_events=make_event_stats(metrics.cluster_events),
        admin_events=make_event_stats(metrics.admin_events),
    )


@app.get("/api/metrics/zabbix", response_model=ZabbixLldResponse)
async def get_metrics_zabbix_lld(
    period_minutes: int = Query(default=5, ge=1, le=1440, description="Период сбора в минутах"),
    hostname: Optional[str] = Query(default=None, description="Имя хоста Zabbix"),
):
    """
    Получить метрики в плоском формате для Zabbix LLD (автообнаружение)

    Возвращает данные в формате:
    [
        {"host": "srv-pinavto01", "key": "1c.excp.count[pinavto_crm]", "value": 779},
        {"host": "srv-pinavto01", "key": "1c.mem.delta[ka_pin_test8]", "value": 120912},
        {"host": "srv-pinavto01", "key": "1c.network.error.10054", "value": 170}
    ]

    - **period_minutes**: Период сбора метрик (1-1440 минут)
    - **hostname**: Имя хоста Zabbix (по умолчанию — hostname сервера)
    """
    import socket

    collector = get_collector()
    metrics = collector.collect(period_minutes=period_minutes)

    if hostname is None:
        hostname = socket.gethostname()

    lld_metrics = metrics.to_zabbix_lld(host=hostname)

    return ZabbixLldResponse(
        timestamp=metrics.timestamp.isoformat(),
        period_minutes=period_minutes,
        hostname=hostname,
        metrics=[ZabbixLldMetric(**m) for m in lld_metrics],
        count=len(lld_metrics),
    )


@app.get("/api/metrics/processes", response_model=ProcessesLldResponse)
async def get_processes_for_lld(
    period_minutes: int = Query(default=5, ge=1, le=1440, description="Период сбора в минутах"),
):
    """
    Получить список процессов для Zabbix LLD (Low Level Discovery)

    Возвращает список всех процессов (БД), обнаруженных в логах за период.
    Используется для автообнаружения элементов в Zabbix.

    Формат ответа:
    [
        {"{#PROC_NAME}": "pinavto_crm"},
        {"{#PROC_NAME}": "ka_pin_test8"},
        {"{#PROC_NAME}": "pinavto_test10"}
    ]

    Это позволяет в Zabbix один раз создать шаблон, который автоматически
    подцепит все базы и будет рисовать по ним отдельные графики ошибок и памяти.

    - **period_minutes**: Период сбора метрик (1-1440 минут)
    """
    collector = get_collector()
    processes = collector.get_processes_for_lld(period_minutes=period_minutes)

    metrics = collector.collect(period_minutes=period_minutes)

    return ProcessesLldResponse(
        timestamp=metrics.timestamp.isoformat(),
        period_minutes=period_minutes,
        processes=[ProcessDiscoveryItem(**p) for p in processes],
        count=len(processes),
    )


@app.get("/api/check", response_model=CheckResponse)
async def check_logs():
    """
    Проверка доступности логов техжурнала

    Проверяет существование директорий и файлов.
    """
    cfg = get_config()
    log_path = cfg.logs_base_path

    collector = get_collector()

    directories = []
    if collector.log_structure:
        for name, dir_info in collector.log_structure.directories.items():
            directories.append(
                {
                    "name": name,
                    "path": str(dir_info.path),
                    "file_count": dir_info.file_count,
                    "size_mb": round(dir_info.total_size_bytes / 1024 / 1024, 2),
                }
            )

    return CheckResponse(
        base_path=str(log_path),
        exists=log_path.exists(),
        directories=directories,
        total_files=collector.log_structure.total_files if collector.log_structure else 0,
        total_size_mb=round(
            (collector.log_structure.total_size_bytes if collector.log_structure else 0)
            / 1024
            / 1024,
            2,
        ),
    )


@app.get("/api/summary")
async def get_summary(
    period_minutes: int = Query(default=5, ge=1, le=1440, description="Период сбора в минутах")
):
    """
    Получить текстовую сводку по техжурналу
    """
    collector = get_collector()
    summary = collector.get_summary(period_minutes=period_minutes)

    return {
        "summary": summary,
        "period_minutes": period_minutes,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/zabbix-data")
async def get_zabbix_data(
    period_minutes: int = Query(default=5, ge=1, le=1440, description="Период сбора в минутах"),
    hostname: Optional[str] = Query(default=None, description="Имя хоста Zabbix"),
):
    """
    Получить данные в формате для Zabbix sender

    Возвращает список кортежей (key, value) для отправки.
    """
    import socket

    collector = get_collector()
    metrics_list = collector.collect_for_zabbix(period_minutes=period_minutes, host=hostname)

    if hostname is None:
        hostname = socket.gethostname()

    return {
        "hostname": hostname,
        "period_minutes": period_minutes,
        "timestamp": datetime.now().isoformat(),
        "metrics": [{"key": key, "value": value} for key, value in metrics_list],
        "count": len(metrics_list),
    }


@app.get("/api/events")
async def get_events(
    period_minutes: int = Query(default=1, ge=1, le=1440, description="Период сбора в минутах"),
    event_type: Optional[str] = Query(
        default=None, description="Тип события (EXCP, CALL, TDEADLOCK, ...)"
    ),
    limit: int = Query(default=50, ge=1, le=1000, description="Максимальное количество записей"),
):
    """
    Получить список событий из техжурнала

    - **period_minutes**: Период сбора (1-1440 минут)
    - **event_type**: Фильтр по типу события
    - **limit**: Максимум записей (1-1000)
    """
    from ..reader.parser import TechJournalParser, LogEntry

    collector = get_collector()
    events = []

    # Получаем директории для парсинга
    directories = collector.get_log_directories()
    if not directories and collector.log_base_path.exists():
        # Fallback на стандартные поддиректории
        for subdir in ["core", "perf", "locks", "sql", "zabbix"]:
            dir_path = collector.log_base_path / subdir
            if dir_path.exists():
                directories.append(dir_path)

    to_time = datetime.now()
    from_time = to_time - timedelta(minutes=period_minutes)

    # Оптимизация: читаем только файлы, измененные за последние period_minutes + буфер 15 мин
    min_mtime = from_time.timestamp() - 900  # 15 минут буфера

    # Оптимизация: ограничиваем количество файлов на директорию
    # Для вложенных каталогов увеличиваем лимит (минимум 100 файлов)
    limit_files_per_dir = max(100, limit * 2) if limit < 1000 else limit

    for log_dir in directories:
        if len(events) >= limit:
            break

        parser = TechJournalParser(log_dir)
        # Используем min_mtime и limit_files для оптимизации
        for entry in parser.parse_directory(
            from_time=from_time,
            to_time=to_time,
            min_mtime=min_mtime,
            limit_files=limit_files_per_dir,
        ):
            if event_type and entry.event_name.upper() != event_type.upper():
                continue

            events.append(
                {
                    "timestamp": entry.timestamp.isoformat(),
                    "event_name": entry.event_name,
                    "process_name": entry.process_name,
                    "computer_name": entry.computer_name,
                    "user": entry.user,
                    "description": entry.description[:200] if entry.description else None,
                    "duration_ms": round(entry.duration / 1000, 2) if entry.duration else None,
                    "source_file": entry.source_file,
                }
            )

            if len(events) >= limit:
                break

    return {
        "period_minutes": period_minutes,
        "event_type": event_type,
        "count": len(events),
        "limit": limit,
        "events": events,
    }


def _generate_detailed_recommendations(
    problems: list,
    insights: list,
    period_minutes: int = 5,
) -> list[str]:
    """
    Генерирует детальные рекомендации на основе найденных проблем и инсайтов.

    Использует LAYER_ACTION_MAP из аналитического модуля для формирования
    человекочитаемых советов с привязкой к компоненту 1С.

    Включает:
    - Общую оценку критичности
    - Конкретные рекомендации по каждому типу проблем (через _generate_human_recommendation)
    - Упоминание затронутых процессов и БД
    """
    from ..reader.analytics import TechJournalAnalyzer

    recommendations: list[str] = []

    # --- Общая оценка ---
    critical_problems = [p for p in problems if p.severity == "critical"]
    warning_problems = [p for p in problems if p.severity == "warning"]

    if critical_problems:
        total_critical_count = sum(p.count for p in critical_problems)
        recommendations.append(
            f"⚠️ ОБНАРУЖЕНО {len(critical_problems)} критичных проблем(ы), "
            f"общее количество событий: {total_critical_count}. "
            f"Требуется немедленное вмешательство по направлениям:"
        )
    elif warning_problems:
        recommendations.append(
            f"⚡ Обнаружено {len(warning_problems)} предупреждений. "
            f"Рекомендуется проверить состояние системы."
        )
    else:
        recommendations.append("✅ Система работает в штатном режиме.")
        return recommendations

    # --- Рекомендации по конкретным проблемам (через LAYER_ACTION_MAP) ---
    for problem in problems:
        if problem.severity not in ("critical", "warning"):
            continue

        # Используем человекочитаемую рекомендацию из аналитического модуля
        human_rec = TechJournalAnalyzer._generate_human_recommendation(problem)
        recommendations.append(human_rec)

    # --- Общие рекомендации из инсайтов ---
    categories_seen = {i.category for i in insights if i.severity in ("critical", "warning")}

    if "load" in categories_seen:
        recommendations.append(
            "📈 Рассмотрите масштабирование кластера 1С или распределение нагрузки по времени."
        )

    return recommendations


# --- Далее основной код ---


@app.get("/api/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    period_minutes: int = Query(
        default=5,
        ge=1,
        le=1440,
        description="Период анализа в минутах (1–1440)",
        examples=[5, 15, 60],
    ),
):
    """
    Получить аналитические выводы по техжурналу 1С.

    Автоматически анализирует технологический журнал за указанный период
    и формирует:

    - **health_score** (0–100) — оценка здоровья системы
    - **health_status** — статус: `healthy`, `degraded`, `critical`
    - **insights** — выводы по категориям (стабильность, SQL, блокировки, нагрузка)
    - **problems** — сгруппированные проблемы с:
      - `error_signature` — сигнатура ошибки (descr_XXXX, file_XXX, hash_XXX)
      - `impact_score` — оценка влияния (0–1)
      - `possible_root_cause` — автоопределение причины
      - `event_samples` — до 3 уникальных примеров событий
      - `merged_from` — объединённые сигнатуры
    - **top_impacted_users** / **top_impacted_processes** — с расчётом `error_rate`
    - **recommendations** — практические рекомендации со ссылками на эндпоинты

    ## Примеры использования

    ```
    # Быстрая проверка (5 минут)
    GET /api/analytics?period_minutes=5

    # Анализ за час
    GET /api/analytics?period_minutes=60
    ```

    ## Интерпретация health_score

    | score | статус | действие |
    |-------|--------|----------|
    | 80–100 | healthy | Система работает штатно |
    | 40–79 | degraded | Есть проблемы — см. `problems` |
    | 0–39 | critical | Требуется немедленное вмешательство |
    """
    collector = get_collector()
    analyzer = TechJournalAnalyzer(collector)

    # Аналитика (health, insights, recommendations)
    result = analyzer.analyze(period_minutes=period_minutes)

    # Проблемы (группировка из сырых событий через парсер)
    problem_groups = analyzer.analyze_problems(period_minutes=period_minutes)

    # Преобразуем в response-модели
    problems = [
        ProblemGroupResponse(
            problem_type=pg.problem_type,
            error_signature=pg.error_signature,
            severity=pg.severity,
            count=pg.count,
            unique_users=pg.unique_users,
            unique_processes=pg.unique_processes,
            unique_computers=pg.unique_computers,
            first_seen=pg.first_seen.isoformat() if pg.first_seen else None,
            last_seen=pg.last_seen.isoformat() if pg.last_seen else None,
            avg_duration_ms=pg.avg_duration_ms,
            max_duration_ms=pg.max_duration_ms,
            min_duration_ms=pg.min_duration_ms,
            event_samples=[ProblemExampleResponse(**ex) for ex in pg.event_samples],
            impact_score=pg.impact_score,
            possible_root_cause=pg.possible_root_cause,
            database_context=pg.database_context,
            merged_from=pg.merged_from,
            component_layer=pg.component_layer,
            human_description=pg.human_description,
            trigger_key=pg.trigger_key,
        )
        for pg in problem_groups
    ]

    # Генерируем детальные рекомендации на основе проблем
    detailed_recommendations = _generate_detailed_recommendations(
        problems, result.insights, period_minutes
    )

    def make_insight(ins) -> InsightResponse:
        return InsightResponse(
            severity=ins.severity,
            category=ins.category,
            title=ins.title,
            description=ins.description,
            metric_value=ins.metric_value,
            recommendation=ins.recommendation,
        )

    def make_user_impact(ui) -> UserImpactResponse:
        return UserImpactResponse(
            entity=ui.entity,
            entity_type=ui.entity_type,
            errors=ui.errors,
            deadlocks=ui.deadlocks,
            timeouts=ui.timeouts,
            slow_sql=ui.slow_sql,
            total_events=ui.total_events,
            error_rate=ui.error_rate,
        )

    return AnalyticsResponse(
        timestamp=result.timestamp,
        period_minutes=result.period_minutes,
        health_score=result.health_score,
        health_status=result.health_status,
        insights=[make_insight(i) for i in result.insights],
        problems=problems,
        top_impacted_users=[make_user_impact(u) for u in result.top_impacted_users],
        top_impacted_processes=[make_user_impact(p) for p in result.top_impacted_processes],
        recommendations=detailed_recommendations,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc: Exception):
    """Обработчик необработанных исключений"""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error=str(exc), detail="Internal server error").model_dump(),
    )
