#!/usr/bin/env python3
"""
Скрипт для автоматической генерации конфигурационного файла userparameter_1c.conf
в зависимости от операционной системы и установленного Zabbix Agent.

Использует CLI команды проекта zbx-1c через:
- Entry points (рекомендуется): zbx-1c-discovery, zbx-1c-metrics
- Или через python -m zbx_1c
"""

import sys
import platform
from pathlib import Path


def get_python_executable():
    """Получить путь к исполняемому файлу Python."""
    return sys.executable


def get_project_paths():
    """Получить пути к проекту и скриптам."""
    script_dir = Path(__file__).parent.parent

    return {
        "project_root": script_dir,
        "venv_python": script_dir / ".venv" / "Scripts" / "python.exe" if platform.system().lower() == "windows" else script_dir / ".venv" / "bin" / "python"
    }


def generate_windows_config(python_path, use_entry_points=True, project_root=None):
    """Генерация конфигурации для Windows."""
    if use_entry_points:
        # Использование entry points из pyproject.toml (после pip install -e .)
        # Это предпочтительный способ - не зависит от путей к Python
        config_content = f'''# Custom parameters for 1C monitoring
#推荐使用 entry points (после установки: pip install -e .)
# Discovery: обнаружение кластеров (LLD)
UserParameter=zbx1cpy.clusters.discovery,zbx-1c-discovery

# Metrics: сбор метрик с параметром кластера ($1)
UserParameter=zbx1cpy.metrics[*],zbx-1c-metrics $1

# Тестовый параметр
UserParameter=zbx1cpy.test,zbx-1c-test

# Альтернативный вариант с явным указанием Python (если entry points не работают):
# UserParameter=zbx1cpy.clusters.discovery, cmd /c chcp 65001 >nul & set PYTHONIOENCODING=utf-8 & cd /d "{project_root}" && "{python_path}" -m zbx_1c discovery
# UserParameter=zbx1cpy.metrics[*], cmd /c chcp 65001 >nul & set PYTHONIOENCODING=utf-8 & cd /d "{project_root}" && "{python_path}" -m zbx_1c metrics $1
'''
    else:
        # Использование установленных команд (требует pip install -e .)
        config_content = '''# Custom parameters for 1C monitoring
# Discovery: обнаружение кластеров (LLD)
UserParameter=zbx1cpy.clusters.discovery, zbx-1c-discovery

# Metrics: сбор метрик с параметром кластера ($1)
UserParameter=zbx1cpy.metrics[*], zbx-1c-metrics $1

# Тестовый параметр
UserParameter=test.echo[*], cmd /c "echo test"
'''
    return config_content


def generate_linux_config(python_path, use_entry_points=True, project_root=None):
    """Генерация конфигурации для Linux."""
    if use_entry_points:
        # Использование entry points из pyproject.toml (после pip install -e .)
        # Это предпочтительный способ - не зависит от путей к Python
        config_content = '''# Custom parameters for 1C monitoring
# Recommended: use entry points (after installation: pip install -e .)
# Discovery: обнаружение кластеров (LLD)
UserParameter=zbx1cpy.clusters.discovery,zbx-1c-discovery

# Metrics: сбор метрик с параметром кластера ($1)
UserParameter=zbx1cpy.metrics[*],zbx-1c-metrics $1

# Тестовый параметр
UserParameter=zbx1cpy.test,zbx-1c-test

# Альтернативный вариант с явным указанием Python (если entry points не работают):
# UserParameter=zbx1cpy.clusters.discovery, LANG=C.UTF-8 PYTHONIOENCODING=utf-8 ''' + python_path + ''' -m zbx_1c discovery
# UserParameter=zbx1cpy.metrics[*], LANG=C.UTF-8 PYTHONIOENCODING=utf-8 ''' + python_path + ''' -m zbx_1c metrics $1
'''
    else:
        # Использование установленных команд (требует pip install -e .)
        config_content = '''# Custom parameters for 1C monitoring
# Discovery: обнаружение кластеров (LLD)
UserParameter=zbx1cpy.clusters.discovery, zbx-1c-discovery

# Metrics: сбор метрик с параметром кластера ($1)
UserParameter=zbx1cpy.metrics[*], zbx-1c-metrics $1

# Тестовый параметр
UserParameter=test.echo[*], echo test
'''
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
        possible_locations.extend([
            "C:/Program Files/Zabbix Agent/",
            "C:/Program Files (x86)/Zabbix Agent/",
            "C:/zabbix_agent/"
        ])
    else:
        # Типичные места установки Zabbix Agent на Linux
        possible_locations.extend([
            "/usr/sbin/zabbix_agent2",
            "/usr/sbin/zabbix_agent",
            "/usr/local/sbin/zabbix_agent2",
            "/usr/local/sbin/zabbix_agent",
            "/etc/zabbix/zabbix_agent2.conf",
            "/etc/zabbix/zabbix_agent.conf"
        ])
    
    # Проверяем наличие файлов
    for location in possible_locations:
        if Path(location).exists():
            if "agent2" in location.lower():
                return "agent2"
            elif "agent" in location.lower() and "agent2" not in location.lower():
                return "agent"
    
    # Попытка определить через командную строку
    try:
        import subprocess
        result = subprocess.run(["zabbix_agent2", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            return "agent2"
    except FileNotFoundError:
        pass
    
    try:
        import subprocess
        result = subprocess.run(["zabbix_agent", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            return "agent"
    except FileNotFoundError:
        pass
    
    return "unknown"


def generate_config(output_path=None, use_entry_points=True):
    """Основная функция генерации конфигурации."""
    os_type = platform.system().lower()
    paths = get_project_paths()

    # Определение используемого Python
    python_executable = get_python_executable()

    # Проверка наличия виртуального окружения
    venv_python = paths["venv_python"]
    if venv_python.exists():
        python_executable = str(venv_python.absolute())

    # Генерация конфигурации в зависимости от ОС
    if os_type == "windows":
        config_content = generate_windows_config(
            python_executable, 
            use_entry_points,
            str(paths["project_root"])
        )
    else:
        config_content = generate_linux_config(
            python_executable,
            use_entry_points,
            str(paths["project_root"])
        )

    # Определение версии Zabbix Agent
    agent_version = detect_zabbix_agent_version()

    # Добавление комментария о версии Zabbix Agent
    header = f"""# Configuration generated for {os_type.title()} OS
# Detected Zabbix Agent version: {agent_version}
# Generated on: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Project root: {paths["project_root"]}
# Mode: {'entry_points' if use_entry_points else 'module'}
"""

    full_config = header + config_content

    # Сохранение в файл
    if output_path is None:
        output_path = paths["project_root"] / "zabbix" / "userparameters" / "userparameter_1c.conf"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_config)

    print(f"Конфигурационный файл успешно создан: {output_path}")
    print(f"OS: {os_type.title()}")
    print(f"Zabbix Agent version: {agent_version}")
    print(f"Python executable: {python_executable}")
    print(f"Mode: {'entry_points (python -m zbx_1c)' if use_entry_points else 'installed commands (zbx-1c-*)'}")

    return output_path


if __name__ == "__main__":
    # Позволяем указать путь к выходному файлу как аргумент командной строки
    output_file = None
    use_entry_points = True
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--use-commands":
            use_entry_points = False
            if len(sys.argv) > 2:
                output_file = sys.argv[2]
        else:
            output_file = sys.argv[1]

    generate_config(output_file, use_entry_points)