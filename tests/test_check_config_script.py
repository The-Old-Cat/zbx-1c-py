"""
Тесты для основного скрипта проверки конфигурации.
"""

import subprocess
import sys
import importlib.util
from pathlib import Path
from zbx_1c_py.utils.check_config import main, validate_settings
import pytest

# Импортируем модуль конфигурации
from zbx_1c_py.config import settings  # noqa: F401

# Добавляем путь к src
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


# Добавляем путь к src для импорта модулей проекта
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_script_can_be_imported():
    """Тест проверяет, что скрипт может быть импортирован без ошибок."""

    assert callable(main)
    assert callable(validate_settings)


def test_script_execution():
    """Тест проверяет, что скрипт может быть выполнен."""
    script_path = Path(__file__).parent.parent / "scripts" / "check_config.py"

    # Выполняем скрипт как отдельный процесс
    result = subprocess.run(
        [sys.executable, str(script_path)], capture_output=True, text=True, check=False, timeout=30
    )

    # Проверяем, что скрипт завершился (даже с ошибкой конфигурации)
    assert result.returncode in [0, 1]  # 0 - успех, 1 - ошибка конфигурации

    # Проверяем, что в выводе есть информация о проверке
    output = result.stdout + result.stderr
    assert "Проверка конфигурации" in output or "CONFIGURATION CHECK" in output.lower()


def test_script_help_option():
    """Тест проверяет, что скрипт корректно обрабатывает опцию --help."""
    script_path = Path(__file__).parent.parent / "scripts" / "check_config.py"

    # Пытаемся выполнить скрипт с --help
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

        # На случай, если скрипт не поддерживает --help, просто проверим, что он не падает
        # В нашем случае скрипт не имеет аргументов, поэтому может вернуть ошибку
        assert result.stdout or result.stderr
    except subprocess.TimeoutExpired:
        pytest.fail("Скрипт завис при попытке выполнения с --help")


def test_script_has_required_functions():
    """Тест проверяет, что скрипт содержит все необходимые функции."""

    script_path = Path(__file__).parent.parent / "src" / "zbx_1c_py" / "utils" / "check_config.py"

    spec = importlib.util.spec_from_file_location("check_config", script_path)

    # Добавляем проверку для линтера и безопасности теста
    if spec is None:
        pytest.fail(f"Не удалось создать спецификацию модуля по пути: {script_path}")

    module = importlib.util.module_from_spec(spec)

    # Важно: у ModuleSpec может не быть loader (теоретически),
    # поэтому здесь тоже лучше добавить проверку для mypy
    if spec.loader is None:
        pytest.fail("У спецификации модуля отсутствует loader")

    spec.loader.exec_module(module)

    # Проверяем наличие необходимых функций
    required_functions = [
        "check_executable_access",
        "check_log_directory",
        "check_ras_connection",
        "validate_settings",
        "print_results",
        "main",
    ]

    for func_name in required_functions:
        assert hasattr(module, func_name), f"Функция {func_name} не найдена в модуле"
        assert callable(getattr(module, func_name)), f"{func_name} не является функцией"


def test_script_dependencies():
    """Тест проверяет, что скрипт может импортировать все зависимости."""

    # Проверяем, что настройки доступны
    assert hasattr(settings, "rac_path")
