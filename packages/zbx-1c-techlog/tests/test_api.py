"""Тесты для FastAPI API техжурнала"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile


@pytest.fixture
def client():
    """Создание тестового клиента"""
    from zbx_1c_techlog.api.app import app

    with TestClient(app) as client:
        yield client


class TestHealthEndpoint:
    """Тесты health check"""

    def test_health_check(self, client):
        """Проверка health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestStructureEndpoint:
    """Тесты структуры логов"""

    def test_get_structure(self, client):
        """Получение структуры логов"""
        response = client.get("/api/structure")
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "base_path" in data
            assert "directories" in data
            assert "total_files" in data


class TestMetricsEndpoint:
    """Тесты метрик"""

    def test_get_metrics(self, client):
        """Получение метрик"""
        response = client.get("/api/metrics?period_minutes=5")
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "period_seconds" in data
        assert "total_events" in data
        assert "errors" in data
        assert "deadlocks" in data

        # Проверяем новые поля
        errors = data["errors"]
        assert "memory_usage_bytes" in errors
        assert "network_errors" in errors
        assert "top_slow_methods" in errors
        assert isinstance(errors["memory_usage_bytes"], int)
        assert isinstance(errors["network_errors"], int)
        assert isinstance(errors["top_slow_methods"], list)

    def test_get_metrics_invalid_period(self, client):
        """Проверка невалидного периода"""
        response = client.get("/api/metrics?period_minutes=0")
        assert response.status_code == 422

        response = client.get("/api/metrics?period_minutes=2000")
        assert response.status_code == 422


class TestMetricsZabbixEndpoint:
    """Тесты эндпоинта /api/metrics/zabbix для Zabbix LLD"""

    def test_get_metrics_zabbix(self, client):
        """Получение метрик в формате Zabbix LLD"""
        response = client.get("/api/metrics/zabbix?period_minutes=5")
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "period_minutes" in data
        assert "hostname" in data
        assert "metrics" in data
        assert "count" in data
        assert isinstance(data["metrics"], list)
        assert data["count"] == len(data["metrics"])

        # Проверяем структуру отдельных метрик
        if data["metrics"]:
            metric = data["metrics"][0]
            assert "host" in metric
            assert "key" in metric
            assert "value" in metric

    def test_get_metrics_zabbix_with_hostname(self, client):
        """Получение метрик с указанием hostname"""
        response = client.get("/api/metrics/zabbix?period_minutes=5&hostname=test-server-01")
        assert response.status_code == 200
        data = response.json()
        assert data["hostname"] == "test-server-01"

    def test_get_metrics_zabbix_invalid_period(self, client):
        """Проверка невалидного периода для Zabbix LLD"""
        response = client.get("/api/metrics/zabbix?period_minutes=0")
        assert response.status_code == 422

        response = client.get("/api/metrics/zabbix?period_minutes=2000")
        assert response.status_code == 422


class TestCheckEndpoint:
    """Тесты проверки логов"""

    def test_check_logs(self, client):
        """Проверка check endpoint"""
        response = client.get("/api/check")
        assert response.status_code == 200
        data = response.json()
        assert "base_path" in data
        assert "exists" in data
        assert "directories" in data


class TestSummaryEndpoint:
    """Тесты сводки"""

    def test_get_summary(self, client):
        """Получение сводки"""
        response = client.get("/api/summary?period_minutes=5")
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "period_minutes" in data


class TestZabbixDataEndpoint:
    """Тесты данных для Zabbix"""

    def test_get_zabbix_data(self, client):
        """Получение данных для Zabbix"""
        response = client.get("/api/zabbix-data?period_minutes=5")
        assert response.status_code == 200
        data = response.json()
        assert "hostname" in data
        assert "metrics" in data
        assert "count" in data


class TestEventsEndpoint:
    """Тесты событий"""

    def test_get_events(self, client):
        """Получение событий"""
        response = client.get("/api/events?period_minutes=60")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "count" in data
        assert "limit" in data

    def test_get_events_with_filter(self, client):
        """Получение событий с фильтром"""
        response = client.get("/api/events?period_minutes=60&event_type=EXCP&limit=50")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] <= 50


class TestIntegration:
    """Интеграционные тесты"""

    def test_full_api_flow(self, client):
        """Полный цикл работы с API"""
        # 1. Health check
        health = client.get("/health")
        assert health.status_code == 200

        # 2. Проверка логов
        check = client.get("/api/check")
        assert check.status_code == 200

        # 3. Структура
        structure = client.get("/api/structure")
        assert structure.status_code in [200, 404]

        # 4. Метрики
        metrics = client.get("/api/metrics?period_minutes=5")
        assert metrics.status_code == 200

        # 5. Сводка
        summary = client.get("/api/summary?period_minutes=5")
        assert summary.status_code == 200

        # 6. Данные для Zabbix
        zabbix = client.get("/api/zabbix-data?period_minutes=5")
        assert zabbix.status_code == 200

        # 7. События
        events = client.get("/api/events?period_minutes=60")
        assert events.status_code == 200
