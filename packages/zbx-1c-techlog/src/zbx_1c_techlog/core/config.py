"""Конфигурация для zbx-1c-techlog"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


def get_project_root() -> Path:
    """
    Получить корневую директорию проекта.

    __file__ = packages/zbx-1c-techlog/src/zbx_1c_techlog/core/config.py
    Нужно подняться на 6 уровней вверх до корня проекта
    """
    return Path(__file__).resolve().parent.parent.parent.parent.parent.parent


class TechlogConfig(BaseSettings):
    """Настройки для мониторинга через техжурнал"""

    # Techjournal log base path
    techjournal_log_base: Optional[Path] = Field(
        default=None, validation_alias="TECHJOURNAL_LOG_BASE"
    )

    # Logging
    log_path: Path = Field(default=Path("./logs"), validation_alias="LOG_PATH")
    debug: bool = Field(default=False, validation_alias="DEBUG")

    # Zabbix settings
    zabbix_server: str = Field(default="127.0.0.1", validation_alias="ZABBIX_SERVER")
    zabbix_port: int = Field(default=10051, validation_alias="ZABBIX_PORT")
    zabbix_sender_path: Optional[str] = Field(
        default=None, validation_alias="ZABBIX_SENDER_PATH"
    )

    # Zabbix API (optional)
    zabbix_use_api: bool = Field(default=False, validation_alias="ZABBIX_USE_API")
    zabbix_api_url: Optional[str] = Field(
        default=None, validation_alias="ZABBIX_API_URL"
    )
    zabbix_api_token: Optional[str] = Field(
        default=None, validation_alias="ZABBIX_API_TOKEN"
    )

    model_config = SettingsConfigDict(
        env_file=get_project_root() / ".env.techlog",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("log_path", mode="before")
    @classmethod
    def create_log_path(cls, v):
        """Создание директории для логов если её нет"""
        if isinstance(v, str):
            v = Path(v)
        v.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("techjournal_log_base", mode="before")
    @classmethod
    def validate_techjournal_path(cls, v):
        """Проверка пути к техжурналу"""
        if v is None:
            return None
        if isinstance(v, str):
            v = Path(v)
        return v

    @property
    def logs_base_path(self) -> Path:
        """Получить базовый путь к логам техжурнала"""
        if self.techjournal_log_base:
            return self.techjournal_log_base

        # Пытаемся определить из LOG_PATH
        return self.log_path.parent / "1c_techjournal"


@lru_cache
def get_config() -> TechlogConfig:
    """Получение настроек с кэшированием"""
    return TechlogConfig()


# Для обратной совместимости
config = get_config()
