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


class EventStatsResponse(BaseModel):
    """Статистика событий"""

    count: int
    users: List[str] = Field(default_factory=list)
    processes: List[str] = Field(default_factory=list)
    computers: List[str] = Field(default_factory=list)
    avg_duration_ms: float
    descriptions: List[str] = Field(default_factory=list)


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
