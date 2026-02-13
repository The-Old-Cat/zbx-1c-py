# Тестирование

## Обзор системы тестирования

Проект zbx-1c-py использует pytest в качестве фреймворка для тестирования. Структура тестов организована для обеспечения надежности и качества кода. Проект кроссплатформенный и тесты должны учитывать особенности работы на Windows, Linux и macOS.

## Запуск тестов

### Запуск всех тестов
```bash
uv run pytest
```

### Запуск тестов с детализацией
```bash
uv run pytest -v
```

### Запуск тестов с покрытием кода
```bash
uv run pytest --cov=src/zbx_1c_py
```

### Запуск конкретного тестового файла
```bash
uv run pytest tests/test_specific_module.py
```

### Альтернативные команды запуска (если возникают ошибки с захватом вывода)
На некоторых системах (особенно Windows) могут возникать ошибки с захватом вывода pytest. В таких случаях используйте:

```bash
# Запуск тестов с отключением предупреждений
uv run pytest --disable-warnings

# Запуск тестов с отключением захвата вывода
uv run pytest --capture=no

# Запуск конкретного тестового файла с отключением предупреждений
uv run pytest tests/test_session.py --disable-warnings
```

## Структура тестов

Тесты находятся в директории `tests/` и организованы следующим образом:

```
tests/
├── test_basic.py           # Базовые тесты
├── test_config.py          # Тесты конфигурации
├── test_clusters.py        # Тесты модуля clusters
├── test_session.py         # Тесты модуля session
├── test_session_active.py  # Тесты модуля session_active
├── test_background_jobs.py # Тесты модуля background_jobs
└── conftest.py            # Общие настройки для тестов
```

## Типы тестов

### 1. Модульные тесты
Тестируют отдельные функции и методы на уровне модулей:

- `test_clusters.py` - тестирование функций получения информации о кластерах
- `test_session.py` - тестирование функций получения информации о сессиях
- `test_session_active.py` - тестирование логики определения активных сессий
- `test_background_jobs.py` - тестирование логики определения активных фоновых заданий

### 2. Интеграционные тесты
Тестируют взаимодействие между несколькими модулями:

- `test_integration.py` - тестирование взаимодействия между модулями
- `test_main.py` - тестирование главного модуля и его интерфейсов

### 3. Тесты конфигурации
Тестируют правильность загрузки и валидации настроек:

- `test_config.py` - тестирование класса Settings и загрузки конфигурации

### 4. Кроссплатформенные тесты
Тестируют работу на разных операционных системах:

- Тесты обработки путей
- Тесты кодировки данных
- Тесты выполнения внешних процессов

## Написание тестов

### Пример модульного теста
```python
import pytest
from src.zbx_1c_py.session_active import is_session_active


def test_active_session_with_recent_activity():
    """Тест активной сессии с недавней активностью"""
    session = {
        "hibernate": "no",
        "last-active-at": "2026-02-11T10:06:04",
        "calls-last-5min": "10",
        "bytes-last-5min": "1000"
    }
    
    assert is_session_active(session) is True


def test_inactive_session_hibernated():
    """Тест неактивной сессии в спящем режиме"""
    session = {
        "hibernate": "yes",
        "last-active-at": "2026-02-11T10:06:04",
        "calls-last-5min": "10"
    }
    
    assert is_session_active(session) is False
```

### Использование фикстур
Для подготовки тестовых данных рекомендуется использовать фикстуры pytest:

```python
import pytest


@pytest.fixture
def sample_session():
    """Фикстура для тестовой сессии"""
    return {
        "hibernate": "no",
        "last-active-at": "2026-02-11T10:06:04",
        "calls-last-5min": "5",
        "bytes-last-5min": "500",
        "user-name": "test_user",
        "app-id": "1CV8C"
    }


def test_session_processing(sample_session):
    """Тест обработки сессии с использованием фикстуры"""
    # Тестовая логика
    assert sample_session["hibernate"] == "no"
```

## Кроссплатформенные аспекты тестирования

### Тестирование обработки путей
```python
import os
import pytest
from pathlib import Path


@pytest.mark.parametrize("os_name,expected_separator", [
    ("windows", "\\"),
    ("linux", "/"),
    ("macos", "/"),
])
def test_path_separators(os_name, expected_separator):
    """Тест разделителей пути для разных ОС"""
    # В реальном тесте можно использовать mock для определения ОС
    if os_name == "windows":
        assert expected_separator == "\\"
    else:
        assert expected_separator == "/"
```

### Тестирование кодировки данных
```python
def test_decode_output_cp866():
    """Тест декодирования данных в кодировке CP866 (Windows)"""
    # Тестирование с mock-данными в CP866
    from src.zbx_1c_py.utils.helpers import decode_output
    test_data = "тест".encode('cp866')  # Только для Windows
    result = decode_output(test_data)
    assert result == "тест"


def test_decode_output_utf8():
    """Тест декодирования данных в кодировке UTF-8 (Linux/macOS)"""
    from src.zbx_1c_py.utils.helpers import decode_output
    test_data = "тест".encode('utf-8')
    result = decode_output(test_data)
    assert result == "тест"
```

## Проверка качества кода

### Проверка уязвимостей
```bash
uv run pip-audit
```

### Статический анализ
Проект может использовать дополнительные инструменты статического анализа:

```bash
# Пример для mypy (если настроен)
uv run mypy src/

# Пример для flake8 (если настроен)
uv run flake8 src/
```

## Тестирование в CI/CD

### Пример конфигурации GitHub Actions с кроссплатформенными тестами
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: [3.8, 3.9, 3.10, 3.11]

    steps:
    - uses: actions/checkout@v3
    
    - name: Install uv
      run: |
        curl -LsSf https://astral.sh/uv/install.sh | sh
        source $HOME/.cargo/env
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: uv sync
    
    - name: Run tests
      run: uv run pytest -v
    
    - name: Run security audit
      run: uv run pip-audit
```

## Тестирование изолированной среды выполнения

### Запуск тестов в изолированной среде
Все тесты должны запускаться через uv для обеспечения изоляции от системного Python:

```bash
# Запуск тестов (гарантирует изоляцию от системного Python)
uv run pytest

# Запуск тестов с покрытием (полностью изолированный)
uv run pytest --cov=src/zbx_1c_py
```

### Проверка изоляции среды
Для проверки корректности изоляции рекомендуется добавлять тесты, проверяющие зависимости:

```python
def test_environment_isolation():
    """Тест изоляции среды выполнения от системного Python"""
    import sys
    import os
    
    # Проверяем, что мы используем изолированное окружение uv
    assert hasattr(sys, '_base_executable') or 'uv' in sys.executable.lower() or \
           os.environ.get('VIRTUAL_ENV') is not None
```

## Тестирование производительности

Для тестирования производительности можно использовать встроенные возможности pytest:

```bash
# Запуск тестов с измерением времени
uv run pytest --durations=10
```

## Mock-объекты и тестирование внешних зависимостей

Для тестирования функций, взаимодействующих с внешними системами (например, rac), рекомендуется использовать mock-объекты:

```python
from unittest.mock import patch, MagicMock


@patch('subprocess.run')
def test_fetch_raw_sessions_success(mock_subprocess):
    """Тест успешного получения сессий"""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = b'test output'
    mock_subprocess.return_value = mock_result
    
    # Тестирование функции
    from src.zbx_1c_py.session import fetch_raw_sessions
    result = fetch_raw_sessions("test-cluster-id")
    
    assert result == []  # Зависит от реализации parse_rac_output
```

## Покрытие кода

Для анализа покрытия кода тестами:

```bash
# Установка coverage инструментов
uv run pip install pytest-cov

# Запуск тестов с анализом покрытия
uv run pytest --cov=src/zbx_1c_py --cov-report=html --cov-report=term
```

## Рекомендации по тестированию

1. **Покрывайте критические пути**: Уделяйте особое внимание логике определения активных сессий и фоновых заданий

2. **Тестируйте граничные условия**: Проверяйте поведение при пустых данных, некорректных форматах дат и т.д.

3. **Изолируйте тесты**: Используйте фикстуры и mock-объекты для изоляции тестируемого кода

4. **Тестируйте обработку ошибок**: Проверяйте, как система реагирует на ошибки взаимодействия с RAS

5. **Поддерживайте актуальность тестов**: Обновляйте тесты при изменении логики

6. **Учитывайте кроссплатформенность**: Проверяйте работу на разных операционных системах

## Устранение неполадок в тестах

### Если тесты падают
1. Проверьте зависимости: `uv sync`
2. Убедитесь, что используете правильную версию Python
3. Проверьте настройки конфигурации
4. Изучите логи ошибок
5. Убедитесь, что тесты не зависят от специфики операционной системы

### Если возникают ошибки с pytest (I/O operation on closed file)
Это известная проблема с захватом вывода в некоторых версиях pytest на Windows. Используйте следующие команды:

```bash
# Запуск всех тестов с отключением захвата вывода
uv run pytest --disable-warnings

# Запуск конкретного тестового файла
uv run pytest tests/test_session.py --disable-warnings

# Запуск тестов с отключением захвата
uv run pytest --capture=no

# Запуск тестов с отключением плагинов, которые могут вызывать проблемы
uv run pytest -p no:warnings
```

### Если тесты зависают
1. Проверьте таймауты в тестах
2. Убедитесь, что mock-объекты корректно настроены
3. Проверьте, не происходит ли обращение к внешним ресурсам

### Известные проблемы с тестами
Некоторые тесты могут не проходить по следующим причинам:

1. **Проблемы с обработкой пустых строк в parse_rac_output**
   - Функция может возвращать неожиданные результаты при обработке текста с пустыми строками
   - Рекомендуется проверить логику разбора многострочного текста с разделителями

2. **Проблемы с декодированием в decode_output**
   - Возможны проблемы с кодировками на разных платформах (CP866 на Windows, UTF-8 на Linux/macOS)
   - Тесты могут не проходить из-за различий в обработке специальных символов
   - Убедитесь, что функция корректно обрабатывает разные кодировки данных

3. **Проблемы с логикой определения активности сессий**
   - Функции определения активности сессий могут возвращать неожиданные результаты в граничных случаях
   - Особое внимание уделите тестам с отсутствующими полями, будущими датами и нулевыми порогами
   - Проверьте логику обработки сессий без полей `calls-last-5min` и `bytes-last-5min`

4. **Проблемы с неправильными импортами в тестах**
   - Убедитесь, что пути импортов в тестах соответствуют реальному расположению файлов
   - Например, используйте `from zbx_1c_py.utils.check_config import ...` вместо `from scripts.check_config import ...`
   - Проверьте, что все импортируемые модули существуют и доступны