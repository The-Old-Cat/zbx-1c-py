# check_webinst.py
import os
import sys
from pathlib import Path

# Загружаем .env
env_file = Path("G:/Automation/zbx-1c-py/.env")
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# Проверяем переменную
webinst_path = os.getenv('WEBINST_PATH')
print(f"WEBINST_PATH из .env: {webinst_path}")

if webinst_path:
    path = Path(webinst_path)
    print(f"Путь: {path}")
    print(f"Существует: {path.exists()}")
    print(f"Абсолютный путь: {path.absolute()}")
    
    if path.exists():
        print("✓ webinst.exe найден!")
    else:
        print("✗ webinst.exe НЕ найден!")
        
        # Проверяем директорию
        print(f"\nПроверка директории: {path.parent}")
        print(f"Директория существует: {path.parent.exists()}")
        
        if path.parent.exists():
            print(f"\nФайлы в директории:")
            for file in path.parent.glob("*.exe"):
                print(f"  - {file.name}")
else:
    print("WEBINST_PATH не задан в .env")

# Проверяем стандартные пути
print("\nПроверка стандартных путей:")
standard_paths = [
    r"C:\Program Files\1cv8\8.3.27.2074\bin\webinst.exe",
    r"C:\Program Files\1cv8\webinst.exe",
    r"C:\Program Files (x86)\1cv8\webinst.exe",
]

for sp in standard_paths:
    p = Path(sp)
    print(f"  {sp}: {p.exists()}")