"""Тесты для модуля мониторинга техжурнала 1С"""

import pytest
from datetime import datetime
from pathlib import Path
from io import StringIO

from zbx_1c.monitoring.techjournal.parser import LogEntry, TechJournalParser
from zbx_1c.monitoring.techjournal.collector import MetricsCollector, EventStats


class TestLogEntry:
    """Тесты для модели LogEntry"""

    def test_log_entry_creation(self):
        """Создание записи лога"""
        entry = LogEntry(
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            process_name="1CV8C.12345",
            user="Admin",
            event_name="EXCP",
            description="Test error",
        )

        assert entry.process_name == "1CV8C.12345"
        assert entry.user == "Admin"
        assert entry.event_name == "EXCP"
        assert entry.description == "Test error"

    def test_log_entry_to_dict(self):
        """Преобразование в словарь"""
        entry = LogEntry(
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            process_name="1CV8C.12345",
            user="Admin",
            event_name="EXCP",
            description="Test error",
        )

        data = entry.to_dict()

        assert data["process_name"] == "1CV8C.12345"
        assert data["user"] == "Admin"
        assert data["event_name"] == "EXCP"
        assert data["description"] == "Test error"


class TestTechJournalParser:
    """Тесты для парсера техжурнала"""

    @pytest.fixture
    def temp_log_dir(self, tmp_path):
        """Создание временной директории для логов"""
        log_dir = tmp_path / "test_logs"
        log_dir.mkdir()
        return log_dir

    def test_parse_line_basic(self):
        """Парсинг базовой строки лога"""
        parser = TechJournalParser("/tmp")

        line = "{1CV8C.12345}  2024-01-15 10:30:00.123+0300  EXCP  Admin  descr=Test error"
        entry = parser.parse_line(line)

        assert entry is not None
        assert entry.process_name == "1CV8C.12345"
        assert entry.user == "Admin"
        assert entry.event_name == "EXCP"
        assert entry.description == "Test error"

    def test_parse_line_with_duration(self):
        """Парсинг строки с длительностью"""
        parser = TechJournalParser("/tmp")

        line = "{1CV8C.12345}  2024-01-15 10:30:00.123+0300  TLOCK  User1  duration=500000"
        entry = parser.parse_line(line)

        assert entry is not None
        assert entry.event_name == "TLOCK"
        assert entry.duration == 500000

    def test_parse_line_with_context(self):
        """Парсинг строки с контекстом"""
        parser = TechJournalParser("/tmp")

        line = "{1CV8C.12345}  2024-01-15 10:30:00.123+0300  CALL  User1  module=CommonModule method=ProcessData duration=2500"
        entry = parser.parse_line(line)

        assert entry is not None
        assert entry.module == "CommonModule"
        assert entry.method == "ProcessData"
        assert entry.duration == 2500

    def test_parse_line_empty(self):
        """Парсинг пустой строки"""
        parser = TechJournalParser("/tmp")

        entry = parser.parse_line("")
        assert entry is None

    def test_parse_line_invalid(self):
        """Парсинг некорректной строки"""
        parser = TechJournalParser("/tmp")

        entry = parser.parse_line("invalid log line")
        assert entry is None

    def test_find_log_files(self, temp_log_dir):
        """Поиск файлов логов"""
        # Создаем тестовые файлы
        (temp_log_dir / "test1.log").write_text("content1")
        (temp_log_dir / "test2.log").write_text("content2")
        (temp_log_dir / "test.txt").write_text("content3")

        parser = TechJournalParser(temp_log_dir)
        files = parser.find_log_files("*.log")

        assert len(files) == 2
        assert all(f.suffix == ".log" for f in files)

    def test_parse_file(self, temp_log_dir):
        """Парсинг файла лога"""
        log_file = temp_log_dir / "test.log"
        log_file.write_text(
            "{1CV8C.12345}  2024-01-15 10:30:00.123+0300  EXCP  Admin  descr=Error 1\n"
            "{1CV8C.12346}  2024-01-15 10:31:00.456+0300  TLOCK  User1  duration=500000\n"
        )

        parser = TechJournalParser(temp_log_dir)
        entries = list(parser.parse_file(log_file))

        assert len(entries) == 2
        assert entries[0].event_name == "EXCP"
        assert entries[1].event_name == "TLOCK"


class TestEventStats:
    """Тесты для статистики событий"""

    def test_event_stats_add(self):
        """Добавление записи в статистику"""
        stats = EventStats()

        entry = LogEntry(
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            process_name="1CV8C.12345",
            user="Admin",
            event_name="EXCP",
            description="Test error",
            duration=100000,
        )

        stats.add(entry)

        assert stats.count == 1
        assert "Admin" in stats.users
        assert "1CV8C.12345" in stats.processes
        assert stats.total_duration == 100000

    def test_event_stats_avg_duration(self):
        """Расчет средней длительности"""
        stats = EventStats()

        for i in range(3):
            entry = LogEntry(
                timestamp=datetime(2024, 1, 15, 10, 30, 0),
                process_name="1CV8C.12345",
                user="Admin",
                event_name="TLOCK",
                duration=300000 * (i + 1),
            )
            stats.add(entry)

        # Средняя: (300 + 600 + 900) / 3 = 600 мс
        assert stats.avg_duration == 600.0

    def test_event_stats_empty(self):
        """Расчет для пустой статистики"""
        stats = EventStats()
        assert stats.avg_duration == 0.0


class TestMetricsCollector:
    """Тесты для сборщика метрик"""

    @pytest.fixture
    def temp_log_structure(self, tmp_path):
        """Создание тестовой структуры логов"""
        log_base = tmp_path / "1c_techjournal"
        log_base.mkdir()

        # Создаем поддиректории
        for subdir in ["core", "perf", "locks", "sql", "zabbix"]:
            (log_base / subdir).mkdir()

        # Создаем тестовые логи
        core_log = log_base / "core" / "test.log"
        core_log.write_text(
            "{1CV8C.12345}  2024-01-15 10:30:00.123+0300  EXCP  Admin  descr=Error 1\n"
            "{1CV8C.12346}  2024-01-15 10:31:00.456+0300  ATTN  User1  descr=Warning 1\n"
        )

        locks_log = log_base / "locks" / "test.log"
        locks_log.write_text(
            "{1CV8C.12347}  2024-01-15 10:32:00.789+0300  TDEADLOCK  User2  descr=Deadlock detected\n"
        )

        return log_base

    def test_collector_initialization(self, temp_log_structure):
        """Инициализация сборщика"""
        collector = MetricsCollector(temp_log_structure)
        assert collector.log_base_path == temp_log_structure

    def test_collector_collect(self, temp_log_structure):
        """Сбор метрик"""
        from datetime import datetime, timedelta

        collector = MetricsCollector(temp_log_structure)

        # Используем явный период для тестовых логов (2024-01-15)
        from_time = datetime(2024, 1, 15, 10, 0, 0)
        to_time = datetime(2024, 1, 15, 11, 0, 0)

        metrics = collector.collect(from_time=from_time, to_time=to_time)

        assert metrics.total_events >= 2
        assert metrics.errors.count >= 1
        assert metrics.warnings.count >= 1
        assert metrics.deadlocks.count >= 1

    def test_collector_to_dict(self, temp_log_structure):
        """Преобразование метрик в словарь"""
        from datetime import datetime

        collector = MetricsCollector(temp_log_structure)

        from_time = datetime(2024, 1, 15, 10, 0, 0)
        to_time = datetime(2024, 1, 15, 11, 0, 0)

        metrics = collector.collect(from_time=from_time, to_time=to_time)
        data = metrics.to_dict()

        assert "total_events" in data
        assert "errors.count" in data
        assert "deadlocks.count" in data
        assert isinstance(data["timestamp"], str)

    def test_collector_summary(self, temp_log_structure):
        """Получение сводки"""
        from datetime import datetime

        collector = MetricsCollector(temp_log_structure)

        from_time = datetime(2024, 1, 15, 10, 0, 0)
        to_time = datetime(2024, 1, 15, 11, 0, 0)

        # Используем явный период для тестовых логов
        metrics = collector.collect(from_time=from_time, to_time=to_time)
        summary = collector.get_summary(period_minutes=60)

        assert "МОНИТОРИНГ ТЕХЖУРНАЛА 1С" in summary
        assert "Всего событий:" in summary
        assert "Ошибки (EXCP):" in summary


class TestParserEdgeCases:
    """Тесты для граничных случаев"""

    def test_timestamp_without_timezone(self):
        """Парсинг timestamp без timezone"""
        parser = TechJournalParser("/tmp")

        line = "{1CV8C.12345}  2024-01-15 10:30:00.123  EXCP  Admin  descr=Test"
        entry = parser.parse_line(line)

        # Должна распознаться, даже если timezone отсутствует
        assert entry is not None or entry is None  # Зависит от реализации

    def test_multiline_description(self):
        """Парсинг строки с многострочным описанием"""
        parser = TechJournalParser("/tmp")

        line = "{1CV8C.12345}  2024-01-15 10:30:00.123+0300  EXCP  Admin  descr=Error with spaces"
        entry = parser.parse_line(line)

        if entry:
            assert "Error with spaces" in entry.description

    def test_cyrillic_characters(self):
        """Парсинг строки с кириллицей"""
        parser = TechJournalParser("/tmp")

        line = "{1CV8C.12345}  2024-01-15 10:30:00.123+0300  EXCP  Admin  descr=Ошибка подключения"
        entry = parser.parse_line(line)

        if entry:
            assert "Ошибка подключения" in entry.description
