"""
Тесты для модуля background_jobs проекта zbx-1c-py.
"""

from datetime import datetime, timedelta
import sys
from pathlib import Path

# Добавляем путь к src для импорта модулей проекта
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Локальный импорт после настройки пути
from src.zbx_1c.monitoring.jobs.reader import (
    is_background_job_active,
    filter_active_background_jobs,
    get_background_job_summary,
)


class TestBackgroundJobsModule:
    """Тесты для функций модуля background_jobs."""

    def test_is_background_job_active_fully_active(self):
        """Тест активного фонового задания с полной активностью."""
        job = {
            "state": "active",
            "duration": "300000",  # 5 минут в миллисекундах
            "started-at": (datetime.now() - timedelta(minutes=3))
            .isoformat()
            .replace("+00:00", "Z"),
            "job-id": "123",
            "user-name": "test_user",
            "description": "Test job",
        }

        result = is_background_job_active(job, max_duration_minutes=10)

        assert result is True

    def test_is_background_job_active_completed_state(self):
        """Тест фонового задания в состоянии completed."""
        job = {
            "state": "completed",  # Завершено
            "duration": "300000",
            "started-at": datetime.now().isoformat().replace("+00:00", "Z"),
            "job-id": "123",
        }

        result = is_background_job_active(job, max_duration_minutes=10)

        assert result is False

    def test_is_background_job_active_failed_state(self):
        """Тест фонового задания в состоянии failed."""
        job = {
            "state": "failed",  # Ошибка
            "duration": "300000",
            "started-at": datetime.now().isoformat().replace("+00:00", "Z"),
            "job-id": "123",
        }

        result = is_background_job_active(job, max_duration_minutes=10)

        assert result is False

    def test_is_background_job_active_canceled_state(self):
        """Тест фонового задания в состоянии canceled."""
        job = {
            "state": "canceled",  # Отменено
            "duration": "300000",
            "started-at": datetime.now().isoformat().replace("+00:00", "Z"),
            "job-id": "123",
        }

        result = is_background_job_active(job, max_duration_minutes=10)

        assert result is False

    def test_is_background_job_active_exceeded_duration(self):
        """Тест фонового задания с превышением длительности."""
        job = {
            "state": "active",
            "duration": "1200000",  # 20 минут в миллисекундах
            "started-at": (datetime.now() - timedelta(minutes=15))
            .isoformat()
            .replace("+00:00", "Z"),
            "job-id": "123",
        }

        result = is_background_job_active(job, max_duration_minutes=10)  # Порог 10 минут

        assert result is False  # Превышение порога

    def test_is_background_job_active_valid_duration(self):
        """Тест фонового задания с допустимой длительностью."""
        job = {
            "state": "active",
            "duration": "300000",  # 5 минут в миллисекундах
            "started-at": (datetime.now() - timedelta(minutes=3))
            .isoformat()
            .replace("+00:00", "Z"),
            "job-id": "123",
        }

        result = is_background_job_active(job, max_duration_minutes=10)  # Порог 10 минут

        assert result is True  # В пределах порога

    def test_is_background_job_active_invalid_started_at(self):
        """Тест фонового задания с некорректной датой начала."""
        job = {
            "state": "active",
            "duration": "300000",
            "started-at": "invalid-date-format",
            "job-id": "123",
        }

        result = is_background_job_active(job, max_duration_minutes=10)

        assert result is False  # При ошибке парсинга даты задание считается неактивным

    def test_is_background_job_active_future_start_time(self):
        """Тест фонового задания с датой начала в будущем."""
        future_time = datetime.now() + timedelta(hours=1)
        job = {
            "state": "active",
            "duration": "0",  # 0 миллисекунд
            "started-at": future_time.isoformat().replace("+00:00", "Z"),
            "job-id": "123",
        }

        result = is_background_job_active(job, max_duration_minutes=10)

        assert result is False  # Дата начала в будущем - задание не может быть активным

    def test_is_background_job_active_missing_fields(self):
        """Тест фонового задания с отсутствующими полями."""
        job = {}  # Пустой словарь

        result = is_background_job_active(job, max_duration_minutes=10)

        assert result is False  # При отсутствии необходимых полей задание считается неактивным

    def test_is_background_job_active_invalid_duration(self):
        """Тест фонового задания с некорректной длительностью."""
        job = {
            "state": "active",
            "duration": "not_a_number",  # Некорректное значение
            "started-at": datetime.now().isoformat().replace("+00:00", "Z"),
            "job-id": "123",
        }

        result = is_background_job_active(job, max_duration_minutes=10)

        # Если поле duration некорректно, проверка длительности пропускается
        # и задание оценивается по другим критериям
        # В данном случае state=active и started-at корректна,
        # но при ошибке парсинга duration проверка длительности пропускается
        # и задание может быть активным, если другие условия выполнены
        # Но т.к. duration не число, то проверка длительности пропускается
        # и задание оценивается только по состоянию и времени начала
        assert result is True  # Только state проверяется, остальные поля игнорируются при ошибках

    def test_filter_active_background_jobs(self):
        """Тест фильтрации активных фоновых заданий."""
        jobs = [
            {
                "state": "active",
                "duration": "300000",  # 5 минут
                "started-at": (datetime.now() - timedelta(minutes=3))
                .isoformat()
                .replace("+00:00", "Z"),
                "job-id": "123",
            },
            {
                "state": "completed",  # Неактивное задание
                "duration": "600000",  # 10 минут
                "started-at": (datetime.now() - timedelta(minutes=8))
                .isoformat()
                .replace("+00:00", "Z"),
                "job-id": "124",
            },
            {
                "state": "active",
                "duration": "1200000",  # 20 минут
                "started-at": (datetime.now() - timedelta(minutes=15))
                .isoformat()
                .replace("+00:00", "Z"),
                "job-id": "125",
            },  # Превышение порога
        ]

        result = filter_active_background_jobs(jobs, max_duration_minutes=10)

        assert isinstance(result, list)
        assert len(result) == 1  # Только одно задание должно быть активным
        first_result = result[0]
        assert first_result["job-id"] == "123"

    def test_get_background_job_summary(self):
        """Тест формирования краткого описания фонового задания."""
        job = {
            "job-id": "123",
            "user-name": "Иванов Иван Иванович",
            "description": "Расчёт зарплаты за февраль 2026",
            "duration": "125000",  # 125 секунд
            "progress": "45",
        }

        result = get_background_job_summary(job)

        assert isinstance(result, str)
        assert "ID: 123" in result
        assert "Иванов И.И." in result  # Имя должно быть сокращено
        assert "..." in result  # Описание должно быть сокращено
        assert "125.0s" in result  # Длительность в секундах
        assert "45%" in result  # Прогресс

    def test_get_background_job_summary_short_description(self):
        """Тест формирования описания с коротким описанием."""
        job = {
            "job-id": "124",
            "user-name": "Петров П.П.",
            "description": "Обновление",
            "duration": "5000",  # 5 секунд
            "progress": "100",
        }

        result = get_background_job_summary(job)

        assert "ID: 124" in result
        assert "Петров П.П." in result
        assert "Обновление" in result  # Короткое описание не сокращается
        assert "5.0s" in result
        assert "100%" in result

    def test_get_background_job_summary_long_description(self):
        """Тест формирования описания с длинным описанием."""
        job = {
            "job-id": "125",
            "user-name": "Сидоров Сидор Сидорович",
            "description": "Очень длинное описание задания, которое превышает допустимую длину",
            "duration": "7200000",  # 2 часа
            "progress": "5",
        }

        result = get_background_job_summary(job)

        assert "ID: 125" in result
        assert "Сидоров С.С." in result  # Имя сокращено
        assert "Очень длинное описание..." in result  # Длинное описание сокращено
        assert "7200.0s" in result
        assert "5%" in result

    def test_get_background_job_summary_no_progress(self):
        """Тест формирования описания без прогресса."""
        job = {
            "job-id": "126",
            "user-name": "Козлов К.К.",
            "description": "Тестовое задание",
            "duration": "1000",  # 1 секунда
            "progress": "0",
        }

        result = get_background_job_summary(job)

        assert "ID: 126" in result
        assert "0%" in result  # Прогресс 0%

    def test_get_background_job_summary_no_progress_field(self):
        """Тест формирования описания без поля прогресса."""
        job = {
            "job-id": "127",
            "user-name": "Новиков Н.Н.",
            "description": "Задание без прогресса",
            "duration": "2000",  # 2 секунды
            # Нет поля progress
        }

        result = get_background_job_summary(job)

        assert "ID: 127" in result
        assert "N/A" in result  # Прогресс не указан


class TestBackgroundJobsEdgeCases:
    """Тесты для граничных условий в модуле background_jobs."""

    def test_is_background_job_active_zero_max_duration(self):
        """Тест фонового задания с нулевым максимальным временем."""
        job = {
            "state": "active",
            "duration": "1000",  # 1 секунда
            "started-at": datetime.now().isoformat().replace("+00:00", "Z"),
            "job-id": "123",
        }

        result = is_background_job_active(job, max_duration_minutes=0)

        # При нулевом пороге любая длительность > 0 превышает порог
        assert result is False

    def test_is_background_job_active_very_high_max_duration(self):
        """Тест фонового задания с очень высоким максимальным временем."""
        job = {
            "state": "active",
            "duration": "36000000",  # 10 часов
            "started-at": (datetime.now() - timedelta(hours=8)).isoformat().replace("+00:00", "Z"),
            "job-id": "123",
        }

        result = is_background_job_active(job, max_duration_minutes=1200)  # 20 часов

        assert result is True  # В пределах порога

    def test_filter_active_background_jobs_empty_list(self):
        """Тест фильтрации пустого списка заданий."""
        result = filter_active_background_jobs([])

        assert result == []

    def test_filter_active_background_jobs_all_inactive(self):
        """Тест фильтрации списка с неактивными заданиями."""
        jobs = [
            {
                "state": "completed",
                "duration": "1000",
                "started-at": datetime.now().isoformat().replace("+00:00", "Z"),
            },
            {
                "state": "failed",
                "duration": "2000",
                "started-at": datetime.now().isoformat().replace("+00:00", "Z"),
            },
        ]

        result = filter_active_background_jobs(jobs)

        assert result == []

    def test_filter_active_background_jobs_all_active(self):
        """Тест фильтрации списка с активными заданиями."""
        jobs = [
            {
                "state": "active",
                "duration": "1000",
                "started-at": (datetime.now() - timedelta(seconds=30))
                .isoformat()
                .replace("+00:00", "Z"),
                "job-id": "1",
            },
            {
                "state": "active",
                "duration": "2000",
                "started-at": (datetime.now() - timedelta(seconds=60))
                .isoformat()
                .replace("+00:00", "Z"),
                "job-id": "2",
            },
        ]

        result = filter_active_background_jobs(jobs)

        assert len(result) == 2
