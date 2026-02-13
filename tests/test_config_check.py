"""
Тесты для проверки конфигурации проекта zbx-1c-py.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Добавляем путь к src для импорта модулей проекта

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zbx_1c_py.utils.check_config import (
    check_executable_access,
    check_log_directory,
    check_ras_connection,
    validate_settings,
    print_results,
)


class TestCheckExecutableAccess:
    """Тесты для функции check_executable_access."""

    def test_empty_path(self):
        """Тест с пустым путем."""
        result, message = check_executable_access("")
        assert result is False
        assert "не задан" in message

    def test_nonexistent_file(self):
        """Тест с несуществующим файлом."""
        result, message = check_executable_access("/nonexistent/file.exe")
        assert result is False
        assert "не найден" in message

    def test_directory_instead_of_file(self, tmp_path):
        """Тест с директорией вместо файла."""
        dir_path = tmp_path / "some_dir"
        dir_path.mkdir()
        result, message = check_executable_access(str(dir_path))
        assert result is False
        assert "не на файл" in message


class TestCheckLogDirectory:
    """Тесты для функции check_log_directory."""

    def test_empty_path_uses_default(self):
        """Тест с пустым путем (используется ./logs по умолчанию)."""
        result, message = check_log_directory("")
        assert result is True
        assert "logs" in message
        # Удаляем созданную директорию
        import shutil

        try:
            shutil.rmtree("./logs", ignore_errors=True)
        except (OSError, PermissionError):
            pass

    def test_create_new_directory(self, tmp_path):
        """Тест создания новой директории."""
        new_dir = tmp_path / "new_logs"
        result, message = check_log_directory(str(new_dir))
        assert result is True
        assert str(new_dir) in message
        assert new_dir.exists()

    def test_existing_directory(self, tmp_path):
        """Тест с существующей директорией."""
        existing_dir = tmp_path / "existing_logs"
        existing_dir.mkdir()
        result, message = check_log_directory(str(existing_dir))
        assert result is True
        assert str(existing_dir) in message


class TestValidateSettings:
    """Тесты для функции validate_settings."""

    def test_validate_settings_structure(self):
        """Тест структуры возвращаемых данных."""
        results = validate_settings()
        assert isinstance(results, list)
        assert len(results) > 0  # Должно быть несколько проверок

        # Проверяем, что каждый элемент - кортеж из 3 элементов
        for item in results:
            assert isinstance(item, tuple)
            assert len(item) == 3
            setting_name, is_valid, message = item
            assert isinstance(setting_name, str)
            assert isinstance(is_valid, bool)
            assert isinstance(message, str)


class TestPrintResults:
    """Тесты для функции print_results."""

    def test_print_results_with_mixed_results(self, capsys):
        """Тест вывода результатов с разными статусами."""
        test_results = [
            ("TEST_SETTING_1", True, "Проверка пройдена"),
            ("TEST_SETTING_2", False, "Проверка не пройдена"),
        ]

        success = print_results(test_results)

        captured = capsys.readouterr()
        output = captured.out

        # Проверяем, что в выводе есть информация о результатах
        assert "РЕЗУЛЬТАТЫ ПРОВЕРКИ" in output
        assert "Проверок пройдено: 1/2" in output
        assert "Обнаружены проблемы" in output
        assert success is False  # Должен вернуть False, т.к. одна ошибка

    def test_print_results_all_success(self, capsys):
        """Тест вывода результатов, когда все проверки успешны."""
        test_results = [
            ("TEST_SETTING_1", True, "Проверка пройдена"),
            ("TEST_SETTING_2", True, "Проверка пройдена"),
        ]

        success = print_results(test_results)

        captured = capsys.readouterr()
        output = captured.out

        # Проверяем, что в выводе есть информация о результатах
        assert "Проверок пройдено: 2/2" in output
        assert "корректна" in output
        assert success is True  # Должен вернуть True, т.к. все ок


class TestIntegration:
    """Интеграционные тесты."""

    @patch("zbx_1c_py.utils.check_config.subprocess.run")
    def test_check_ras_connection_success(self, mock_subprocess_run):
        """Тест успешного подключения к RAS."""
        # Мокаем успешный результат
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "cluster list output"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        # Тестируем
        result, message = check_ras_connection()

        assert result is True
        assert "успешно" in message
        mock_subprocess_run.assert_called_once()

    @patch("zbx_1c_py.utils.check_config.subprocess.run")
    def test_check_ras_connection_failure(self, mock_subprocess_run):
        """Тест неуспешного подключения к RAS."""
        # Мокаем неуспешный результат
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Connection failed"
        mock_subprocess_run.return_value = mock_result

        # Тестируем
        result, message = check_ras_connection()

        assert result is False
        assert "Ошибка" in message or "Connection failed" in message
        mock_subprocess_run.assert_called_once()

    @patch("zbx_1c_py.utils.check_config.subprocess.run")
    def test_check_ras_connection_timeout(self, mock_subprocess_run):
        """Тест таймаута при подключении к RAS."""
        # Мокаем исключение таймаута
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired(cmd=["test"], timeout=10)

        # Тестируем
        result, message = check_ras_connection()

        assert result is False
        assert "Таймаут" in message
