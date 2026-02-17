# Отправка статуса кластера в Zabbix

## Обзор

Статус кластера определяется через TCP-подключение к рабочему серверу 1С и может принимать значения:
- `available` — кластер доступен
- `unavailable` — кластер недоступен
- `unknown` — не удалось определить статус

## Способ 1: Отправка через zabbix_sender (рекомендуется)

### Скрипт send_cluster_status.py

```bash
# Отправить статус конкретного кластера
python send_cluster_status.py <cluster_id>

# Отправить статусы всех кластеров
python send_cluster_status.py --all
```

### Переменные окружения

```bash
ZABBIX_SERVER=192.168.1.100      # Хост Zabbix сервера
ZABBIX_HOST=1C_Cluster           # Имя хоста в Zabbix
```

### Пример использования

```bash
# Windows
set ZABBIX_SERVER=192.168.1.100
set ZABBIX_HOST=1C_Cluster
python send_cluster_status.py f93863ed-3fdb-4e01-a74c-e112c81b053b

# Linux
export ZABBIX_SERVER=192.168.1.100
export ZABBIX_HOST=1C_Cluster
python send_cluster_status.py f93863ed-3fdb-4e01-a74c-e112c81b053b
```

### Планировщик заданий (Windows)

Создайте задачу в Планировщике заданий:
- **Триггер**: Каждые 1 минуту
- **Действие**: 
  ```
  python.exe C:\Automation\zbx-1c-py\send_cluster_status.py --all
  ```

### Cron (Linux)

```bash
# Отправка статусов каждую минуту
* * * * * /usr/bin/python3 /opt/zbx-1c-py/send_cluster_status.py --all
```

---

## Способ 2: Отправка через External Check

### Настройка Zabbix Server

В `zabbix_server.conf`:
```ini
ExternalScripts=/usr/lib/zabbix/externalscripts
```

### Скрипт для External Check

Создайте `/usr/lib/zabbix/externalscripts/zbx1cpy_cluster_status.py`:

```python
#!/usr/bin/env python3
import sys
import os
from pathlib import Path

sys.path.insert(0, '/opt/zbx-1c-py/src')

os.environ['RAC_PATH'] = '/opt/1C/v8.3/x86_64/rac'
os.environ['RAC_HOST'] = '127.0.0.1'
os.environ['RAC_PORT'] = '1545'

from zbx_1c.core.config import Settings
from zbx_1c.monitoring.cluster.discovery import discover_clusters

cluster_id = sys.argv[1] if len(sys.argv) > 1 else None
settings = Settings()
clusters = discover_clusters(settings)

for cluster in clusters:
    if str(cluster.id) == cluster_id:
        print(cluster.status)
        sys.exit(0)

print("unknown")
sys.exit(1)
```

```bash
chmod +x /usr/lib/zabbix/externalscripts/zbx1cpy_cluster_status.py
```

### Элемент данных в Zabbix

| Параметр | Значение |
|----------|----------|
| **Имя** | `Cluster status` |
| **Тип** | `External check` |
| **Ключ** | `zbx1cpy.cluster.status[f93863ed-3fdb-4e01-a74c-e112c81b053b]` |
| **Интервал опроса** | `1m` |
| **Тип информации** | `Текст` |

---

## Способ 3: Отправка вместе с метриками

### Скрипт zbx_1c_metrics.py

```bash
# Получить метрики со статусом в JSON
python zbx_1c_metrics.py <cluster_id>

# Отправить в Zabbix через trapper
python zbx_1c_metrics.py <cluster_id> | zabbix_sender -T -i -
```

### Пример вывода

```json
{
  "cluster": {
    "id": "f93863ed-3fdb-4e01-a74c-e112c81b053b",
    "name": "Локальный кластер",
    "status": "available"
  },
  "metrics": {
    "total_sessions": 8,
    "active_sessions": 8,
    "total_jobs": 0,
    "active_jobs": 0
  }
}
```

### UserParameter для Zabbix Agent

В `zabbix_agentd.conf`:

```ini
UserParameter=zbx1cpy.cluster.metrics[*],python /opt/zbx-1c-py/zbx_1c_metrics.py $1
```

### Зависимый элемент данных для статуса

| Параметр | Значение |
|----------|----------|
| **Тип** | `Зависимый элемент данных` |
| **Имя** | `Cluster status` |
| **Ключ** | `zbx1cpy.cluster.status[{#CLUSTER.ID}]` |
| **Мастер-элемент** | `zbx1cpy.cluster.metrics[{#CLUSTER.ID}]` |
| **JSONPath** | `$.cluster.status` |

---

## Настройка в Zabbix

### 1. LLD Правило обнаружения

| Параметр | Значение |
|----------|----------|
| **Имя** | `1C:Clusters discovery` |
| **Тип** | `External check` |
| **Ключ** | `python["C:/Automation/zbx-1c-py/src/zbx_1c/cli/commands.py", "discovery"]` |
| **Интервал** | `5m` |

### 2. Прототип элемента данных

| Параметр | Значение |
|----------|----------|
| **Имя** | `Cluster {#CLUSTER.NAME} status` |
| **Тип** | `Zabbix trapper` |
| **Ключ** | `zbx1cpy.cluster.status[{#CLUSTER.ID}]` |
| **Тип информации** | `Текст` |

### 3. Прототип триггера

| Параметр | Значение |
|----------|----------|
| **Имя** | `Cluster {#CLUSTER.NAME} is unavailable` |
| **Выражение** | `last(/Template/zbx1cpy.cluster.status[{#CLUSTER.ID}])="unavailable"` |
| **Серьёзность** | `Высокая` |

---

## Проверка

### Проверка LLD

```bash
python -m zbx_1c.cli.commands discovery
```

Вывод:
```json
{
  "data": [
    {
      "{#CLUSTER.ID}": "f93863ed-3fdb-4e01-a74c-e112c81b053b",
      "{#CLUSTER.NAME}": "Локальный кластер",
      "{#CLUSTER.HOST}": "srv-pinavto01",
      "{#CLUSTER.PORT}": 1541,
      "{#CLUSTER.STATUS}": "available"
    }
  ]
}
```

### Проверка отправки статуса

```bash
python send_cluster_status.py f93863ed-3fdb-4e01-a74c-e112c81b053b
```

Вывод:
```
[OK] Sent status 'available' for cluster f93863ed-3fdb-4e01-a74c-e112c81b053b
```

### Проверка метрик со статусом

```bash
python zbx_1c_metrics.py f93863ed-3fdb-4e01-a74c-e112c81b053b
```

Вывод:
```json
{
  "cluster": {
    "id": "f93863ed-3fdb-4e01-a74c-e112c81b053b",
    "name": "Локальный кластер",
    "status": "available"
  },
  "metrics": {
    "total_sessions": 8,
    "active_sessions": 8,
    "total_jobs": 0,
    "active_jobs": 0
  }
}
```
