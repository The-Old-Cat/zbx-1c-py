"""
Тесты для проверки конфигурации проекта zbx-1c-py.
"""

import os
import sys
from pathlib import Path
from zbx_1c_py import config

# Добавляем путь к src для импорта модулей проекта
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.zbx_1c.core.config import Settings, settings


class TestConfigModule:
    """Тесты для модуля конфигурации."""

    def test_settings_instance_creation(self):
        """Тест создания экземпляра настроек."""
        # Проверяем, что экземпляр настроек создается
        assert settings is not None
        assert isinstance(settings, Settings)

    def test_settings_attributes_existence(self):
        """Тест существования атрибутов настроек."""
        # Проверяем, что все ожидаемые атрибуты существуют
        assert hasattr(settings, "rac_path")
        assert hasattr(settings, "rac_host")
        assert hasattr(settings, "rac_port")
        assert hasattr(settings, "user_name")
        assert hasattr(settings, "user_pass")
        assert hasattr(settings, "debug")
        assert hasattr(settings, "log_path")

    def test_settings_default_values(self):
        """Тест значений по умолчанию."""
        # Проверяем значения по умолчанию
        assert settings.rac_host == "127.0.0.1"
        assert settings.rac_port == 1545
        assert settings.debug is False
        assert isinstance(settings.user_name, str)
        assert isinstance(settings.user_pass, str)
        assert isinstance(settings.log_path, str)

    def test_settings_types(self):
        """Тест типов данных настроек."""
        # Проверяем типы данных
        assert isinstance(settings.rac_path, str)
        assert isinstance(settings.rac_host, str)
        assert isinstance(settings.rac_port, int)
        assert isinstance(settings.user_name, str)
        assert isinstance(settings.user_pass, str)
        assert isinstance(settings.debug, bool)
        assert isinstance(settings.log_path, str)

    def test_settings_validation(self):
        """Тест валидации настроек."""
        # Создаем настройки с корректными значениями
        test_settings = Settings(
            rac_path="/path/to/rac",
            rac_host="localhost",
            rac_port=1541,
            user_name="test_user",
            user_pass="test_pass",
            debug=True,
            log_path="/tmp/logs",
        )

        assert test_settings.rac_path == "/path/to/rac"
        assert test_settings.rac_host == "localhost"
        assert test_settings.rac_port == 1541
        assert test_settings.user_name == "test_user"
        assert test_settings.user_pass == "test_pass"
        assert test_settings.debug is True
        assert test_settings.log_path == "/tmp/logs"

    def test_settings_port_validation(self):
        """Тест валидации порта."""
        # Проверяем, что корректные порты принимаются
        port_settings = Settings(rac_port=1541)
        assert port_settings.rac_port == 1541

        # В текущей реализации валидация порта не настроена,
        # но мы можем протестировать, что отрицательные значения не вызывают ошибки
        # и просто сохраняются как есть
        negative_settings = Settings(rac_port=-1)
        assert negative_settings.rac_port == -1

    def test_settings_debug_flag(self):
        """Тест флага отладки."""
        # Создаем настройки с разными значениями debug
        settings_true = Settings(debug=True)
        settings_false = Settings(debug=False)

        assert settings_true.debug is True
        assert settings_false.debug is False


class TestEnvironmentVariableConfiguration:
    """Тесты для загрузки конфигурации из переменных окружения."""

    def test_load_from_environment_variables(self):
        """Тест загрузки настроек из переменных окружения."""
        # Сохраняем оригинальные значения
        original_env = {
            "RAC_PATH": os.environ.get("RAC_PATH"),
            "RAC_HOST": os.environ.get("RAC_HOST"),
            "RAC_PORT": os.environ.get("RAC_PORT"),
            "USER_NAME": os.environ.get("USER_NAME"),
            "USER_PASS": os.environ.get("USER_PASS"),
            "DEBUG": os.environ.get("DEBUG"),
            "LOG_PATH": os.environ.get("LOG_PATH"),
        }

        try:
            # Устанавливаем тестовые переменные окружения
            os.environ["RAC_PATH"] = "/custom/path/to/rac"
            os.environ["RAC_HOST"] = "custom.host.local"
            os.environ["RAC_PORT"] = "1546"
            os.environ["USER_NAME"] = "test_user"
            os.environ["USER_PASS"] = "test_pass"
            os.environ["DEBUG"] = "true"
            os.environ["LOG_PATH"] = "/custom/logs"

            # Создаем новые настройки
            env_settings = Settings()

            # Проверяем, что настройки загрузились из переменных окружения
            assert env_settings.rac_path == "/custom/path/to/rac"
            assert env_settings.rac_host == "custom.host.local"
            assert env_settings.rac_port == 1546
            assert env_settings.user_name == "test_user"
            assert env_settings.user_pass == "test_pass"
            assert env_settings.debug is True
            assert env_settings.log_path == "/custom/logs"

        finally:
            # Восстанавливаем оригинальные значения
            for key, value in original_env.items():
                if value is not None:
                    os.environ[key] = value
                elif key in os.environ:
                    del os.environ[key]

    def test_environment_variable_boolean_conversion(self):
        """Тест преобразования булевых значений из переменных окружения."""
        original_debug = os.environ.get("DEBUG")

        try:
            # Тестируем разные варианты значений для булева
            test_cases = [
                ("true", True),
                ("True", True),
                ("1", True),
                ("false", False),
                ("False", False),
                ("0", False),
            ]

            for env_value, expected_bool in test_cases:
                os.environ["DEBUG"] = env_value
                env_bool_settings = Settings()

                assert env_bool_settings.debug is expected_bool

        finally:
            # Восстанавливаем оригинальное значение
            if original_debug is not None:
                os.environ["DEBUG"] = original_debug
            elif "DEBUG" in os.environ:
                del os.environ["DEBUG"]

    def test_environment_variable_integer_conversion(self):
        """Тест преобразования целочисленных значений из переменных окружения."""
        original_port = os.environ.get("RAC_PORT")

        try:
            os.environ["RAC_PORT"] = "1547"
            env_int_settings = Settings()

            assert env_int_settings.rac_port == 1547
            assert isinstance(env_int_settings.rac_port, int)

        finally:
            # Восстанавливаем оригинальное значение
            if original_port is not None:
                os.environ["RAC_PORT"] = original_port
            elif "RAC_PORT" in os.environ:
                del os.environ["RAC_PORT"]


class TestConfigValidation:
    """Тесты валидации конфигурации."""

    def test_invalid_port_values(self):
        """Тест недопустимых значений порта."""
        # В текущей реализации валидация порта не настроена,
        # поэтому все значения принимаются
        invalid_ports = [-1, 0, 65536, 70000]

        for invalid_port in invalid_ports:
            invalid_port_settings = Settings(rac_port=invalid_port)
            assert invalid_port_settings.rac_port == invalid_port

    def test_valid_port_ranges(self):
        """Тест допустимых диапазонов порта."""
        valid_ports = [1, 80, 443, 1541, 1545, 8080, 65535]

        for valid_port in valid_ports:
            settings_obj = Settings(rac_port=valid_port)
            assert settings_obj.rac_port == valid_port

    def test_empty_string_values(self):
        """Тест пустых строковых значений."""
        empty_test_settings = Settings(
            rac_path="", rac_host="", user_name="", user_pass="", log_path=""
        )

        assert empty_test_settings.rac_path == ""
        assert empty_test_settings.rac_host == ""
        assert empty_test_settings.user_name == ""
        assert empty_test_settings.user_pass == ""
        assert empty_test_settings.log_path == ""

    def test_long_string_values(self):
        """Тест длинных строковых значений."""
        long_path = "a" * 1000  # Очень длинный путь
        long_test_settings = Settings(rac_path=long_path)

        assert long_test_settings.rac_path == long_path


class TestConfigIntegration:
    """Интеграционные тесты конфигурации."""

    def test_config_used_by_other_modules(self):
        """Тест использования конфигурации другими модулями."""
        # Проверяем, что другие модули могут использовать настройки

        # Проверяем, что модули могут получить доступ к настройкам
        assert hasattr(config, "settings")
        assert hasattr(config, "Settings")

        # Проверяем, что настройки те же самые
        assert config.settings is settings

    def test_config_consistency_across_modules(self):
        """Тест согласованности конфигурации между модулями."""
        # Проверяем, что все модули видят одинаковые настройки

        # Проверяем, что настройки одинаковые
        assert config.settings is settings
        assert config.settings.rac_host == settings.rac_host
        assert config.settings.rac_port == settings.rac_port
        assert config.settings.debug == settings.debug
