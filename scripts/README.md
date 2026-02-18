# Скрипты проекта

В этой директории находятся вспомогательные скрипты для проекта zbx-1c-py.

## Доступные скрипты

### generate_userparam (CLI команда)

Скрипт для автоматической генерации конфигурационного файла `userparameter_1c.conf` для Zabbix Agent.

**Функциональность:**
- Определяет операционную систему (Windows/Linux)
- Определяет версию Zabbix Agent (agent/agent2)
- Использует виртуальное окружение проекта (если существует)
- Генерирует конфигурацию для CLI команд проекта

**Запуск:**
```bash
# Через entry point (после установки)
zbx-1c-generate-userparam

# С указанием выходного файла
zbx-1c-generate-userparam -o /etc/zabbix/zabbix_agent2.d/userparameter_1c.conf

# Принудительно для Linux
zbx-1c-generate-userparam --force-os linux

# Через uv (для разработки)
uv run zbx-1c-generate-userparam
```

**Режимы работы:**
- По умолчанию использует `python -m zbx_1c <command>` с полным путём к Python
- Генерирует конфигурацию для Windows или Linux автоматически

**Пример генерируемой конфигурации (Windows):**
```conf
UserParameter=zbx1cpy.clusters.discovery,cd /d "G:\Automation\zbx-1c-py" && "G:\Automation\zbx-1c-py\.venv\Scripts\python.exe" -m zbx_1c discovery
UserParameter=zbx1cpy.cluster.status[*],cd /d "G:\Automation\zbx-1c-py" && "G:\Automation\zbx-1c-py\.venv\Scripts\python.exe" -m zbx_1c status $1
UserParameter=zbx1cpy.metrics[*],cd /d "G:\Automation\zbx-1c-py" && "G:\Automation\zbx-1c-py\.venv\Scripts\python.exe" -m zbx_1c metrics $1
```

**Пример генерируемой конфигурации (Linux):**
```conf
UserParameter=zbx1cpy.clusters.discovery,LANG=C.UTF-8 PYTHONIOENCODING=utf-8 "/usr/bin/python3" -m zbx_1c discovery
UserParameter=zbx1cpy.cluster.status[*],LANG=C.UTF-8 PYTHONIOENCODING=utf-8 "/usr/bin/python3" -m zbx_1c status $1
UserParameter=zbx1cpy.metrics[*],LANG=C.UTF-8 PYTHONIOENCODING=utf-8 "/usr/bin/python3" -m zbx_1c metrics $1
```

---

## Проверка конфигурации

Для проверки конфигурации используйте CLI команду:

```bash
# Через entry point
zbx-1c-check-config

# Через основную команду
zbx-1c check-config

# Через uv
uv run zbx-1c check-config
```

---

## Директории

### dev/
Скрипты для разработки и отладки.

### deploy/
Скрипты для развёртывания проекта.
