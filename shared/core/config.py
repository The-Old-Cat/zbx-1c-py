"""
Базовые классы конфигурации для проектов zbx-1c.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


def get_project_root() -> Path:
    """Получить корневую директорию проекта"""
    return Path(__file__).resolve().parent.parent.parent.parent


class BaseConfig(BaseSettings):
    """
    Базовый класс конфигурации.

    Наследуйте от этого класса для создания специфичных конфигов.
    """

    # Общие настройки
    log_path: Path = Field(default=Path("./logs"), validation_alias="LOG_PATH")
    debug: bool = Field(default=False, validation_alias="DEBUG")

    model_config = SettingsConfigDict(
        env_file=get_project_root() / ".env",
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


@lru_cache
def get_config() -> BaseConfig:
    """Получение конфигурации с кэшированием"""
    return BaseConfig()
