"""
Тесты для модуля session проекта zbx-1c-py.
"""

from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
from subprocess import TimeoutExpired
from src.zbx_1c.core.config import settings
from src.zbx_1c.monitoring.cluster.manager import cluster_id

# Добавляем путь к src для импорта модулей проекта
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.zbx_1c.monitoring.session.collector import get_session_command, fetch_raw_sessions, get_active_sessions_report


class TestSessionModule:
    """Тесты для функций модуля session."""

    def test_get_session_command_basic(self):
        """Тест формирования базовой команды для получения сессий."""
        cluster_uuid = "test-cluster-id"
        command = get_session_command(cluster_uuid)

        # Проверяем, что команда содержит основные элементы
        assert isinstance(command, list)
        assert (
            len(command) >= 5
        )  # Должно быть как минимум: путь к rac, адрес, session, list, --cluster, id
        assert settings.rac_path in command
        assert "session" in command
        assert "list" in command
        assert "--cluster" in command
        assert cluster_uuid in command

    def test_get_session_command_with_auth(self):
        """Тест формирования команды с аутентификацией."""
        # Создаем временные настройки для теста
        cluster_uuid = "test-cluster-id"
        command = get_session_command(cluster_uuid)

        # Команда может содержать аутентификацию, если она настроена в конфиге
        # Проверяем структуру команды
        assert isinstance(command, list)
        assert (
            len(command) >= 6
        )  # Должно быть как минимум: путь к rac, адрес, session, list, --cluster, id

    @patch("zbx_1c_py.session.subprocess.run")
    @patch("zbx_1c_py.session.decode_output")
    @patch("zbx_1c_py.session.parse_rac_output")
    def test_fetch_raw_sessions_success(
        self, mock_parse_rac_output, mock_decode_output, mock_subprocess_run
    ):
        """Тест успешного получения сессий."""
        # Мокаем успешный результат
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b"session data"
        mock_subprocess_run.return_value = mock_result
        mock_decode_output.return_value = "decoded session data"
        mock_parse_rac_output.return_value = [{"session-id": "1", "user-name": "test"}]

        cluster_uuid = "test-cluster-id"
        result = fetch_raw_sessions(cluster_uuid)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["session-id"] == "1"
        mock_subprocess_run.assert_called_once()
        mock_parse_rac_output.assert_called_once_with("decoded session data")

    @patch("zbx_1c_py.session.subprocess.run")
    def test_fetch_raw_sessions_no_cluster_id(self, mock_subprocess_run):
        """Тест получения сессий без ID кластера."""
        result = fetch_raw_sessions("")

        assert not result
        # subprocess.run не должен быть вызван
        mock_subprocess_run.assert_not_called()

    @patch("zbx_1c_py.session.subprocess.run")
    def test_fetch_raw_sessions_timeout(self, mock_subprocess_run):
        """Тест получения сессий при таймауте."""
        # Мокаем исключение TimeoutExpired

        mock_subprocess_run.side_effect = TimeoutExpired(cmd=["test"], timeout=20)

        cluster_uuid = "test-cluster-id"
        result = fetch_raw_sessions(cluster_uuid)

        assert not result

    @patch("zbx_1c_py.session.subprocess.run")
    def test_fetch_raw_sessions_file_not_found(self, mock_subprocess_run):
        """Тест получения сессий при отсутствии файла."""
        # Мокаем исключение FileNotFoundError
        mock_subprocess_run.side_effect = FileNotFoundError("File not found")

        cluster_uuid = "test-cluster-id"
        result = fetch_raw_sessions(cluster_uuid)

        assert not result

    @patch("zbx_1c_py.session.fetch_raw_sessions")
    @patch("zbx_1c_py.session.filter_active_sessions")
    @patch("zbx_1c_py.session.universal_filter")
    def test_get_active_sessions_report(
        self, mock_universal_filter, mock_filter_active_sessions, mock_fetch_raw_sessions
    ):
        """Тест получения отчета об активных сессиях."""
        # Мокаем возвращаемые значения
        mock_fetch_raw_sessions.return_value = [
            {"session-id": "1", "user-name": "user1", "app-id": "app1", "last-active-at": "time1"}
        ]
        mock_filter_active_sessions.return_value = [
            {"session-id": "1", "user-name": "user1", "app-id": "app1", "last-active-at": "time1"}
        ]
        mock_universal_filter.return_value = [
            {"session-id": "1", "user-name": "user1", "app-id": "app1", "last-active-at": "time1"}
        ]

        result = get_active_sessions_report(only_active=True)

        assert isinstance(result, list)
        mock_fetch_raw_sessions.assert_called_once_with(cluster_id)
        mock_filter_active_sessions.assert_called_once()
        mock_universal_filter.assert_called_once()

    @patch("zbx_1c_py.session.fetch_raw_sessions")
    def test_get_active_sessions_report_empty(self, mock_fetch_raw_sessions):
        """Тест получения отчета об активных сессиях с пустыми данными."""
        # Мокаем пустой результат
        mock_fetch_raw_sessions.return_value = []

        result = get_active_sessions_report(only_active=True)

        assert not result
        mock_fetch_raw_sessions.assert_called_once()


class TestSessionEdgeCases:
    """Тесты для граничных условий в модуле session."""

    def test_get_session_command_special_characters(self):
        """Тест команды с особыми символами в ID кластера."""
        cluster_uuid = "test-cluster-with-special-chars_123"
        command = get_session_command(cluster_uuid)

        assert cluster_uuid in command
        assert isinstance(command, list)

    @patch("zbx_1c_py.session.subprocess.run")
    @patch("zbx_1c_py.session.decode_output")
    @patch("zbx_1c_py.session.parse_rac_output")
    def test_fetch_raw_sessions_empty_response(
        self, mock_parse_rac_output, mock_decode_output, mock_subprocess_run
    ):
        """Тест получения сессий с пустым ответом."""
        # Мокаем пустой результат
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b""
        mock_subprocess_run.return_value = mock_result
        mock_decode_output.return_value = ""
        mock_parse_rac_output.return_value = []

        cluster_uuid = "test-cluster-id"
        result = fetch_raw_sessions(cluster_uuid)

        assert not result
        assert mock_parse_rac_output.call_args[0][0] == ""
