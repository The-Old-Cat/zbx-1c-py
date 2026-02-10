import os
import sys
import tempfile
import json
from unittest.mock import patch

# Добавляем путь к src в sys.path для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from zbx_1c_py.main import main
from zbx_1c_py.config import settings


def test_main_without_cluster_id(capsys):
    """Тест основной функции без заданного cluster_id"""
    # Сохраняем оригинальное значение
    original_cluster_id = settings.cluster_id
    
    try:
        # Устанавливаем пустой cluster_id
        settings.cluster_id = ""
        
        # Вызываем главную функцию
        main()
        
        # Проверяем вывод
        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())
        
        # Ожидаем пустой массив
        assert output == []
        
    finally:
        # Восстанавливаем оригинальное значение
        settings.cluster_id = original_cluster_id


def test_main_with_cluster_id():
    """Тест основной функции с заданным cluster_id"""
    # Проверяем, что cluster_id задан
    assert settings.cluster_id != ""