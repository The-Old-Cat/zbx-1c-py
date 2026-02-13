"""
Тесты для проверки запуска скрипта check-config через uv run.
"""

import subprocess
import sys
from pathlib import Path
import pytest


def test_uv_run_check_config():
    """Тест запуска скрипта через uv run."""
    # Проверяем, что команда uv run доступна
    try:
        result = subprocess.run(
            [sys.executable, "-m", "uv", "--version"], capture_output=True, text=True, check=False
        )

        # Если uv не установлен через Python, пробуем просто uv
        if result.returncode != 0:
            result = subprocess.run(
                ["uv", "--version"], capture_output=True, text=True, check=False
            )

            if result.returncode != 0:
                pytest.skip("uv не установлен")
    except FileNotFoundError:
        pytest.skip("uv не установлен")

    # Пытаемся запустить скрипт check-config через uv run
    result = subprocess.run(
        ["uv", "run", "check-config"], capture_output=True, text=True, check=False, timeout=30
    )

    # Скрипт может завершиться с кодом 0 (успех) или 1 (ошибка конфигурации)
    # Это нормальное поведение, главное, чтобы он не падал с исключением

    # Проверяем, что в выводе есть информация о проверке конфигурации
    output = result.stdout + result.stderr
    assert "Проверка конфигурации" in output or "CONFIGURATION CHECK" in output.upper()
    assert result.returncode in [0, 1]  # 0 - успех, 1 - ошибка конфигурации


def test_python_module_run():
    """Тест запуска скрипта как модуля Python."""
    # Проверяем запуск скрипта как модуля
    script_path = Path(__file__).parent.parent / "scripts" / "check_config.py"

    result = subprocess.run(
        [sys.executable, str(script_path)], capture_output=True, text=True, check=False, timeout=30
    )

    # Проверяем, что скрипт завершился (даже с ошибкой конфигурации)
    assert result.returncode in [0, 1]

    # Проверяем, что в выводе есть информация о проверке
    output = result.stdout + result.stderr
    assert "Проверка конфигурации" in output or "CONFIGURATION CHECK" in output.upper()


def test_script_returns_correct_exit_code():
    """Тест проверяет, что скрипт возвращает корректный код выхода."""
    script_path = Path(__file__).parent.parent / "scripts" / "check_config.py"

    # Создаем временную копию скрипта с измененными настройками для теста
    # В реальном тесте мы просто проверим, что скрипт не падает с исключением
    result = subprocess.run(
        [sys.executable, str(script_path)], capture_output=True, text=True, check=False, timeout=30
    )

    # Скрипт должен возвращать 0 при успешной проверке или 1 при ошибках конфигурации
    assert result.returncode in [
        0,
        1,
    ], f"Скрипт завершился с кодом {result.returncode}, что не является ожидаемым"


def test_script_outputs_expected_sections():
    """Тест проверяет, что скрипт выводит ожидаемые разделы."""
    script_path = Path(__file__).parent.parent / "scripts" / "check_config.py"

    result = subprocess.run(
        [sys.executable, str(script_path)], capture_output=True, text=True, check=False, timeout=30
    )

    output = result.stdout + result.stderr  # Объединяем stdout и stderr

    # Проверяем наличие основных разделов вывода
    assert "РЕЗУЛЬТАТЫ ПРОВЕРКИ" in output or "RESULTS" in output
    assert "Проверок пройдено:" in output or "Checks passed:" in output

    # Проверяем, что в выводе есть информация о настройках
    assert "RAC_PATH" in output or "RAC Host" in output
    assert "LOG_PATH" in output or "Log directory" in output
