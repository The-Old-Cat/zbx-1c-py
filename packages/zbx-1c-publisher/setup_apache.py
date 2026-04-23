#!/usr/bin/env python
"""Скрипт для развёртывания Apache."""

import sys
import os
import platform
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent / "src"))

from zbx_1c_publisher.core.apache_deploy import (
    deploy_apache,
    check_apache_status,
    get_apache_version,
    restart_apache_service,
    stop_apache_service,
    start_apache_service,
    get_install_path,
    get_onec_conf_path,
    create_1c_conf_template,
    ensure_1c_conf_included,
)


def check_admin() -> bool:
    """Проверка прав администратора."""
    system = platform.system().lower()

    if system == "windows":
        try:
            import ctypes

            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    elif system == "linux":
        try:
            return os.geteuid() == 0
        except AttributeError:
            try:
                return os.getuid() == 0
            except AttributeError:
                import subprocess

                result = subprocess.run(["id", "-u"], capture_output=True, text=True)
                return result.stdout.strip() == "0"
        except Exception:
            return False
    return True  # Для macOS и других ОС


def main():
    print("=" * 60)
    print("УПРАВЛЕНИЕ APACHE ДЛЯ 1С")
    print("=" * 60)

    # Проверка прав
    if not check_admin():
        print("\n⚠ ВНИМАНИЕ: Скрипт запущен без прав администратора!")
        print("Некоторые операции могут быть недоступны.")
        print("Для полной функциональности запустите от имени администратора.\n")

    print("\nВыберите действие:")
    print("  1 - Развернуть/установить Apache")
    print("  2 - Проверить статус Apache")
    print("  3 - Перезапустить Apache")
    print("  4 - Остановить Apache")
    print("  5 - Запустить Apache")
    print("  6 - Показать версию Apache")
    print("  7 - Создать конфигурацию для 1С")
    print("  0 - Выход")

    choice = input("\nВаш выбор: ").strip()

    if choice == "1":
        print("\nРазвёртывание Apache...")
        publish_root = Path("C:/Apache24/htdocs")
        success, msg = deploy_apache(publish_root)
        if success:
            print(f"✓ {msg}")
        else:
            print(f"✗ Ошибка: {msg}")

    elif choice == "2":
        print("\nПроверка статуса Apache...")
        success, msg = check_apache_status()
        if success:
            print(f"✓ {msg}")
        else:
            print(f"✗ {msg}")

    elif choice == "3":
        print("\nПерезапуск Apache...")
        success, msg = restart_apache_service()
        if success:
            print(f"✓ {msg}")
        else:
            print(f"✗ Ошибка: {msg}")

    elif choice == "4":
        print("\nОстановка Apache...")
        success, msg = stop_apache_service()
        if success:
            print(f"✓ {msg}")
        else:
            print(f"✗ Ошибка: {msg}")

    elif choice == "5":
        print("\nЗапуск Apache...")
        success, msg = start_apache_service()
        if success:
            print(f"✓ {msg}")
        else:
            print(f"✗ Ошибка: {msg}")

    elif choice == "6":
        print("\nВерсия Apache...")
        version = get_apache_version()
        print(f"  {version}")

    elif choice == "7":
        print("\nСоздание конфигурации для 1С...")
        publish_root = Path("C:/Apache24/htdocs")
        conf_path = create_1c_conf_template(publish_root)
        print(f"✓ Создан файл: {conf_path}")

        # Подключаем в основной конфиг
        apache_conf = get_install_path() / "conf" / "httpd.conf"
        if apache_conf.exists():
            ensure_1c_conf_included(apache_conf)
            print(f"✓ Конфиг подключён к {apache_conf}")

    else:
        print("Завершение работы.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрерывание пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        input("\nНажмите Enter для выхода...")
