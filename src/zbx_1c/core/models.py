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
    status: str
    timestamp: datetime = Field(default_factory=datetime.now)

    # Для Zabbix trapper
    def to_zabbix(self) -> List[Dict[str, Any]]:
        return [
            {"key": "zbx1cpy.cluster.total_sessions", "value": self.total_sessions},
            {"key": "zbx1cpy.cluster.active_sessions", "value": self.active_sessions},
            {"key": "zbx1cpy.cluster.total_jobs", "value": self.total_jobs},
            {"key": "zbx1cpy.cluster.active_jobs", "value": self.active_jobs},
            {"key": "zbx1cpy.cluster.total_infobases", "value": self.total_infobases},
            {"key": "zbx1cpy.cluster.status", "value": self.status},
        ]
