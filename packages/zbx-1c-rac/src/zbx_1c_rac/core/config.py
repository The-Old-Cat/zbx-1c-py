"""Конфигурация для zbx-1c-rac"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


def get_project_root() -> Path:
    """Получить корневую директорию проекта"""
    return Path(__file__).resolve().parent.parent.parent.parent.parent


class RacConfig(BaseSettings):
    """Настройки для мониторинга через RAC"""

    # RAC configuration
    rac_path: Path = Field(default=Path("rac"), validation_alias="RAC_PATH")
    rac_host: str = Field(default="127.0.0.1", validation_alias="RAC_HOST")
    rac_port: int = Field(default=1545, validation_alias="RAC_PORT")

    # Authentication (optional)
    user_name: Optional[str] = Field(default=None, validation_alias="USER_NAME")
    user_pass: Optional[str] = Field(default=None, validation_alias="USER_PASS")

    # Logging
    log_path: Path = Field(default=Path("./logs"), validation_alias="LOG_PATH")
    debug: bool = Field(default=False, validation_alias="DEBUG")

    # Timeouts (seconds)
    rac_timeout: int = Field(default=30, validation_alias="RAC_TIMEOUT")
    command_timeout: int = Field(default=60, validation_alias="COMMAND_TIMEOUT")

    # Cache settings
    cache_ttl: int = Field(default=300, validation_alias="CACHE_TTL")

    # Session limit (number of licenses, set manually)
    session_limit: int = Field(default=100, validation_alias="SESSION_LIMIT")

    model_config = SettingsConfigDict(
        env_file=get_project_root() / ".env.rac",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("rac_path", mode="before")
    @classmethod
    def validate_rac_path(cls, v):
        """Проверка существования rac с учетом кроссплатформенности"""
        if isinstance(v, str):
            v = Path(v)

        if not v.exists():
            # Пробуем найти в PATH
            import shutil

            which_rac = shutil.which("rac")
            if which_rac:
                return Path(which_rac)

            # Если не нашли, возвращаем как есть
            return v

        return v

    @field_validator("log_path", mode="before")
    @classmethod
    def create_log_path(cls, v):
        """Создание директории для логов если её нет"""
        if isinstance(v, str):
            v = Path(v)
        v.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("rac_port")
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError(f"Invalid port number: {v}")
        return v


@lru_cache
def get_config() -> RacConfig:
    """Получение настроек с кэшированием"""
    return RacConfig()


# Для обратной совместимости
config = get_config()
