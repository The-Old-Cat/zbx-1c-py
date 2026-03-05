"""Тесты для zbx-1c-rac"""

import pytest


class TestConfig:
    """Тесты конфигурации"""

    def test_config_import(self):
        """Проверка импорта конфигурации"""
        from zbx_1c_rac.core.config import RacConfig, get_config

        assert RacConfig is not None
        assert get_config is not None

    def test_config_instance(self):
        """Проверка создания экземпляра конфигурации"""
        from zbx_1c_rac.core.config import RacConfig

        config = RacConfig()
        assert config.rac_host == "127.0.0.1"
        assert config.rac_port == 1545


class TestConverters:
    """Тесты конвертеров"""

    def test_decode_output(self):
        """Проверка декодирования вывода"""
        from zbx_1c_rac.utils.converters import decode_output

        # UTF-8
        data_utf8 = "test".encode("utf-8")
        assert decode_output(data_utf8) == "test"

        # CP1251 (кириллица)
        data_cp1251 = "тест".encode("cp1251")
        assert decode_output(data_cp1251) == "тест"

    def test_parse_rac_output(self):
        """Проверка парсинга вывода rac"""
        from zbx_1c_rac.utils.converters import parse_rac_output

        output = """cluster: abc-123
name: Test Cluster
host: 127.0.0.1
port: 1545

cluster: def-456
name: Prod Cluster
host: 192.168.1.1
port: 1545
"""
        result = parse_rac_output(output)

        assert len(result) == 2
        assert result[0]["cluster"] == "abc-123"
        assert result[0]["name"] == "Test Cluster"
        assert result[1]["cluster"] == "def-456"

    def test_format_lld_data(self):
        """Проверка форматирования LLD данных"""
        from zbx_1c_rac.utils.converters import format_lld_data

        data = [{"id": "abc", "name": "Test"}]
        result = format_lld_data(data)

        assert "data" in result
        assert len(result["data"]) == 1


class TestRacClient:
    """Тесты RAC клиента"""

    def test_check_ras_availability_false(self):
        """Проверка недоступности RAS (тестовый порт)"""
        from zbx_1c_rac.utils.rac_client import check_ras_availability

        # Проверяем заведомо недоступный порт
        result = check_ras_availability("127.0.0.1", 59999, timeout=1)
        assert result is False


class TestSessionCollector:
    """Тесты сборщика сессий"""

    def test_session_collector_import(self):
        """Проверка импорта SessionCollector"""
        from zbx_1c_rac.monitoring.session.collector import SessionCollector

        collector = SessionCollector()
        assert collector is not None

    def test_is_active_static(self):
        """Проверка проверки активности сессии"""
        from zbx_1c_rac.monitoring.session.collector import SessionCollector

        # Активная сессия (Designer, недавняя активность)
        session_active = {
            "app": "Designer",
            "last-active-at": "2024-01-15T14:30:00",
            "hibernate": "no",
        }

        # Неактивная сессия (старая активность)
        session_inactive = {
            "app": "Designer",
            "last-active-at": "2024-01-01T14:30:00",
            "hibernate": "yes",
        }

        # Проверяем с фиксированным временем
        # Для простоты проверяем только логику hibernate
        assert SessionCollector._is_active(
            session_inactive, 5, True, 1, True, 1024
        ) is False


class TestJobReader:
    """Тесты чтения заданий"""

    def test_job_reader_import(self):
        """Проверка импорта JobReader"""
        from zbx_1c_rac.monitoring.jobs.reader import JobReader

        reader = JobReader()
        assert reader is not None


class TestInfobaseMonitor:
    """Тесты мониторинга ИБ"""

    def test_infobase_monitor_import(self):
        """Проверка импорта InfobaseMonitor"""
        from zbx_1c_rac.monitoring.infobase.monitor import InfobaseMonitor

        monitor = InfobaseMonitor()
        assert monitor is not None


class TestClusterManager:
    """Тесты менеджера кластеров"""

    def test_cluster_manager_import(self):
        """Проверка импорта ClusterManager"""
        from zbx_1c_rac.monitoring.cluster.manager import ClusterManager

        manager = ClusterManager()
        assert manager is not None

    def test_get_server_memory(self):
        """Проверка получения памяти процессов"""
        from zbx_1c_rac.monitoring.cluster.manager import ClusterManager

        manager = ClusterManager()
        memory = manager.get_server_memory()

        assert "rphost" in memory
        assert "rmngr" in memory
        assert "ragent" in memory
        assert "total_mb" in memory
