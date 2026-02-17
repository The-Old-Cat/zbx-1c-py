"""
Тесты для модуля session_active проекта zbx-1c-py.
"""

from datetime import datetime, timedelta
import sys
from pathlib import Path

# Добавляем путь к src для импорта модулей проекта
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.zbx_1c.monitoring.session.filters import is_session_active, filter_active_sessions, get_session_summary


class TestSessionActiveModule:
    """Тесты для функций модуля session_active."""

    def test_is_session_active_fully_active(self):
        """Тест активной сессии с полной активностью."""
        # Создаем сессию с полной активностью
        now = datetime.now()
        session = {
            "hibernate": "no",
            "last-active-at": now.isoformat(),
            "calls-last-5min": "10",
            "bytes-last-5min": "1000",
        }

        result = is_session_active(session, threshold_minutes=5)

        assert result is True

    def test_is_session_active_hibernated(self):
        """Тест сессии в спящем режиме."""
        session = {
            "hibernate": "yes",  # Спящий режим
            "last-active-at": datetime.now().isoformat(),
            "calls-last-5min": "10",
            "bytes-last-5min": "1000",
        }

        result = is_session_active(session, threshold_minutes=5)

        assert result is False

    def test_is_session_active_old_activity(self):
        """Тест сессии с устаревшей активностью."""
        old_time = datetime.now() - timedelta(minutes=10)
        session = {
            "hibernate": "no",
            "last-active-at": old_time.isoformat(),
            "calls-last-5min": "0",  # Нет активности
            "bytes-last-5min": "0",  # Нет трафика
        }

        result = is_session_active(session, threshold_minutes=5)

        assert result is False

    def test_is_session_active_no_traffic(self):
        """Тест сессии без трафика и вызовов."""
        now = datetime.now()
        session = {
            "hibernate": "no",
            "last-active-at": now.isoformat(),
            "calls-last-5min": "0",  # Нет вызовов
            "bytes-last-5min": "0",  # Нет трафика
        }

        result = is_session_active(session, threshold_minutes=5)

        assert result is False

    def test_is_session_active_with_calls(self):
        """Тест сессии с вызовами, но без трафика."""
        now = datetime.now()
        session = {
            "hibernate": "no",
            "last-active-at": now.isoformat(),
            "calls-last-5min": "5",  # Есть вызовы
            "bytes-last-5min": "0",  # Нет трафика
        }

        result = is_session_active(session, threshold_minutes=5)

        assert result is True

    def test_is_session_active_with_bytes(self):
        """Тест сессии с трафиком, но без вызовов."""
        now = datetime.now()
        session = {
            "hibernate": "no",
            "last-active-at": now.isoformat(),
            "calls-last-5min": "0",  # Нет вызовов
            "bytes-last-5min": "100",  # Есть трафик
        }

        result = is_session_active(session, threshold_minutes=5)

        assert result is True

    def test_is_session_active_no_fields(self):
        """Тест сессии без полей активности."""
        now = datetime.now()
        session = {
            "hibernate": "no",
            "last-active-at": now.isoformat(),
            # Нет полей calls-last-5min и bytes-last-5min
        }

        result = is_session_active(session, threshold_minutes=5)

        # Если поля отсутствуют, функция должна полагаться только на первые два критерия
        # hibernate = "no" и last-active-at = now -> активна
        assert result is True

    def test_is_session_active_invalid_date(self):
        """Тест сессии с некорректной датой."""
        session = {
            "hibernate": "no",
            "last-active-at": "invalid-date-format",
            "calls-last-5min": "10",
            "bytes-last-5min": "1000",
        }

        result = is_session_active(session, threshold_minutes=5)

        assert result is False  # При ошибке парсинга даты сессия считается неактивной

    def test_is_session_active_missing_fields(self):
        """Тест сессии с отсутствующими полями."""
        session = {}  # Пустой словарь

        result = is_session_active(session, threshold_minutes=5)

        assert result is False  # При отсутствии необходимых полей сессия считается неактивной

    def test_filter_active_sessions(self):
        """Тест фильтрации активных сессий."""
        sessions = [
            {
                "hibernate": "no",
                "last-active-at": datetime.now().isoformat(),
                "calls-last-5min": "10",
                "bytes-last-5min": "1000",
            },
            {
                "hibernate": "yes",  # Неактивная сессия
                "last-active-at": datetime.now().isoformat(),
                "calls-last-5min": "5",
                "bytes-last-5min": "500",
            },
            {
                "hibernate": "no",
                "last-active-at": (datetime.now() - timedelta(minutes=10)).isoformat(),
                "calls-last-5min": "0",  # Нет активности
                "bytes-last-5min": "0",
            },
        ]

        result = filter_active_sessions(sessions, threshold_minutes=5)

        assert isinstance(result, list)
        assert len(result) == 1  # Только одна сессия должна быть активной
        assert result[0]["hibernate"] == "no"

    def test_get_session_summary(self):
        """Тест формирования краткого описания сессии."""
        session = {
            "user-name": "Иванов Иван Иванович",
            "app-id": "1CV8C",
            "last-active-at": "2026-02-11T10:06:04",
            "calls-last-5min": "36",
        }

        result = get_session_summary(session)

        assert isinstance(result, str)
        assert "Иванов И.И." in result  # Имя должно быть сокращено
        assert "1CV8C" in result
        assert "10:06:04" in result
        assert "36" in result

    def test_get_session_summary_short_name(self):
        """Тест формирования описания с коротким именем."""
        session = {
            "user-name": "Иванов И.И.",
            "app-id": "Designer",
            "last-active-at": "2026-02-11T10:06:04",
            "calls-last-5min": "0",
        }

        result = get_session_summary(session)

        assert "Иванов И.И." in result  # Имя уже короткое
        assert "Designer" in result

    def test_get_session_summary_long_description(self):
        """Тест формирования описания с длинным описанием."""
        session = {
            "user-name": "Петров Петр Петрович",
            "app-id": "1CV8C",
            "last-active-at": "2026-02-11T10:06:04",
            "calls-last-5min": "125",
        }

        result = get_session_summary(session)

        assert "Петров П.П." in result  # Имя должно быть сокращено
        assert "125" in result


class TestSessionActiveEdgeCases:
    """Тесты для граничных условий в модуле session_active."""

    def test_is_session_active_future_date(self):
        """Тест сессии с датой в будущем."""
        future_time = datetime.now() + timedelta(hours=1)
        session = {
            "hibernate": "no",
            "last-active-at": future_time.isoformat(),
            "calls-last-5min": "10",
            "bytes-last-5min": "1000",
        }

        result = is_session_active(session, threshold_minutes=5)

        # Если дата в будущем, сессия не должна считаться активной
        assert result is False

    def test_is_session_active_zero_threshold(self):
        """Тест сессии с нулевым порогом."""
        now = datetime.now()
        session = {
            "hibernate": "no",
            "last-active-at": now.isoformat(),
            "calls-last-5min": "10",
            "bytes-last-5min": "1000",
        }

        result = is_session_active(session, threshold_minutes=0)

        # Даже при нулевом пороге, если активность была "сейчас", сессия активна
        assert result is True

    def test_is_session_active_large_threshold(self):
        """Тест сессии с большим порогом."""
        old_time = datetime.now() - timedelta(hours=1)
        session = {
            "hibernate": "no",
            "last-active-at": old_time.isoformat(),
            "calls-last-5min": "10",
            "bytes-last-5min": "1000",
        }

        result = is_session_active(session, threshold_minutes=120)  # 2 часа

        # При большом пороге даже старая активность может быть "актуальной"
        assert result is True

    def test_filter_active_sessions_empty_list(self):
        """Тест фильтрации пустого списка сессий."""
        result = filter_active_sessions([])

        assert result == []

    def test_filter_active_sessions_all_inactive(self):
        """Тест фильтрации списка с неактивными сессиями."""
        sessions = [
            {"hibernate": "yes", "last-active-at": datetime.now().isoformat()},
            {"hibernate": "no", "last-active-at": (datetime.now() - timedelta(days=1)).isoformat()},
        ]

        result = filter_active_sessions(sessions)

        assert result == []

    def test_filter_active_sessions_all_active(self):
        """Тест фильтрации списка с активными сессиями."""
        sessions = [
            {
                "hibernate": "no",
                "last-active-at": datetime.now().isoformat(),
                "calls-last-5min": "5",
                "bytes-last-5min": "100",
            },
            {
                "hibernate": "no",
                "last-active-at": datetime.now().isoformat(),
                "calls-last-5min": "10",
                "bytes-last-5min": "200",
            },
        ]

        result = filter_active_sessions(sessions)

        assert len(result) == 2
