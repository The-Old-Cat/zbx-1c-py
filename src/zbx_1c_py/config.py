from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # Указываем поля и их значения по умолчанию
    rac_path: str = Field(default="rac")
    rac_host: str = Field(default="127.0.0.1")
    rac_port: int = Field(default=1545)
    debug: bool = Field(default=False)

    # Настройка для чтения из .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Создаем один экземпляр настроек для всего приложения
settings = Settings()
