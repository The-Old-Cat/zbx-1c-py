"""Конфигурация для zbx-1c-rac"""

import sys
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


def get_project_root() -> Path:
    """Получить корневую директорию проекта"""
    return Path(__file__).resolve().parent.parent.parent.parent.parent


def get_default_log_path() -> Path:
    """
    Получить путь к директории логов с учетом ОС.
    
    Использует стандартные директории для каждой платформы:
    - Windows: %APPDATA%/zbx-1c-rac/logs/ или ./logs/
    - Linux: /var/log/zbx-1c-rac/ или ~/.local/share/zbx-1c-rac/logs/
    - macOS: ~/Library/Logs/zbx-1c-rac/ или ./logs/
    """
    # Если запущено из виртуального окружения проекта, используем ./logs/
    project_root = get_project_root()
    project_logs = project_root / "logs" / "rac"
    
    # Проверяем, можем ли писать в директорию проекта
    try:
        if project_root.exists() and os.access(project_root, os.W_OK):
            project_logs.mkdir(parents=True, exist_ok=True)
            return project_logs
    except (OSError, PermissionError):
        pass
    
    # Используем стандартные директории ОС
    if sys.platform == "win32":
        # Windows: %APPDATA%/zbx-1c-rac/logs/
        appdata = os.environ.get("APPDATA")
        if appdata:
            log_path = Path(appdata) / "zbx-1c-rac" / "logs"
        else:
            log_path = Path.home() / "AppData" / "Roaming" / "zbx-1c-rac" / "logs"
    elif sys.platform == "darwin":
        # macOS: ~/Library/Logs/zbx-1c-rac/
        log_path = Path.home() / "Library" / "Logs" / "zbx-1c-rac"
    else:
        # Linux: /var/log/zbx-1c-rac/ или ~/.local/share/zbx-1c-rac/logs/
        var_log = Path("/var/log/zbx-1c-rac")
        if os.access(var_log.parent, os.W_OK):
            log_path = var_log
        else:
            # Fallback на домашнюю директорию
            log_path = Path.home() / ".local" / "share" / "zbx-1c-rac" / "logs"
    
    # Создаём директорию
    try:
        log_path.mkdir(parents=True, exist_ok=True)
        return log_path
    except (OSError, PermissionError):
        # Если не удалось создать, возвращаем ./logs/
        return project_logs


def get_default_rac_path() -> Path:
    """Получить путь к rac с учетом ОС"""
    # Пробуем найти в PATH
    import shutil
    which_rac = shutil.which("rac")
    if which_rac:
        return Path(which_rac)
    
    # Пути по умолчанию для разных ОС
    if sys.platform == "win32":
        # Windows: типовой путь к 1C
        default_paths = [
            Path("C:/Program Files/1cv8/8.3.27.1786/bin/rac.exe"),
            Path("C:/Program Files (x86)/1cv8/8.3.27.1786/bin/rac.exe"),
            Path("rac.exe"),
        ]
    else:
        # Linux: типовой путь к 1C
        default_paths = [
            Path("/opt/1C/v8.3/x86_64/rac"),
            Path("/opt/1C/v8.3/i386/rac"),
            Path("/usr/bin/rac"),
            Path("rac"),
        ]
    
    for path in default_paths:
        if path.exists():
            return path
    
    # Возвращаем первый путь по умолчанию
    return default_paths[0]


class RacConfig(BaseSettings):
    """Настройки для мониторинга через RAC"""

    # RAC configuration
    rac_path: Path = Field(default_factory=get_default_rac_path, validation_alias="RAC_PATH")
    rac_host: str = Field(default="127.0.0.1", validation_alias="RAC_HOST")
    rac_port: int = Field(default=1545, validation_alias="RAC_PORT")

    # Authentication (optional)
    user_name: Optional[str] = Field(default=None, validation_alias="USER_NAME")
    user_pass: Optional[str] = Field(default=None, validation_alias="USER_PASS")

    # Logging
    log_path: Path = Field(default_factory=get_default_log_path, validation_alias="LOG_PATH")
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
