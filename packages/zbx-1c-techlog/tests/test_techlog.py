"""Тесты для zbx-1c-techlog"""

import pytest
from datetime import datetime, timedelta


class TestConfig:
    """Тесты конфигурации"""

    def test_config_import(self):
        """Проверка импорта конфигурации"""
        from zbx_1c_techlog.core.config import TechlogConfig, get_config

        assert TechlogConfig is not None
        assert get_config is not None

    def test_config_instance(self):
        """Проверка создания экземпляра конфигурации"""
        from zbx_1c_techlog.core.config import TechlogConfig

        config = TechlogConfig()
        assert config.zabbix_server == "127.0.0.1"
        assert config.zabbix_port == 10051
        assert config.zabbix_use_api is False


class TestParser:
    """Тесты парсера техжурнала"""

    def test_log_entry_import(self):
        """Проверка импорта LogEntry"""
        from zbx_1c_techlog.reader.parser import LogEntry

        assert LogEntry is not None

    def test_log_entry_from_line(self):
        """Проверка парсинга строки лога"""
        from zbx_1c_techlog.reader.parser import LogEntry

        line = "2024-01-15 10:30:00.123+0300 EXCP process-name computer user description"
        entry = LogEntry.from_line(line)

        assert entry is not None
        assert entry.event_name == "EXCP"
        assert entry.process_name == "process-name"
        assert entry.computer_name == "computer"
        assert entry.user == "user"
        assert entry.description == "description"

    def test_log_entry_from_line_empty(self):
        """Проверка парсинга пустой строки"""
        from zbx_1c_techlog.reader.parser import LogEntry

        entry = LogEntry.from_line("")
        assert entry is None

        entry = LogEntry.from_line("   ")
        assert entry is None

    def test_log_entry_with_duration(self):
        """Проверка парсинга длительности"""
        from zbx_1c_techlog.reader.parser import LogEntry

        line = "2024-01-15 10:30:00.123+0300 CALL process computer user Duration: 500000"
        entry = LogEntry.from_line(line)

        assert entry is not None
        assert entry.event_name == "CALL"
        assert entry.duration == 500000


class TestTechJournalParser:
    """Тесты парсера файлов техжурнала"""

    def test_parser_import(self):
        """Проверка импорта TechJournalParser"""
        from zbx_1c_techlog.reader.parser import TechJournalParser

        parser = TechJournalParser("/tmp/test_logs")
        assert parser is not None


class TestCollector:
    """Тесты сборщика метрик"""

    def test_event_stats_import(self):
        """Проверка импорта EventStats"""
        from zbx_1c_techlog.reader.collector import EventStats

        stats = EventStats()
        assert stats.count == 0
        assert stats.avg_duration == 0.0

    def test_event_stats_add(self):
        """Проверка добавления записи в статистику"""
        from zbx_1c_techlog.reader.collector import EventStats
        from zbx_1c_techlog.reader.parser import LogEntry

        stats = EventStats()
        entry = LogEntry(
            timestamp=datetime.now(),
            event_name="EXCP",
            user="test_user",
            process_name="test_process",
            duration=100000,
            description="Test error",
        )

        stats.add(entry)

        assert stats.count == 1
        assert "test_user" in stats.users
        assert "test_process" in stats.processes
        assert stats.avg_duration == 100.0  # 100000 мкс = 100 мс

    def test_metrics_result_import(self):
        """Проверка импорта MetricsResult"""
        from zbx_1c_techlog.reader.collector import MetricsResult

        result = MetricsResult(
            timestamp=datetime.now(),
            period_seconds=300,
            logs_base_path="/tmp/test_logs",
        )

        assert result.total_events == 0
        assert result.critical_events == 0

    def test_metrics_collector_import(self):
        """Проверка импорта MetricsCollector"""
        from zbx_1c_techlog.reader.collector import MetricsCollector

        collector = MetricsCollector("/tmp/test_logs")
        assert collector is not None


class TestZabbixSender:
    """Тесты отправщика в Zabbix"""

    def test_sender_import(self):
        """Проверка импорта ZabbixSender"""
        from zbx_1c_techlog.zabbix_sender import ZabbixSender, SendResult

        assert ZabbixSender is not None
        assert SendResult is not None

    def test_send_result(self):
        """Проверка SendResult"""
        from zbx_1c_techlog.zabbix_sender import SendResult

        result = SendResult(success=True, sent_count=10, message="OK")

        assert result.success is True
        assert result.sent_count == 10
        assert result.message == "OK"

    def test_sender_initialization(self):
        """Проверка инициализации отправщика"""
        from zbx_1c_techlog.zabbix_sender import ZabbixSender

        sender = ZabbixSender(
            zabbix_server="192.168.1.100",
            zabbix_port=10052,
            zabbix_host="test_host",
        )

        assert sender.zabbix_server == "192.168.1.100"
        assert sender.zabbix_port == 10052
        assert sender.zabbix_host == "test_host"
