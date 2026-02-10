#!/usr/bin/env python3
"""
Скрипт для проверки конфигурации приложения
"""

import sys
import os
from loguru import logger

# Добавляем путь к src в sys.path для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.zbx_1c_py.config import settings


def check_configuration():
    """
    Проверяет конфигурацию приложения и выводит текущие значения
    """
    logger.info("Проверка конфигурации приложения...")
    
    print("Текущая конфигурация:")
    print(f"  1C_CLUSTER_ID: {settings.cluster_id}")
    print(f"  RAC_PATH: {settings.rac_path}")
    print(f"  RAC_HOST: {settings.rac_host}")
    print(f"  RAC_PORT: {settings.rac_port}")
    print(f"  DEBUG: {settings.debug}")
    
    # Проверяем, что обязательные параметры установлены
    if not settings.cluster_id or settings.cluster_id == "your_cluster_id_here":
        print("\n[WARNING] 1C_CLUSTER_ID не установлен или содержит значение по умолчанию!")
        print("   Пожалуйста, установите правильное значение в переменной окружения или файле .env")
        return False
    
    print("\n[OK] Конфигурация в порядке!")
    return True


if __name__ == "__main__":
    success = check_configuration()
    sys.exit(0 if success else 1)