"""
Тест для проверки команды rac напрямую
"""
import subprocess
import sys
import os
from pathlib import Path

# Добавляем путь к src, чтобы можно было импортировать модули
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.zbx_1c.core.config import settings
from src.zbx_1c.utils.converters import decode_output, parse_rac_output

def test_direct_command():
    print("Тестирование прямой команды rac.exe")
    print("="*60)
    
    cluster_id = "f93863ed-3fdb-4e01-a74c-e112c81b053b"
    ras_address = f"{settings.rac_host}:{settings.rac_port}"
    
    print(f"Команда будет выполнена для:")
    print(f"  Cluster ID: {cluster_id}")
    print(f"  RAS Address: {ras_address}")
    print(f"  User: {settings.user_name}")
    print()
    
    # Команда, аналогичная той, что используется в модуле
    command = [
        settings.rac_path,
        "infobase", 
        "summary", 
        "list", 
        f"--cluster={cluster_id}"
    ]

    # Добавляем авторизацию, если параметры заданы в конфиге
    if settings.user_name:
        command.extend(["--cluster-user", settings.user_name])
    if settings.user_pass:
        command.extend(["--cluster-pwd", settings.user_pass])

    # Добавляем адрес RAS в конец команды
    command.append(ras_address)

    print(f"Выполняемая команда: {' '.join(command)}")
    print()
    
    try:
        result = subprocess.run(command, capture_output=True, check=False, text=False, timeout=15)

        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            print("STDOUT (raw length):", len(result.stdout))
            decoded_text = decode_output(result.stdout)
            print("STDOUT (decoded):")
            print(repr(decoded_text))  # Показываем в виде repr для видимости всех символов
            print()
            print("STDOUT (formatted):")
            print(decoded_text)
            print()
            
            # Парсим вывод
            infobases = parse_rac_output(decoded_text)
            print(f"Парсер нашел {len(infobases)} информационных баз:")
            for i, ib in enumerate(infobases):
                name = ib.get('name', 'N/A')
                infobase_id = ib.get('infobase', 'N/A')
                print(f"  [{i+1}] {name} (ID: {infobase_id})")
        else:
            print("STDOUT пустой")
        
        if result.stderr:
            print("STDERR:")
            stderr_text = decode_output(result.stderr)
            print(stderr_text)
        else:
            print("STDERR пустой")
            
    except Exception as e:
        print(f"Ошибка при выполнении команды: {e}")

if __name__ == "__main__":
    test_direct_command()