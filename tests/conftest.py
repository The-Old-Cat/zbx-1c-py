"""
Конфигурационный файл для pytest.
Используется для настройки тестовой среды.
"""

import os
import sys
from pathlib import Path

# Устанавливаем переменную окружения для обозначения тестовой среды
os.environ["PYTEST_CURRENT_TEST"] = "1"

# Добавляем путь к src для импорта модулей проекта
sys.path.insert(0, str(Path(__file__).parent / "src"))
