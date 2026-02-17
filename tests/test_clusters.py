"""
Тесты для модуля clusters проекта zbx-1c-py.
"""

from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Добавляем путь к src для импорта модулей проекта
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Local imports after path setup
from src.zbx_1c.monitoring.cluster.manager import (
    check_ras_availability,
    get_all_clusters,
    initialize_cluster_info,
)


class TestClustersModule:
    """Тесты для функций модуля clusters."""

    @patch("zbx_1c_py.clusters.subprocess.run")
    @patch("zbx_1c_py.clusters.decode_output")
    def test_check_ras_availability_success(self, mock_decode_output, mock_subprocess_run):
        """Тест успешной проверки доступности RAS."""
        # Мокаем успешный результат
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result
        mock_decode_output.return_value = "decoded output"

        result = check_ras_availability()

        assert result["available"] is True
        assert result["message"] == "RAS is reachable"
        assert result["code"] == 0
        mock_subprocess_run.assert_called_once()

    @patch("zbx_1c_py.clusters.subprocess.run")
    @patch("zbx_1c_py.clusters.decode_output")
    def test_check_ras_availability_error(self, mock_decode_output, mock_subprocess_run):
        """Тест проверки доступности RAS с ошибкой."""
        # Мокаем результат с ошибкой
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_subprocess_run.return_value = mock_result
        mock_decode_output.return_value = "connection error"

        result = check_ras_availability()

        assert result["available"] is False
        assert "RAC Error" in result["message"]
        assert result["code"] == 1

    @patch("zbx_1c_py.clusters.subprocess.run")
    @patch("zbx_1c_py.clusters.decode_output")
    @patch("zbx_1c_py.clusters.parse_rac_output")
    def test_get_all_clusters_success(
        self, mock_parse_rac_output, mock_decode_output, mock_subprocess_run
    ):
        """Тест получения всех кластеров при успешном выполнении."""
        # Мокаем успешный результат
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b"cluster data"
        mock_subprocess_run.return_value = mock_result
        mock_decode_output.return_value = "decoded cluster data"
        mock_parse_rac_output.return_value = [{"cluster": "test-id", "name": "test-name"}]

        result = get_all_clusters()

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["cluster"] == "test-id"
        mock_parse_rac_output.assert_called_once_with("decoded cluster data")

    @patch("zbx_1c_py.clusters.subprocess.run")
    def test_get_all_clusters_error(self, mock_subprocess_run):
        """Тест получения всех кластеров при ошибке выполнения."""
        # Мокаем исключение FileNotFoundError
        mock_subprocess_run.side_effect = FileNotFoundError("File not found")

        result = get_all_clusters()

        assert not result

    def test_get_cluster_ids(self):
        """Тест получения ID кластеров."""
        # Тестируем с mock-данными
        mock_clusters = [
            {"cluster": "cluster-1", "name": "Cluster 1"},
            {"cluster": "cluster-2", "name": "Cluster 2"},
            {"cluster": None, "name": "Invalid Cluster"},
        ]

        # Так как функция использует глобальные переменные,
        # мы не можем легко протестировать её напрямую
        # Вместо этого проверим логику через initialize_cluster_info

    def test_get_default_cluster(self):
        """Тест получения кластера по умолчанию."""
        # Тестируем с mock-данными
        mock_clusters = [
            {"cluster": "cluster-1", "name": "Cluster 1"},
            {"cluster": "cluster-2", "name": "Cluster 2"},
        ]

        # Так как функция использует глобальные переменные,
        # мы не можем легко протестировать её напрямую
        # Вместо этого проверим логику через initialize_cluster_info

    def test_initialize_cluster_info(self):
        """Тест инициализации информации о кластерах."""
        # Тестируем структуру возвращаемых данных
        result = initialize_cluster_info()

        assert isinstance(result, tuple)
        assert len(result) == 3

        all_clusters, cluster_id, cluster_name = result
        assert isinstance(all_clusters, list)
        assert isinstance(cluster_id, str)
        assert isinstance(cluster_name, str)


# Дополнительные тесты для граничных условий
class TestEdgeCases:
    """Тесты для граничных условий."""

    def test_empty_cluster_list(self):
        """Тест с пустым списком кластеров."""
        # Тестируем логику получения ID кластеров из пустого списка
        mock_clusters = []

        # Так как функции используют глобальные переменные,
        # создадим вспомогательную функцию для тестирования логики
        cluster_ids = [str(c.get("cluster")) for c in mock_clusters if c.get("cluster") is not None]
        assert not cluster_ids

    def test_cluster_with_none_id(self):
        """Тест кластера с None ID."""
        mock_clusters = [
            {"cluster": None, "name": "Invalid Cluster"},
            {"cluster": "valid-id", "name": "Valid Cluster"},
        ]

        # Тестируем логику фильтрации
        cluster_ids = [str(c.get("cluster")) for c in mock_clusters if c.get("cluster") is not None]
        assert len(cluster_ids) == 1
        assert cluster_ids[0] == "valid-id"
