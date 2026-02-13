"""
Модуль конфигурации приложения zbx_1c_py.

Содержит класс Settings, который управляет настройками приложения,
включая параметры подключения к RAS (Remote Administration Service) 1С,
аутентификацию и пути к файлам.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


# Определяем корень проекта
# src/zbx_1c_py/config.py -> корень проекта
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    Класс настроек приложения для мониторинга 1С:Предприятия.

    Attributes:
        rac_path (str): Путь к исполняемому файлу rac.exe (по умолчанию "")
        rac_host (str): Хост RAS-сервиса 1С (по умолчанию "127.0.0.1")
        rac_port (int): Порт RAS-сервиса 1С (по умолчанию 1545)
        user_name (str): Имя пользователя для аутентификации в кластере (по умолчанию "")
        user_pass (str): Пароль пользователя для аутентификации в кластере (по умолчанию "")
        debug (bool): Флаг включения режима отладки (по умолчанию False)
        log_path (str): Путь к директории для логов (по умолчанию "")

    Configuration:
        - Загрузка настроек из файла .env в корне проекта
        - Поддержка переменных окружения
        - Валидация типов данных
    """

    # Указываем поля и их значения по умолчанию
    rac_path: str = Field(
        default="",
        description="Путь к исполняемому файлу rac.exe, например: C:/Program Files/1cv8/rac.exe",
    )
    rac_host: str = Field(default="127.0.0.1", description="Хост RAS-сервиса 1С:Предприятия")
    rac_port: int = Field(
        default=1545, description="Порт RAS-сервиса 1С:Предприятия (обычно 1541 или 1545)"
    )
    user_name: str = Field(
        default="", description="Имя пользователя для аутентификации в кластере 1С"
    )
    user_pass: str = Field(
        default="", description="Пароль пользователя для аутентификации в кластере 1С"
    )
    debug: bool = Field(default=False, description="Флаг включения режима отладки")
    log_path: str = Field(default="", description="Путь к директории для хранения лог-файлов")

    """
    Конфигурация загрузки настроек из файла .env
    """
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"), env_file_encoding="utf-8"
    )


# Создаем один экземпляр настроек для всего приложения
# Этот экземпляр используется во всех модулях приложения для доступа к настройкам
settings = Settings()
