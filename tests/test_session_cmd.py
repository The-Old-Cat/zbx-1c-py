"""
Скрипт для тестирования команды session list

ПРИМЕЧАНИЕ: Этот файл содержит примеры тестов и не должен использоваться
в production. Для реального тестирования используйте pytest с fixtures.
"""

import subprocess
import sys
import os
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
    """Тестируем команду session list
    
    Примечание: Используйте переменные окружения для чувствительных данных:
    - TEST_CLUSTER_USER
    - TEST_CLUSTER_PWD  
    - TEST_CLUSTER_ID
    """
    
    # Получаем тестовые данные из переменных окружения или используем заглушки
    cluster_user = os.environ.get("TEST_CLUSTER_USER", "test_user")
    cluster_pwd = os.environ.get("TEST_CLUSTER_PWD", "test_password")
    cluster_id = os.environ.get("TEST_CLUSTER_ID", "00000000-0000-0000-0000-000000000000")

    print("=== Тест команды session list ===")
    print(f"Путь к rac: {settings.rac_path}")
    print(f"Адрес RAS: {settings.rac_host}:{settings.rac_port}")
    print(f"ID кластера: {cluster_id}")

    # Пробуем разные форматы команды session list
    commands_to_test = [
        # Формат 1: --cluster как отдельный параметр
        [
            settings.rac_path,
            "session",
            "list",
            "--cluster",
            cluster_id,
            "--cluster-user",
            cluster_user,
            "--cluster-pwd",
            cluster_pwd,
            "localhost:1545"
        ],
        # Формат 2: --cluster как один параметр
        [
            settings.rac_path,
            "session",
            "list",
            f"--cluster={cluster_id}",
            "--cluster-user",
            cluster_user,
            "--cluster-pwd",
            cluster_pwd,
            "localhost:1545"
        ],
        # Формат 3: без --cluster (может быть, для session list он не нужен?)
        [
            settings.rac_path,
            "session",
            "list",
            "--cluster-user",
            cluster_user,
            "--cluster-pwd",
            cluster_pwd,
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
