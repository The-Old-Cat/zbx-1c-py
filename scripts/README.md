# Скрипты проекта

В этой директории находятся вспомогательные скрипты для проекта zbx-1c-py.

## Доступные скрипты

### generate_userparam_config.py
Скрипт для автоматической генерации конфигурационного файла `userparameter_1c.conf` для Zabbix Agent.

**Функциональность:**
- Определяет операционную систему (Windows/Linux)
- Определяет версию Zabbix Agent (agent/agent2)
- Использует виртуальное окружение проекта (если существует)
- Генерирует конфигурацию для CLI команд проекта

**Запуск:**
```bash
# Генерация в директорию по умолчанию (zabbix/userparameter_1c.conf)
python scripts/generate_userparam_config.py

# Генерация в указанный файл
python scripts/generate_userparam_config.py /path/to/userparameter.conf

# Использование установленных команд вместо python -m zbx_1c
python scripts/generate_userparam_config.py --use-commands
```

**Режимы работы:**
- `entry_points` (по умолчанию): использует `python -m zbx_1c <command>`
- `installed commands`: использует установленные команды `zbx-1c-discovery`, `zbx-1c-metrics` (требует `pip install -e .`)

**Пример генерируемой конфигурации:**
```conf
UserParameter=zbx1cpy.clusters.discovery, "python.exe" -m zbx_1c discovery
UserParameter=zbx1cpy.metrics[*], "python.exe" -m zbx_1c metrics $1
```

---

### check_config.py
Скрипт для проверки корректности настройки конфигурации проекта zbx-1c-py.

**Функциональность:**
- Проверяет наличие и доступность исполняемого файла rac
- Проверяет правильность настроек подключения к RAS
- Проверяет доступность директории для логов
- Проверяет правильность формата настроек
- Тестирует подключение к RAS

**Запуск:**
```bash
# Рекомендуемый способ (через entry point)
uv run check-config

# Альтернативный способ
python scripts/check_config.py
```

---

## Директории

### dev/
Скрипты для разработки и отладки.

### deploy/
Скрипты для развёртывания проекта.