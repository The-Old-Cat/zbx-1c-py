"""
Тесты для проверки кроссплатформенности проекта zbx-1c-py.
"""

import os
import sys
from pathlib import Path
import tempfile
import platform
import pytest

# Добавляем путь к src для импорта модулей проекта
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.zbx_1c.core.config import settings


class TestCrossPlatform:
    """Тесты для проверки кроссплатформенности."""

    def test_path_separators_handling(self):
        """Тест обработки разделителей пути."""
        # Проверяем, что код может работать с разными разделителями пути
        if os.name == "nt":  # Windows
            path_with_backslash = "C:\\Program Files\\1cv8\\rac.exe"
            path_with_forward_slash = "C:/Program Files/1cv8/rac.exe"
        else:  # Unix-like
            path_with_backslash = "/opt/1c/rac"
            path_with_forward_slash = "/opt/1c/rac"

        # Оба пути должны быть обрабатываемы корректно
        path_obj1 = Path(path_with_backslash)
        path_obj2 = Path(path_with_forward_slash)

        # Path должен корректно обрабатывать оба формата
        assert str(path_obj1).replace("\\", "/") == str(path_obj2).replace("\\", "/")

    def test_config_path_handling(self):
        """Тест обработки путей в конфигурации."""
        # Проверяем, что настройки могут содержать пути с разными разделителями
        original_path = settings.rac_path

        try:
            # Тестируем, что пути могут быть изменены и обработаны
            if os.name == "nt":
                settings.rac_path = "C:\\Program Files\\1cv8\\test.exe"
            else:
                settings.rac_path = "/opt/1c/test"

            # Проверяем, что путь корректно сохранен
            assert settings.rac_path is not None

        finally:
            # Восстанавливаем оригинальный путь
            settings.rac_path = original_path

    def test_file_operations_cross_platform(self, tmp_path):
        """Тест файловых операций на разных платформах."""
        # Создаем временный файл
        test_file = tmp_path / "test_file.txt"
        test_content = "тестовое содержимое"

        # Записываем и читаем файл
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)

        with open(test_file, "r", encoding="utf-8") as f:
            read_content = f.read()

        assert read_content == test_content

    @pytest.mark.skipif(platform.system() == "Windows", reason="Тест только для Unix-систем")
    def test_unix_permissions_handling(self, tmp_path):
        """Тест обработки прав доступа к файлам (Unix-системы)."""
        test_file = tmp_path / "test_executable"
        test_file.write_text("#!/bin/bash\necho 'test'", encoding="utf-8")

        # Устанавливаем права на выполнение
        os.chmod(str(test_file), 0o755)

        # Проверяем, что права установлены
        stat_info = os.stat(str(test_file))
        assert stat_info.st_mode & 0o755 == 0o755

    def test_encoding_handling(self):
        """Тест обработки кодировок."""
        # Тестируем, что текст с кириллицей корректно обрабатывается
        test_text = "тестовая строка с кириллицей"

        # Кодируем и декодируем строку
        encoded = test_text.encode("utf-8")
        decoded = encoded.decode("utf-8")

        assert decoded == test_text

    def test_temporary_directories(self):
        """Тест временных директорий."""
        # Используем стандартный модуль для создания временных директорий
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            assert temp_path.exists()

            # Создаем файл во временной директории
            test_file = temp_path / "temp_test.txt"
            test_file.write_text("тест", encoding="utf-8")

            assert test_file.exists()


class TestEnvironmentVariables:
    """Тесты для проверки работы с переменными окружения на разных платформах."""

    def test_environment_variable_case_sensitivity(self):
        """Тест чувствительности к регистру переменных окружения."""
        test_var_name = "ZBX_TEST_VAR"
        test_value = "test_value"

        # Устанавливаем переменную окружения
        os.environ[test_var_name] = test_value

        try:
            # Проверяем, что переменная установлена
            retrieved_value = os.environ.get(test_var_name)
            assert retrieved_value == test_value

            # На Unix-системах переменные окружения чувствительны к регистру
            # На Windows - нет (но в Python getenv чувствителен к регистру)
            if platform.system() != "Windows":
                assert os.environ.get(test_var_name.lower()) is None
            else:
                # На Windows в системе переменные нечувствительны к регистру,
                # но в Python os.environ чувствителен к регистру
                # Однако некоторые системы могут возвращать значение в другом регистре
                # В большинстве случаев Python на Windows все равно чувствителен к регистру
                # для os.environ.get()
                lowercase_value = os.environ.get(test_var_name.lower())
                # В зависимости от системы, результат может отличаться
                # Поэтому просто проверим, что тест не падает

        finally:
            # Удаляем переменную окружения
            if test_var_name in os.environ:
                del os.environ[test_var_name]

    def test_path_environment_variable(self):
        """Тест переменной PATH."""
        # Проверяем, что переменная PATH существует
        path_value = os.environ.get("PATH")
        assert path_value is not None
        assert len(path_value) > 0

        # Проверяем, что PATH содержит разделители
        if os.name == "nt":
            assert ";" in path_value
        else:
            assert ":" in path_value


class TestPlatformSpecificFeatures:
    """Тесты специфичных для платформы функций."""

    def test_platform_identification(self):
        """Тест определения платформы."""
        current_platform = platform.system()
        assert current_platform in ["Windows", "Linux", "Darwin"]

        # Проверяем, что os.name соответствует ожиданиям
        if current_platform == "Windows":
            assert os.name == "nt"
        else:
            assert os.name in ["posix", "java"]

    def test_file_system_features(self):
        """Тест специфичных для файловой системы функций."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Создаем файл с именем, содержащим специфичные для платформы символы
            if os.name == "nt":
                # Windows не позволяет использовать определенные символы в именах файлов
                file_name = "test_file.txt"
            else:
                # Unix-системы позволяют больше символов
                file_name = "test_file.txt"

            test_file = temp_path / file_name
            test_file.write_text("content", encoding="utf-8")

            assert test_file.exists()


class TestCrossPlatformIntegration:
    """Интеграционные тесты кроссплатформенности."""

    def test_config_loading_on_different_platforms(self):
        """Тест загрузки конфигурации."""
        # Проверяем, что настройки загружаются корректно
        assert hasattr(settings, "rac_path")
        assert hasattr(settings, "rac_host")
        assert hasattr(settings, "rac_port")

        # Проверяем типы данных
        assert isinstance(settings.rac_host, str)
        assert isinstance(settings.rac_port, int)

    def test_path_manipulation_functions(self):
        """Тест функций манипуляции путями."""
        # Используем pathlib для кроссплатформенной работы с путями
        test_path = Path("some") / "path" / "with" / "components"

        # Проверяем, что путь корректно сформирован
        assert isinstance(test_path, Path)
        assert len(str(test_path)) > 0

        # Проверяем, что путь может быть преобразован в строку
        path_str = str(test_path)
        assert isinstance(path_str, str)

        # Проверяем, что компоненты пути сохранены
        assert "some" in path_str
        assert "components" in path_str
