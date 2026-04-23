"""Конфигурация для автопубликации 1С."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PublisherConfig(BaseSettings):
    """Конфигурация автопубликации 1С."""

    model_config = SettingsConfigDict(
        env_file=os.environ.get("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # =========================================================
    # Сервер 1С:Предприятия
    # =========================================================
    SERVER_1C_HOST: str = Field(default="localhost", description="Адрес сервера 1С")
    SERVER_1C_PORT: int = Field(default=1545, description="Порт сервера 1С")
    SERVER_1C_CLUSTER: str = Field(default="", description="Имя кластера 1С")
    SERVER_1C_USER: str = Field(default="", description="Пользователь администратора кластера")
    SERVER_1C_PASSWORD: str = Field(default="", description="Пароль администратора кластера")

    # =========================================================
    # Публикация
    # =========================================================
    PUBLISH_MODE: str = Field(default="FULL", description="Режим публикации (FULL/THIN)")
    WEBINST_PATH: Optional[str] = Field(default=None, description="Путь к webinst.exe")
    PUBLISH_ROOT: str = Field(default="/htdocs", description="Корневая директория для публикации")
    TECH_SUFFIX: str = Field(default="_mg", description="Суффикс для технических имён")
    PUBLISH_TYPE: str = Field(default="prod", description="Тип публикации: prod или tech")
    APACHE_CONF_PATH: Optional[str] = Field(default=None, description="Путь к httpd.conf Apache")

    # =========================================================
    # Apache deployment
    # =========================================================
    APACHE_VERSION: str = Field(default="2.4.66", description="Версия Apache")
    APACHE_VS: str = Field(default="VS18", description="Версия Visual Studio для Apache")
    APACHE_DOWNLOAD_URL: Optional[str] = Field(default=None)
    APACHE_FALLBACK_URL: Optional[str] = Field(default=None)
    APACHE_INSTALL_PATH_WIN: str = Field(default=r"C:\Apache24")
    APACHE_INSTALL_PATH_LINUX: str = Field(default="/etc/apache2")
    APACHE_SERVICE_NAME: str = Field(default="Apache2.4")
    DOWNLOAD_TIMEOUT: int = Field(default=300)

    # =========================================================
    # Версия 1С (для поиска бинарников)
    # =========================================================
    ONEC_VERSION: str = Field(default="8.3.27.2074", description="Версия платформы 1С")

    # =========================================================
    # Фильтрация баз
    # =========================================================
    BASE_PREFIX: str = Field(default="", description="Префиксы баз для публикации")
    BASE_EXCLUDE: str = Field(default="", description="Исключения баз")

    # =========================================================
    # Логирование
    # =========================================================
    LOG_LEVEL: str = Field(default="INFO", description="Уровень логирования")
    LOG_PATH: str = Field(default="./logs", description="Путь к логам")

    @property
    def webinst_path(self) -> Optional[Path]:
        return Path(self.WEBINST_PATH) if self.WEBINST_PATH else None

    @property
    def publish_root_path(self) -> Path:
        return Path(self.PUBLISH_ROOT)

    def get_publish_dir(self, base_name: str) -> Path:
        if self.PUBLISH_TYPE.upper() == "TECH":
            tech_name = f"{base_name}{self.TECH_SUFFIX}"
            return Path(self.PUBLISH_ROOT) / "tech" / tech_name
        return Path(self.PUBLISH_ROOT) / "prod" / base_name

    def get_vrd_filename(self) -> str:
        return "full.vrd" if self.PUBLISH_MODE.upper() == "FULL" else "thin.vrd"

    @property
    def apache_conf_path(self) -> Optional[Path]:
        return Path(self.APACHE_CONF_PATH) if self.APACHE_CONF_PATH else None

    def get_base_prefixes(self) -> List[str]:
        return (
            [p.strip() for p in self.BASE_PREFIX.split(",") if p.strip()]
            if self.BASE_PREFIX
            else []
        )

    def get_base_excludes(self) -> List[str]:
        return (
            [e.strip() for e in self.BASE_EXCLUDE.split(",") if e.strip()]
            if self.BASE_EXCLUDE
            else []
        )

    def should_publish_base(self, base_name: str) -> bool:
        if base_name in self.get_base_excludes():
            return False
        prefixes = self.get_base_prefixes()
        if prefixes:
            return any(base_name.startswith(prefix) for prefix in prefixes)
        return True
