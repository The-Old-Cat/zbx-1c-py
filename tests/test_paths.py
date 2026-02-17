"""
Тестовый файл для проверки работы нового модуля paths.py
"""
import sys
import os
# Добавляем путь к src, чтобы можно было импортировать модули
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.zbx_1c.utils.fs import get_platform_specific_rac_path, get_log_file_path, normalize_path, join_paths

def test_paths():
    print("Тестирование нового модуля paths.py")
    print("="*50)
    
    # Тестируем получение пути к rac.exe
    print("1. Тестирование get_platform_specific_rac_path():")
    rac_path = get_platform_specific_rac_path()
    print(f"   Путь к rac.exe: {rac_path}")
    
    # Тестируем получение пути к лог-файлу
    print("\n2. Тестирование get_log_file_path():")
    log_path = get_log_file_path("./logs", "test.log")
    print(f"   Путь к лог-файлу: {log_path}")
    
    # Тестируем нормализацию пути
    print("\n3. Тестирование normalize_path():")
    normalized = normalize_path("../some/relative/path")
    print(f"   Нормализованный путь: {normalized}")
    
    # Тестируем объединение путей
    print("\n4. Тестирование join_paths():")
    joined = join_paths("folder1", "folder2", "file.txt")
    print(f"   Объединенный путь: {joined}")
    
    print("\n" + "="*50)
    print("Тестирование завершено успешно!")

if __name__ == "__main__":
    test_paths()