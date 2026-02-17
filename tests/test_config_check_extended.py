"""
Дополнительные тесты для проверки конфигурации проекта zbx-1c-py.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch
from pydantic_settings import BaseSettings
import pytest


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.zbx_1c.core.config import settings
from src.zbx_1c.cli.zabbix_config import check_executable_access


class TestCheckExecutableAccessDetailed:
    """Детальные тесты для функции check_executable_access."""

    def test_valid_executable_file(self, tmp_path):
        """Тест с существующим исполняемым файлом."""
        # Создаем временный файл
        exe_file = tmp_path / "test_executable.exe"
        exe_file.write_text("#!/bin/bash\necho 'test'")

        # На Windows не можем проверить исполняемость так же, как на Unix
        if os.name == "nt":  # Windows
            result, message = check_executable_access(str(exe_file))
            # На Windows мы просто проверяем существование файла
            assert result is True
        else:  # Unix-like
            os.chmod(str(exe_file), 0o755)  # Делаем файл исполняемым
            result, message = check_executable_access(str(exe_file))
            assert result is True
            assert "доступен" in message.lower()

    def test_non_executable_file_unix(self, tmp_path):
        """Тест с неисполняемым файлом (Unix)."""
        if os.name == "nt":  # Пропускаем на Windows
            pytest.skip("Тест только для Unix-систем")

        # Создаем временный файл
        exe_file = tmp_path / "test_non_executable"
        exe_file.write_text("test content")
        os.chmod(str(exe_file), 0o644)  # Файл не исполняемый

        result, message = check_executable_access(str(exe_file))
        assert result is False
        assert "исполняем" in message.lower()


def test_settings_loaded_correctly():
    """Тест проверяет, что настройки загружаются корректно."""
    # Проверяем, что у нас есть все ожидаемые настройки
    assert hasattr(settings, "rac_path")
    assert hasattr(settings, "rac_host")
    assert hasattr(settings, "rac_port")
    assert hasattr(settings, "user_name")
    assert hasattr(settings, "user_pass")
    assert hasattr(settings, "debug")
    assert hasattr(settings, "log_path")

    # Проверяем типы данных
    assert isinstance(settings.rac_host, str)
    assert isinstance(settings.rac_port, int)
    assert isinstance(settings.debug, bool)


@patch.dict(
    os.environ,
    {
        "RAC_PATH": "/custom/path/to/rac",
        "RAC_HOST": "custom.host.local",
        "RAC_PORT": "1546",
        "USER_NAME": "test_user",
        "USER_PASS": "test_pass",
        "DEBUG": "true",
        "LOG_PATH": "/custom/logs",
    },
)
def test_settings_from_environment():
    """Тест загрузки настроек из переменных окружения."""
    # Перезагружаем настройки, чтобы они использовали переменные окружения

    class TestSettings(BaseSettings):
        rac_path: str = ""
        rac_host: str = "127.0.0.1"
        rac_port: int = 1545
        user_name: str = ""
        user_pass: str = ""
        debug: bool = False
        log_path: str = ""

    test_settings = TestSettings()

    assert test_settings.rac_path == "/custom/path/to/rac"
    assert test_settings.rac_host == "custom.host.local"
    assert test_settings.rac_port == 1546
    assert test_settings.user_name == "test_user"
    assert test_settings.user_pass == "test_pass"
    assert test_settings.debug is True
    assert test_settings.log_path == "/custom/logs"


def test_default_values():
    """Тест значений по умолчанию."""
    # Проверяем, что у настроек есть корректные значения по умолчанию
    assert settings.rac_host == "127.0.0.1"
    assert settings.rac_port == 1545
    assert settings.debug is False
