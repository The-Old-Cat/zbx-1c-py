"""
Скрипт для тестирования команды session list
"""

import subprocess
import sys
from pathlib import Path

# Добавляем путь к родительскому каталогу в sys.path для импорта
sys.path.insert(0, str(Path(__file__).parent))

import sys
from pathlib import Path

# Добавляем путь к src для импорта модулей проекта
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from zbx_1c.core.config import settings
    from zbx_1c.utils.converters import decode_output
except ImportError:
    print("Не удалось импортировать настройки")
    sys.exit(1)

def test_session_list_command():
    """Тестируем команду session list"""
    
    print("=== Тест команды session list ===")
    print(f"Путь к rac: {settings.rac_path}")
    print(f"Адрес RAS: {settings.rac_host}:{settings.rac_port}")
    print(f"ID кластера: f93863ed-3fdb-4e01-a74c-e112c81b053b")
    
    # Пробуем разные форматы команды session list
    commands_to_test = [
        # Формат 1: --cluster как отдельный параметр
        [
            settings.rac_path,
            "session", 
            "list", 
            "--cluster",
            "f93863ed-3fdb-4e01-a74c-e112c81b053b",
            "--cluster-user=new_1cPin_KA",
            "--cluster-pwd=!Admin1c!159753",
            "localhost:1545"
        ],
        # Формат 2: --cluster как один параметр
        [
            settings.rac_path,
            "session", 
            "list", 
            "--cluster=f93863ed-3fdb-4e01-a74c-e112c81b053b",
            "--cluster-user=new_1cPin_KA",
            "--cluster-pwd=!Admin1c!159753",
            "localhost:1545"
        ],
        # Формат 3: без --cluster (может быть, для session list он не нужен?)
        [
            settings.rac_path,
            "session", 
            "list",
            "--cluster-user=new_1cPin_KA",
            "--cluster-pwd=!Admin1c!159753",
            "localhost:1545"
        ]
    ]
    
    for i, command in enumerate(commands_to_test, 1):
        print(f"\n--- Тест {i}: {' '.join(command)} ---")
        
        try:
            result = subprocess.run(command, capture_output=True, text=False, timeout=15)
            
            print(f"Код возврата: {result.returncode}")
            
            if result.stdout:
                print("STDOUT:")
                stdout_text = decode_output(result.stdout)
                print(stdout_text)
            
            if result.stderr:
                print("STDERR:")
                stderr_text = decode_output(result.stderr)
                print(stderr_text)
                
        except subprocess.TimeoutExpired:
            print("Таймаут выполнения команды")
        except Exception as e:
            print(f"Ошибка выполнения команды: {e}")

if __name__ == "__main__":
    test_session_list_command()