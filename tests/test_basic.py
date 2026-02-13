"""
Базовые тесты для проекта zbx-1c-py.
"""

import sys
from pathlib import Path

# Импорты модулей проекта
from zbx_1c_py import main as main_module
from zbx_1c_py import config as config_module
from zbx_1c_py import clusters as clusters_module
from zbx_1c_py import session as session_module
from zbx_1c_py import session_active as session_active_module
from zbx_1c_py import background_jobs as background_jobs_module
from zbx_1c_py.utils import helpers as helpers_module
import zbx_1c_py as project_module

# Добавляем путь к src для импорта модулей проекта
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_project_imports():
    """Тест проверяет, что основные модули проекта могут быть импортированы."""
    # Проверяем, что модули являются модулями Python
    assert hasattr(main_module, "__name__")
    assert hasattr(config_module, "__name__")
    assert hasattr(clusters_module, "__name__")
    assert hasattr(session_module, "__name__")
    assert hasattr(session_active_module, "__name__")
    assert hasattr(background_jobs_module, "__name__")
    assert hasattr(helpers_module, "__name__")


def test_main_module_structure():
    """Тест проверяет структуру основного модуля."""
    # Проверяем наличие основных функций
    assert hasattr(main_module, "main")
    assert hasattr(main_module, "get_discovery_json")
    assert hasattr(main_module, "collect_metrics_for_cluster")
    assert callable(main_module.main)
    assert callable(main_module.get_discovery_json)
    assert callable(main_module.collect_metrics_for_cluster)


def test_config_module_structure():
    """Тест проверяет структуру модуля конфигурации."""
    # Проверяем наличие основных компонентов
    assert hasattr(config_module, "settings")
    assert hasattr(config_module, "Settings")
    assert hasattr(config_module.settings, "rac_path")
    assert hasattr(config_module.settings, "rac_host")
    assert hasattr(config_module.settings, "rac_port")


def test_version_info():
    """Тест проверяет наличие информации о версии."""

    assert hasattr(project_module, "__version__")
    assert isinstance(project_module.__version__, str)
    assert len(project_module.__version__) > 0
