"""Pydantic схемы для API техжурнала"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LogStructureDir(BaseModel):
    """Информация о директории с логами"""

    path: str
    log_type: str
    file_count: int
    total_size_mb: float
    files: List[str] = Field(default_factory=list)


class LogStructureResponse(BaseModel):
    """Структура логов техжурнала"""

    base_path: str
    directories: Dict[str, LogStructureDir]
    total_files: int
    total_size_mb: float
    detected_formats: List[str] = Field(default_factory=list)


class SlowMethodInfo(BaseModel):
    """Информация о медленном методе"""

    method: str
    count: int
    total_duration_ms: float
    avg_duration_ms: float


class MemoryByProcessInfo(BaseModel):
    """Информация о потреблении памяти процессом"""

    process: str
    value: int


class SqlTableInfo(BaseModel):
    """Информация о SQL-таблице 1С"""

    table: str = Field(..., description="Имя таблицы (T123, S456...)")
    hint: str = Field(..., description="Тип объекта метаданных (Документ, Справочник...)")
    count: int = Field(..., description="Количество обращений")
    avg_duration_ms: float = Field(..., description="Средняя длительность запроса")
    max_duration_ms: float = Field(..., description="Максимальная длительность запроса")


class EventStatsResponse(BaseModel):
    """Статистика событий"""

    count: int
    users: List[str] = Field(default_factory=list)
    processes: List[str] = Field(default_factory=list)
    computers: List[str] = Field(default_factory=list)
    avg_duration_ms: float
    descriptions: List[str] = Field(default_factory=list)
    memory_usage_bytes: int = Field(default=0, description="Суммарное потребление памяти в байтах")
    memory_by_process: List[MemoryByProcessInfo] = Field(
        default_factory=list, description="Топ-3 процесса по потреблению памяти"
    )
    network_errors: int = Field(
        default=0, description="Количество сетевых ошибок (10054, 10053...)"
    )
    top_slow_methods: List[SlowMethodInfo] = Field(
        default_factory=list, description="Топ-5 самых медленных методов"
    )
    sql_queries: List[str] = Field(
        default_factory=list, description="Тексты SQL-запросов (для slow_sql, первые 200 симв.)"
    )
    sql_tables: List[SqlTableInfo] = Field(
        default_factory=list,
        description="Топ SQL-таблиц с расшифровкой типа объекта метаданных",
    )


class MetricsResponse(BaseModel):
    """Метрики техжурнала"""

    timestamp: str
    period_seconds: int
    logs_base_path: str

    total_events: int
    critical_events: int

    errors: EventStatsResponse
    warnings: EventStatsResponse
    deadlocks: EventStatsResponse
    timeouts: EventStatsResponse
    long_locks: EventStatsResponse
    long_calls: EventStatsResponse
    slow_sql: EventStatsResponse
    cluster_events: EventStatsResponse
    admin_events: EventStatsResponse


class LogEntryResponse(BaseModel):
    """Запись лога"""

    timestamp: str
    event_name: str
    process_name: Optional[str] = None
    computer_name: Optional[str] = None
    user: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    format: str
    source_file: Optional[str] = None


class ParserStatsResponse(BaseModel):
    """Статистика парсинга"""

    total_lines: int
    parsed_lines: int
    failed_lines: int
    formats: List[str] = Field(default_factory=list)
    event_types: List[str] = Field(default_factory=list)


class CheckResponse(BaseModel):
    """Результат проверки логов"""

    base_path: str
    exists: bool
    directories: List[Dict[str, Any]] = Field(default_factory=list)
    total_files: int
    total_size_mb: float


class HealthResponse(BaseModel):
    """Health check"""

    status: str
    version: str = "0.1.0"


class ErrorResponse(BaseModel):
    """Ошибка"""

    error: str
    detail: Optional[str] = None


class ZabbixLldMetric(BaseModel):
    """Отдельная метрика для Zabbix LLD"""

    host: str
    key: str
    value: Any


class ZabbixLldResponse(BaseModel):
    """Ответ эндпоинта /api/metrics/zabbix"""

    timestamp: str
    period_minutes: int
    hostname: str
    metrics: List[ZabbixLldMetric]
    count: int


# ---------------------------------------------------------------
# Аналитика
# ---------------------------------------------------------------


class InsightResponse(BaseModel):
    """Отдельный аналитический вывод"""

    severity: str = Field(..., description="Критичность: `critical`, `warning`, `info`")
    category: str = Field(..., description="Категория: `stability`, `locks`, `sql`, `load`")
    title: str = Field(..., description="Краткий заголовок вывода")
    description: str = Field(..., description="Развёрнутое описание с цифрами")
    metric_value: Optional[str] = Field(None, description="Числовое значение метрики")
    recommendation: str = Field("", description="Что делать (может быть пустым для info)")


class UserImpactResponse(BaseModel):
    """Влияние конкретного пользователя/процесса"""

    entity: str = Field(..., description="Имя пользователя или процесса (БД)")
    entity_type: str = Field(..., description="Тип сущности: `user` или `process`")
    errors: int = Field(0, description="Количество ошибок (EXCP/EXCEPTION/RPHOST)")
    deadlocks: int = Field(0, description="Количество дедлоков (TDEADLOCK)")
    timeouts: int = Field(0, description="Количество таймаутов (TTIMEOUT)")
    slow_sql: int = Field(0, description="Количество медленных SQL-запросов")
    total_events: int = Field(0, description="Общее количество событий из техжурнала")
    error_rate: float = Field(
        0.0,
        description=(
            "Процент ошибок: `(errors + deadlocks + timeouts) / total_events × 100`. "
            ">10% — требует внимания, >30% — критично"
        ),
    )


class ProblemExampleResponse(BaseModel):
    """Пример проблемы для диагностики"""

    timestamp: Optional[str] = Field(None, description="Время конкретного события (ISO 8601)")
    user: Optional[str] = Field(None, description="Пользователь, вызвавший событие")
    process: Optional[str] = Field(None, description="Процесс (имя БД)")
    computer: Optional[str] = Field(None, description="Имя сервера/компьютера")
    description: Optional[str] = Field(
        None, description="Описание события (первые 300 символов). Для ошибок — текст исключения"
    )
    duration_ms: Optional[float] = Field(None, description="Длительность события в мс")
    sql: Optional[str] = Field(
        None, description="Текст SQL-запроса (только для slow_sql, 500 симв.)"
    )


class ProblemGroupResponse(BaseModel):
    """Группа однотипных проблем"""

    problem_type: str = Field(
        ...,
        description=("Тип: `error`, `deadlock`, `timeout`, `slow_sql`, `long_lock`, `long_call`"),
    )
    error_signature: str = Field(
        ...,
        description=(
            "Сигнатура ошибки — ключ группировки. "
            "Форматы: `descr_XXXX` (код ошибки), `file_XXX.cpp`, `hash_XXXXXXXX`, `unknown`"
        ),
    )
    severity: str = Field(..., description="Критичность: `critical`, `warning`, `info`")
    count: int = Field(..., description="Количество повторений этой проблемы за период")
    unique_users: List[str] = Field(default_factory=list, description="Уникальные пользователи")
    unique_processes: List[str] = Field(
        default_factory=list, description="Уникальные процессы (имена БД)"
    )
    unique_computers: List[str] = Field(
        default_factory=list, description="Уникальные серверы/компьютеры"
    )
    first_seen: Optional[str] = Field(
        None, description="Время первого появления проблемы (ISO 8601)"
    )
    last_seen: Optional[str] = Field(
        None, description="Время последнего появления проблемы (ISO 8601)"
    )
    avg_duration_ms: Optional[float] = Field(
        None, description="Средняя длительность в мс. null если не измеряется"
    )
    max_duration_ms: Optional[float] = Field(
        None, description="Максимальная длительность в мс — самый тяжёлый случай"
    )
    min_duration_ms: Optional[float] = Field(None, description="Минимальная длительность в мс")
    event_samples: List[ProblemExampleResponse] = Field(
        default_factory=list,
        description="До 3 уникальных выборок событий-представителей этой проблемы",
    )
    impact_score: float = Field(
        0.0,
        description=(
            "Оценка влияния (0–1). Рассчитывается из критичности, "
            "количества событий (log-шкала), числа процессов и пользователей"
        ),
    )
    possible_root_cause: Optional[str] = Field(
        None,
        description=(
            "Предполагаемая причина — автоопределение по сигнатуре. "
            "Напр.: `Network Timeout / Firewall TCP RST`"
        ),
    )
    database_context: List[str] = Field(
        default_factory=list,
        description="Имена БД (из unique_processes), затронутых проблемой",
    )
    merged_from: List[str] = Field(
        default_factory=list,
        description=(
            "Объединённые сигнатуры. Если несколько разных сигнатур объединены "
            "в одну проблему (напр. hash_XXX → descr_10054), здесь перечислены поглощённые"
        ),
    )
    component_layer: Optional[str] = Field(
        None,
        description=(
            "Подсистема 1С, определённая по пути к файлу ошибки. "
            "Возможные значения: `backend` (сервер приложений), `vrs` (веб-сервисы), "
            "`network` (сетевой транспорт), `cluster` (администрирование), "
            "`database` (СУБД), `filesystem` (файловые операции), "
            "`security` (криптография/аутентификация), `debug` (отладка), `common` (прочее)"
        ),
    )
    human_description: Optional[str] = Field(
        None,
        description=(
            "Человекочитаемое описание проблемы. "
            "Примеры: `Network Timeout (TCP RST) [34x]`, `Module error: rphost [5x]`"
        ),
    )
    trigger_key: Optional[str] = Field(
        None,
        description=(
            "Стабильный Zabbix-friendly ключ для триггеров. "
            "Примеры: `error_descr_10054`, `error_file_rphost`, `sql_slow`"
        ),
    )


class AnalyticsResponse(BaseModel):
    """Ответ эндпоинта аналитики"""

    timestamp: str = Field(..., description="Время формирования отчёта (ISO 8601)")
    period_minutes: int = Field(..., description="Период анализа в минутах")
    health_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Оценка здоровья системы (0–100). 100 = всё отлично, 0 = критическое",
    )
    health_status: str = Field(
        ...,
        description="Статус: `healthy` (штатно), `degraded` (есть проблемы), `critical` (критично)",
    )
    insights: List[InsightResponse] = Field(
        default_factory=list,
        description="Аналитические выводы по категориям (стабильность, SQL, блокировки...)",
    )
    problems: List[ProblemGroupResponse] = Field(
        default_factory=list,
        description="Сгруппированные проблемы с деталями, отсортированные по критичности",
    )
    top_impacted_users: List[UserImpactResponse] = Field(
        default_factory=list, description="Топ пользователей, наиболее пострадавших от проблем"
    )
    top_impacted_processes: List[UserImpactResponse] = Field(
        default_factory=list,
        description="Топ процессов с наибольшим количеством ошибок (сортировка по error_rate)",
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description=(
            "Практические рекомендации. Содержат конкретные данные: "
            "коды ошибок, процессы, ссылки на эндпоинты для детализации"
        ),
    )


class ProcessDiscoveryItem(BaseModel):
    """Элемент обнаружения процесса для Zabbix LLD"""

    proc_name: str = Field(
        ..., alias="{#PROC_NAME}", description="Имя процесса (макрос Zabbix LLD)"
    )


class ProcessesLldResponse(BaseModel):
    """Ответ эндпоинта /api/metrics/processes для Zabbix LLD"""

    timestamp: str = Field(..., description="Время формирования ответа (ISO 8601)")
    period_minutes: int = Field(..., description="Период анализа в минутах")
    processes: List[ProcessDiscoveryItem] = Field(
        default_factory=list,
        description="Список обнаруженных процессов в формате Zabbix LLD",
    )
    count: int = Field(..., description="Количество обнаруженных процессов")
