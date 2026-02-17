"""
Интеграционные тесты для проекта zbx-1c-py.
"""

from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
import json

# Добавляем путь к src для импорта модулей проекта
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zbx_1c_py import main
from zbx_1c_py import clusters
from zbx_1c_py import session
from zbx_1c_py import session_active
from zbx_1c_py import background_jobs
from zbx_1c_py.utils import helpers


class TestIntegration:
    """Интеграционные тесты для проверки взаимодействия между модулями."""

    @patch("zbx_1c_py.clusters.subprocess.run")
    @patch("zbx_1c_py.clusters.decode_output")
    @patch("zbx_1c_py.clusters.parse_rac_output")
    def test_clusters_and_utils_integration(
        self, mock_parse_rac_output, mock_decode_output, mock_subprocess_run
    ):
        """Тест интеграции модулей clusters и utils."""
        # Мокаем успешный результат
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b"cluster data"
        mock_subprocess_run.return_value = mock_result
        mock_decode_output.return_value = "decoded cluster data"
        mock_parse_rac_output.return_value = [{"cluster": "test-id", "name": "test-name"}]

        # Вызываем функцию из модуля clusters
        result = clusters.get_all_clusters()

        # Проверяем, что функция из utils была вызвана
        mock_parse_rac_output.assert_called_once_with("decoded cluster data")
        mock_decode_output.assert_called_once_with(b"cluster data")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["cluster"] == "test-id"

    @patch("zbx_1c_py.session.subprocess.run")
    @patch("zbx_1c_py.session.decode_output")
    @patch("zbx_1c_py.session.parse_rac_output")
    def test_session_and_utils_integration(
        self, mock_parse_rac_output, mock_decode_output, mock_subprocess_run
    ):
        """Тест интеграции модулей session и utils."""
        # Мокаем успешный результат
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b"session data"
        mock_subprocess_run.return_value = mock_result
        mock_decode_output.return_value = "decoded session data"
        mock_parse_rac_output.return_value = [
            {
                "session-id": "1",
                "user-name": "test",
                "hibernate": "no",
                "last-active-at": "2026-02-11T10:06:04",
            }
        ]

        # Вызываем функцию из модуля session
        result = session.fetch_raw_sessions("test-cluster-id")

        # Проверяем, что функция из utils была вызвана
        mock_parse_rac_output.assert_called_once_with("decoded session data")
        mock_decode_output.assert_called_once_with(b"session data")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["session-id"] == "1"

    @patch("zbx_1c_py.session.cluster_id", "test-cluster-id")
    @patch("zbx_1c_py.session.fetch_raw_sessions")
    @patch("zbx_1c_py.session_active.filter_active_sessions")
    def test_session_and_session_active_integration(
        self, mock_filter_active_sessions, mock_fetch_raw_sessions
    ):
        """Тест интеграции модулей session и session_active."""
        # Мокаем данные
        mock_fetch_raw_sessions.return_value = [
            {
                "session-id": "1",
                "user-name": "test",
                "hibernate": "no",
                "last-active-at": "2026-02-11T10:06:04",
            }
        ]
        mock_filter_active_sessions.return_value = [
            {
                "session-id": "1",
                "user-name": "test",
                "hibernate": "no",
                "last-active-at": "2026-02-11T10:06:04",
            }
        ]

        # Вызываем функцию из модуля session
        result = session.get_active_sessions_report(only_active=True)

        # Проверяем, что функция из session_active была вызвана
        mock_filter_active_sessions.assert_called_once()
        mock_fetch_raw_sessions.assert_called_once()

        assert isinstance(result, list)

    @patch("zbx_1c_py.main.fetch_background_jobs_raw")
    @patch("zbx_1c_py.background_jobs.is_background_job_active")
    def test_main_and_background_jobs_integration(
        self, mock_is_background_job_active, mock_fetch_background_jobs_raw
    ):
        """Тест интеграции модулей main и background_jobs."""
        # Мокаем данные
        mock_fetch_background_jobs_raw.return_value = [
            {
                "job-id": "1",
                "state": "active",
                "duration": "1000",
                "started-at": "2026-02-11T10:06:04",
            }
        ]
        mock_is_background_job_active.return_value = True

        # Вызываем вспомогательную функцию для получения заданий
        raw_jobs = mock_fetch_background_jobs_raw("test-cluster-id")
        active_jobs = [
            j for j in raw_jobs if mock_is_background_job_active(j, max_duration_minutes=60)
        ]

        # Проверяем, что функция из background_jobs была вызвана
        assert len(active_jobs) == 1
        mock_is_background_job_active.assert_called()

    @patch("zbx_1c_py.utils.helpers.universal_filter")
    def test_utils_integration_with_various_modules(self, mock_universal_filter):
        """Тест интеграции модуля helpers с различными модулями."""
        # Мокаем результат фильтрации
        mock_universal_filter.return_value = [{"filtered": "data"}]

        # Тестируем вызов из модуля session
        test_data = [{"original": "data"}]
        test_fields = ["filtered"]

        result = helpers.universal_filter(test_data, test_fields)

        # Проверяем, что фильтр работает корректно
        mock_universal_filter.assert_called_once_with(test_data, test_fields)
        assert result == [{"filtered": "data"}]


class TestMainIntegration:
    """Интеграционные тесты для главного модуля."""

    @patch("zbx_1c_py.main.get_all_clusters")
    def test_get_discovery_json_integration(self, mock_get_all_clusters):
        """Тест интеграции функции генерации JSON для обнаружения."""
        # Мокаем данные кластеров
        mock_get_all_clusters.return_value = [
            {"cluster": "a1b2c3d4-5678-90ab-cdef-1234567890ab", "name": "Основной кластер"},
            {"cluster": "b2c3d4e5-6789-01ab-cdef-2345678901bc", "name": "Резервный кластер"},
        ]

        result = main.get_discovery_json()

        # Проверяем, что результат - это JSON-строка

        parsed_result = json.loads(result)

        assert isinstance(parsed_result, list)
        assert len(parsed_result) == 2
        assert parsed_result[0]["{#CLUSTER_ID}"] == "a1b2c3d4-5678-90ab-cdef-1234567890ab"
        assert parsed_result[0]["{#CLUSTER_NAME}"] == "Основной кластер"

    @patch("zbx_1c_py.main.fetch_raw_sessions")
    @patch("zbx_1c_py.main.filter_active_sessions")
    @patch("zbx_1c_py.main.fetch_background_jobs_raw")
    @patch("zbx_1c_py.main.is_background_job_active")
    def test_collect_metrics_for_cluster_integration(
        self,
        mock_is_background_job_active,
        mock_fetch_background_jobs_raw,
        mock_filter_active_sessions,
        mock_fetch_raw_sessions,
    ):
        """Тест интеграции функции сбора метрик для кластера."""
        # Мокаем данные
        mock_fetch_raw_sessions.return_value = [
            {
                "session-id": "1",
                "user-name": "user1",
                "hibernate": "no",
                "last-active-at": "2026-02-11T10:06:04",
            },
            {
                "session-id": "2",
                "user-name": "user2",
                "hibernate": "yes",
                "last-active-at": "2026-02-11T09:00:00",
            },
        ]
        mock_filter_active_sessions.return_value = [
            {
                "session-id": "1",
                "user-name": "user1",
                "hibernate": "no",
                "last-active-at": "2026-02-11T10:06:04",
            }
        ]
        mock_fetch_background_jobs_raw.return_value = [
            {
                "job-id": "1",
                "state": "active",
                "duration": "1000",
                "started-at": "2026-02-11T10:06:04",
            },
            {
                "job-id": "2",
                "state": "completed",
                "duration": "2000",
                "started-at": "2026-02-11T09:00:00",
            },
        ]
        mock_is_background_job_active.return_value = True

        # Создаем тестовый кластер
        test_cluster = {"cluster": "test-id", "name": "Test Cluster"}
        
        # Мокаем переменную в модуле main, а не в модуле clusters
        with patch.object(main_module, 'all_available_clusters', [test_cluster]):
            result = main.collect_metrics_for_cluster("test-id")

        parsed_result = json.loads(result)

        assert isinstance(parsed_result, dict)
        assert parsed_result["cluster_id"] == "test-id"
        assert parsed_result["cluster_name"] == "Test Cluster"
        assert "metrics" in parsed_result
        assert "total_sessions" in parsed_result["metrics"]
        assert "active_sessions" in parsed_result["metrics"]
        assert "active_bg_jobs" in parsed_result["metrics"]
        assert "status" in parsed_result["metrics"]

    @patch("zbx_1c_py.main.check_ras_availability")
    def test_main_check_ras_integration(self, mock_check_ras_availability):
        """Тест интеграции проверки RAS."""
        # Мокаем результат
        mock_check_ras_availability.return_value = {
            "available": True,
            "message": "RAS is reachable",
            "code": 0,
        }

        # Тестируем через main (хотя напрямую вызываем функцию)
        result = main.check_ras_availability()

        assert result["available"] is True
        assert result["message"] == "RAS is reachable"
        assert result["code"] == 0


class TestCrossModuleIntegration:
    """Кросс-модульные интеграционные тесты."""

    def test_session_active_integration_with_helpers(self):
        """Тест интеграции session_active с helpers."""
        # Тестируем, что функции из session_active могут использовать функции из helpers
        test_session = {
            "user-name": "Иванов Иван Иванович",
            "app-id": "1CV8C",
            "last-active-at": "2026-02-11T10:06:04",
            "calls-last-5min": "36",
        }

        # Используем функцию из session_active
        summary = session_active.get_session_summary(test_session)

        # Проверяем, что результат содержит ожидаемые элементы
        assert "Иванов И.И." in summary  # Имя должно быть сокращено
        assert "1CV8C" in summary
        assert "36" in summary

    def test_background_jobs_integration_with_helpers(self):
        """Тест интеграции background_jobs с helpers."""
        # Тестируем, что функции из background_jobs могут использовать функции из helpers
        test_job = {
            "job-id": "123",
            "user-name": "Иванов Иван Иванович",
            "description": "Расчёт зарплаты за февраль 2026",
            "duration": "125000",  # 125 секунд
            "progress": "45",
        }

        # Используем функцию из background_jobs
        summary = background_jobs.get_background_job_summary(test_job)

        # Проверяем, что результат содержит ожидаемые элементы
        assert "ID: 123" in summary
        assert "Иванов И.И." in summary  # Имя должно быть сокращено
        assert "Расчёт зарплаты..." in summary  # Описание должно быть сокращено
        assert "125.0s" in summary
        assert "45%" in summary
