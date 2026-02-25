from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ClusterInfo(BaseModel):
    """Информация о кластере 1С"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    host: str
    port: int
    status: str
    description: Optional[str] = None

    # Для Zabbix LLD
    def to_lld(self) -> Dict[str, Any]:
        return {
            "{#CLUSTER.ID}": str(self.id),
            "{#CLUSTER.NAME}": self.name,
            "{#CLUSTER.HOST}": self.host,
            "{#CLUSTER.PORT}": self.port,
            "{#CLUSTER.STATUS}": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClusterInfo":
        """Создание из словаря"""
        # Пробуем получить ID из разных полей
        cluster_id = data.get("cluster") or data.get("id")
        if not cluster_id:
            raise ValueError("Cluster ID not found in data")

        return cls(
            id=UUID(str(cluster_id)),
            name=data.get("name", "unknown"),
            host=data.get("host", "localhost"),
            port=int(data.get("port", 1541)),
            status=data.get("status", "unknown"),
            description=data.get("description", data.get("desc")),
        )


class SessionInfo(BaseModel):
    """Информация о сессии"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    session_id: UUID = Field(..., alias="session")
    session_id_num: Optional[int] = Field(None, alias="session-id")
    user_name: str = Field(..., alias="user-name")
    host: str
    app_id: str = Field(..., alias="app-id")
    started_at: datetime = Field(..., alias="started-at")
    last_active_at: datetime = Field(..., alias="last-active-at")
    duration: int
    db_name: str = Field(..., alias="infobase")
    connection: str
    hibernate: str
    blocked_by_dbms: int = Field(0, alias="blocked-by-dbms")
    blocked_by_ls: int = Field(0, alias="blocked-by-ls")

    @property
    def is_active(self) -> bool:
        """Проверка активности сессии"""
        return self.hibernate == "no"


class JobInfo(BaseModel):
    """Информация о фоновом задании"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    job_id: UUID = Field(..., alias="job")
    name: str
    user_name: str = Field(..., alias="user-name")
    started_at: datetime = Field(..., alias="started-at")
    status: str
    duration: int
    infobase: str

    @property
    def is_running(self) -> bool:
        """Проверка выполнения задания"""
        return self.status == "running"


class InfobaseInfo(BaseModel):
    """Информация об информационной базе"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    infobase: UUID
    name: str
    descr: str = ""


class WorkingServerInfo(BaseModel):
    """Информация о рабочем сервере 1С
    
    Архитектура:
    - Рабочий сервер — узел с агентом ragent (хост)
    - На сервере запускается N рабочих процессов rphost.exe
    - connections-limit — лимит сессий НА ОДИН процесс
    - Общий лимит сервера = connections-limit × processes_count
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    name: str = ""
    host: str
    port: int
    status: str = "unknown"  # working / not-working
    memory_used: int = Field(default=0, alias="memory-used")  # в КБ
    memory_limit: int = Field(default=0, alias="memory-limit")  # в КБ
    start_time: Optional[datetime] = Field(None, alias="start-time")
    current_connections: int = Field(default=0, alias="current-connections")
    limit_connections: int = Field(default=0, alias="limit-connections")
    cluster_id: Optional[UUID] = Field(None, alias="cluster")
    
    # Количество рабочих процессов на сервере (rphost)
    # Используется для расчета общего лимита сессий
    processes_count: int = 1

    @property
    def memory_percent(self) -> float:
        """Процент использования памяти"""
        if self.memory_limit > 0:
            return round((self.memory_used / self.memory_limit) * 100, 2)
        return 0.0

    @property
    def session_percent(self) -> float:
        """Процент использования сессий"""
        if self.limit_connections > 0:
            return round((self.current_connections / self.limit_connections) * 100, 2)
        return 0.0

    @property
    def uptime_minutes(self) -> Optional[int]:
        """Время работы сервера в минутах"""
        if not self.start_time:
            return None
        now = datetime.now()
        start = self.start_time
        if start.tzinfo:
            now = now.replace(tzinfo=start.tzinfo)
        delta = now - start
        return int(delta.total_seconds() / 60)

    def is_recently_restarted(self, threshold_minutes: int = 5) -> bool:
        """Проверка: сервер был перезапущен недавно (< threshold_minutes минут)"""
        uptime = self.uptime_minutes
        return uptime is not None and uptime < threshold_minutes

    def to_lld(self) -> Dict[str, Any]:
        """Формат для Zabbix LLD"""
        return {
            "{#SERVER.NAME}": self.name,
            "{#SERVER.HOST}": self.host,
            "{#SERVER.PORT}": self.port,
            "{#SERVER.STATUS}": self.status,
            "{#SERVER.CLUSTER.ID}": str(self.cluster_id) if self.cluster_id else "",
        }


class ClusterMetrics(BaseModel):
    """Метрики кластера"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    cluster_id: UUID
    cluster_name: str
    total_sessions: int
    active_sessions: int
    total_jobs: int
    active_jobs: int
    total_infobases: int = 0
    # Метрики рабочих серверов
    total_servers: int = 0
    working_servers: int = 0
    total_server_memory_used: int = 0  # суммарная память всех серверов (КБ)
    total_server_memory_limit: int = 0  # суммарный лимит памяти (КБ)
    total_server_session_limit: int = 0  # суммарный лимит сессий по всем серверам
    servers_restarted_recently: int = 0  # количество серверов, перезапущенных <5 мин назад
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def server_memory_percent(self) -> float:
        """Процент использования памяти всеми серверами"""
        if self.total_server_memory_limit > 0:
            return round((self.total_server_memory_used / self.total_server_memory_limit) * 100, 2)
        return 0.0

    # Для Zabbix trapper
    def to_zabbix(self) -> List[Dict[str, Any]]:
        return [
            {"key": "zbx1cpy.cluster.total_sessions", "value": self.total_sessions},
            {"key": "zbx1cpy.cluster.active_sessions", "value": self.active_sessions},
            {"key": "zbx1cpy.cluster.total_jobs", "value": self.total_jobs},
            {"key": "zbx1cpy.cluster.active_jobs", "value": self.active_jobs},
            {"key": "zbx1cpy.cluster.total_infobases", "value": self.total_infobases},
            {"key": "zbx1cpy.cluster.total_servers", "value": self.total_servers},
            {"key": "zbx1cpy.cluster.working_servers", "value": self.working_servers},
            {"key": "zbx1cpy.cluster.server_memory_percent", "value": self.server_memory_percent},
            {"key": "zbx1cpy.cluster.servers_restarted_recently", "value": self.servers_restarted_recently},
        ]
