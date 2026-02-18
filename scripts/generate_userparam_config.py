#!/usr/bin/env python3
"""
Скрипт для автоматической генерации конфигурационного файла userparameter_1c.conf
в зависимости от операционной системы и установленного Zabbix Agent.

Использует CLI команды проекта zbx-1c через:
- Entry points (рекомендуется): zbx-1c-discovery, zbx-1c-status, zbx-1c-metrics
- Или через python -m zbx_1c
"""

import sys
import platform
import shutil
from pathlib import Path


def get_python_executable():
    """Получить путь к исполняемому файлу Python."""
    return sys.executable


def get_project_paths():
    """Получить пути к проекту и скриптам."""
    script_dir = Path(__file__).parent.parent

    return {
        "project_root": script_dir,
        "venv_python": (
            script_dir / ".venv" / "Scripts" / "python.exe"
            if platform.system().lower() == "windows"
            else script_dir / ".venv" / "bin" / "python"
        ),
    }


def find_python_in_path():
    """Попытаться найти python в PATH."""
    python_cmd = "python.exe" if platform.system().lower() == "windows" else "python3"
    return shutil.which(python_cmd) or shutil.which("python")


def generate_windows_config(python_path, use_entry_points=True, project_root=None):
    """Генерация конфигурации для Windows."""
    # Используем cd /d для корректной кодировки (chcp 65001 не всегда работает)
    config_content = f"""# ===========================================
# UserParameter для мониторинга кластеров 1С
# ===========================================
# Mode: Python Module с полным путём
# ===========================================

# LLD Discovery: обнаружение кластеров
UserParameter=zbx1cpy.clusters.discovery,cd /d "{project_root}" && "{python_path}" -m zbx_1c discovery

# Статус кластера: available | unavailable | unknown
UserParameter=zbx1cpy.cluster.status[*],cd /d "{project_root}" && "{python_path}" -m zbx_1c status $1

# Метрики кластера (сессии, задания)
UserParameter=zbx1cpy.metrics[*],cd /d "{project_root}" && "{python_path}" -m zbx_1c metrics $1

# Метрики всех кластеров (для Master Item)
UserParameter=zbx1cpy.metrics.all,cd /d "{project_root}" && "{python_path}" -m zbx_1c metrics

# Проверка доступности RAS
UserParameter=zbx1cpy.ras.check,cd /d "{project_root}" && "{python_path}" -m zbx_1c check-ras

# Тестовый параметр
UserParameter=zbx1cpy.test,cd /d "{project_root}" && "{python_path}" -m zbx_1c test
"""
    return config_content


def generate_linux_config(python_path, use_entry_points=True, project_root=None):
    """Генерация конфигурации для Linux."""
    # Прямой вызов через python -m с полным путём
    # Не используем переменные среды - Zabbix их не поддерживает
    config_content = f"""# ===========================================
# UserParameter для мониторинга кластеров 1С
# ===========================================
# Mode: Python Module с полным путём
# ===========================================

# LLD Discovery: обнаружение кластеров
UserParameter=zbx1cpy.clusters.discovery,LANG=C.UTF-8 PYTHONIOENCODING=utf-8 "{python_path}" -m zbx_1c discovery

# Статус кластера: available | unavailable | unknown
UserParameter=zbx1cpy.cluster.status[*],LANG=C.UTF-8 PYTHONIOENCODING=utf-8 "{python_path}" -m zbx_1c status $1

# Метрики кластера (сессии, задания)
UserParameter=zbx1cpy.metrics[*],LANG=C.UTF-8 PYTHONIOENCODING=utf-8 "{python_path}" -m zbx_1c metrics $1

# Метрики всех кластеров (для Master Item)
UserParameter=zbx1cpy.metrics.all,LANG=C.UTF-8 PYTHONIOENCODING=utf-8 "{python_path}" -m zbx_1c metrics

# Проверка доступности RAS
UserParameter=zbx1cpy.ras.check,LANG=C.UTF-8 PYTHONIOENCODING=utf-8 "{python_path}" -m zbx_1c check-ras

# Тестовый параметр
UserParameter=zbx1cpy.test,LANG=C.UTF-8 PYTHONIOENCODING=utf-8 "{python_path}" -m zbx_1c test
"""
    return config_content


def detect_zabbix_agent_version():
    """
    Попытка определить версию Zabbix Agent.
    Возвращает 'agent2' если обнаружена вторая версия, 'agent' для первой версии или 'unknown'.
    """
    # Попытка определить по наличию типичных файлов конфигурации или бинарников
    possible_locations = []

    if platform.system().lower() == "windows":
        # Типичные места установки Zabbix Agent на Windows
        possible_locations.extend(
            [
                "C:/Program Files/Zabbix Agent/",
                "C:/Program Files (x86)/Zabbix Agent/",
                "C:/zabbix_agent/",
                "C:/Program Files/Zabbix Agent 2/",
                "C:/Program Files (x86)/Zabbix Agent 2/",
            ]
        )
    else:
        # Типичные места установки Zabbix Agent на Linux
        possible_locations.extend(
            [
                "/usr/sbin/zabbix_agent2",
                "/usr/sbin/zabbix_agent",
                "/usr/local/sbin/zabbix_agent2",
                "/usr/local/sbin/zabbix_agent",
                "/etc/zabbix/zabbix_agent2.conf",
                "/etc/zabbix/zabbix_agent.conf",
                "/etc/zabbix/zabbix_agent2.d/",
                "/etc/zabbix/zabbix_agentd.d/",
            ]
        )

    # Проверяем наличие файлов
    for location in possible_locations:
        path = Path(location)
        if path.exists():
            location_lower = location.lower()
            if "agent2" in location_lower or "agent 2" in location_lower:
                return "agent2"
            elif "agent" in location_lower:
                return "agent"

    # Попытка определить через командную строку
    try:
        import subprocess

        result = subprocess.run(
            ["zabbix_agent2", "--version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return "agent2"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    try:
        import subprocess

        result = subprocess.run(
            ["zabbix_agent", "--version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return "agent"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return "unknown"


def generate_config(output_path=None, use_entry_points=True, force_os=None):
    """
    Основная функция генерации конфигурации.

    Args:
        output_path: Путь для сохранения конфигурации (по умолчанию: zabbix/userparameters/)
        use_entry_points: Использовать entry points (True) или python -m (False)
        force_os: Принудительно указать ОС ('windows' или 'linux'), по умолчанию определяется автоматически
    """
    os_type = force_os if force_os else platform.system().lower()
    paths = get_project_paths()

    # Определение используемого Python
    python_executable = get_python_executable()

    # Проверка наличия виртуального окружения
    venv_python = paths["venv_python"]
    if venv_python.exists():
        python_executable = str(venv_python.absolute())
    else:
        # Пытаемся найти python в PATH
        python_in_path = find_python_in_path()
        if python_in_path:
            python_executable = python_in_path

    # Генерация конфигурации в зависимости от ОС
    if os_type == "windows":
        config_content = generate_windows_config(
            python_executable, use_entry_points, str(paths["project_root"])
        )
        config_comment = f"# Для Windows (Zabbix Agent 2)"
        install_path = "C:\\Program Files\\Zabbix Agent 2\\zabbix_agent2.d\\"
        restart_cmd = "Restart-Service zabbix-agent2"
    else:
        config_content = generate_linux_config(
            python_executable, use_entry_points, str(paths["project_root"])
        )
        config_comment = f"# Для Linux (Zabbix Agent / Agent 2)"
        install_path = "/etc/zabbix/zabbix_agent2.d/"
        restart_cmd = "sudo systemctl restart zabbix-agent2"

    # Определение версии Zabbix Agent
    agent_version = detect_zabbix_agent_version()

    # Добавление заголовка
    header = f"""# ===========================================
{config_comment}
# ===========================================
# Сгенерировано: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# OS: {os_type.title()}
# Zabbix Agent: {agent_version}
# Project root: {paths["project_root"]}
# Режим: {'Entry Points (zbx-1c-*)' if use_entry_points else 'Python Module (python -m zbx_1c)'}
# Python: {python_executable}
# ===========================================
# Установка:
#   Windows: Копировать в {install_path}
#   Linux:   Копировать в {install_path}
#
# Перезапуск агента:
#   {restart_cmd}
#
# Проверка:
#   zabbix_get -s <host> -k zbx1cpy.clusters.discovery
# ===========================================

"""

    full_config = header + config_content

    # Сохранение в файл
    if output_path is None:
        output_path = paths["project_root"] / "zabbix" / "userparameters" / "userparameter_1c.conf"
    else:
        output_path = Path(output_path)

    # Создаём директорию если не существует
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_config)

    # Безопасный вывод для Windows (избегаем проблем с кодировкой консоли)
    def safe_print(text):
        """Безопасный print для Windows консоли"""
        try:
            print(text)
        except UnicodeEncodeError:
            # Кодируем в ASCII с заменой невалидных символов
            print(text.encode("ascii", errors="replace").decode("ascii"))

    safe_print(f"[OK] Конфигурационный файл успешно создан: {output_path}")
    safe_print(f"OS: {os_type.title()}")
    safe_print(f"Zabbix Agent: {agent_version}")
    safe_print(f"Python: {python_executable}")
    safe_print(f"Mode: {'Entry Points' if use_entry_points else 'Python Module'}")
    safe_print(f"\nInstallation:")
    if os_type == "windows":
        safe_print(f"   Copy to: C:\\Program Files\\Zabbix Agent 2\\zabbix_agent2.d\\")
        safe_print(f"   Restart: Restart-Service zabbix-agent2")
    else:
        safe_print(f"   Copy to: /etc/zabbix/zabbix_agent2.d/")
        safe_print(f"   Restart: sudo systemctl restart zabbix-agent2")
    safe_print(f"\nCheck:")
    safe_print(f"   zabbix_get -s <host> -k zbx1cpy.clusters.discovery")
    safe_print(f"   zabbix_get -s <host> -k zbx1cpy.cluster.status[<cluster_id>]")

    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Генерация конфигурационного файла userparameter_1c.conf для Zabbix",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python scripts/generate_userparam_config.py
  python scripts/generate_userparam_config.py --use-module
  python scripts/generate_userparam_config.py -o /etc/zabbix/zabbix_agent2.d/userparameter_1c.conf
  python scripts/generate_userparam_config.py --force-os linux
        """,
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Путь для сохранения конфигурации (по умолчанию: zabbix/userparameters/userparameter_1c.conf)",
    )

    parser.add_argument(
        "--use-module",
        action="store_true",
        help="Использовать 'python -m zbx_1c' вместо entry points (не требует pip install -e .)",
    )

    parser.add_argument(
        "--force-os",
        type=str,
        choices=["windows", "linux"],
        default=None,
        help="Принудительно указать ОС (по умолчанию определяется автоматически)",
    )

    args = parser.parse_args()

    generate_config(
        output_path=args.output, use_entry_points=not args.use_module, force_os=args.force_os
    )
