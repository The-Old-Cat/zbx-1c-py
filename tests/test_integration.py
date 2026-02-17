"""
Тест для проверки интеграции нового модуля путей с остальными модулями
"""
import sys
import os

# Добавляем путь к src, чтобы можно было импортировать модули
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_integration():
    print("Тестирование интеграции нового модуля путей с остальными модулями")
    print("="*60)
    
    # Тестируем импорт модуля utils, включающего новый модуль paths
    print("1. Тестирование импорта zbx_1c_py.utils...")
    from zbx_1c_py.utils import paths, helpers
    print("   + zbx_1c_py.utils успешно импортирован")
    
    # Тестируем, что функции из paths работают
    print("\n2. Тестирование функций из zbx_1c_py.utils.paths...")
    rac_path = paths.get_platform_specific_rac_path()
    print(f"   + get_platform_specific_rac_path() = {rac_path}")
    
    log_path = paths.get_log_file_path("./logs", "integration_test.log")
    print(f"   + get_log_file_path('./logs', 'integration_test.log') = {log_path}")
    
    # Тестируем импорт модуля config, который теперь использует функции из paths
    print("\n3. Тестирование импорта zbx_1c_py.config...")
    from zbx_1c_py import config
    settings = config.settings
    print(f"   + zbx_1c_py.config успешно импортирован")
    print(f"   + settings.rac_path = {settings.rac_path}")
    
    # Тестируем импорт модуля clusters, который теперь использует функции из paths
    print("\n4. Тестирование импорта zbx_1c_py.clusters...")
    from zbx_1c_py import clusters
    print("   + zbx_1c_py.clusters успешно импортирован")
    
    # Тестируем импорт модуля session, который теперь использует функции из paths
    print("\n5. Тестирование импорта zbx_1c_py.session...")
    from zbx_1c_py import session
    print("   + zbx_1c_py.session успешно импортирован")
    
    # Тестируем импорт модуля background_jobs, который теперь использует функции из paths
    print("\n6. Тестирование импорта zbx_1c_py.background_jobs...")
    from zbx_1c_py import background_jobs
    print("   + zbx_1c_py.background_jobs успешно импортирован")
    
    # Тестируем импорт модуля main, который теперь использует функции из paths
    print("\n7. Тестирование импорта zbx_1c_py.main...")
    from zbx_1c_py import main
    print("   + zbx_1c_py.main успешно импортирован")
    
    print("\n" + "="*60)
    print("+ Все тесты интеграции пройдены успешно!")
    print("+ Новый модуль путей корректно интегрирован с остальными модулями")

if __name__ == "__main__":
    test_integration()