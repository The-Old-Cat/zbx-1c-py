# API и CLI справочник

## CLI команды

### Запуск через модуль

```bash
python -m zbx_1c <command> [options]
```

### Основные команды

#### check-ras

Проверка доступности RAS сервиса.

```bash
python -m zbx_1c check-ras [--config .env]
```

**Пример вывода:**
```json
{
  "host": "127.0.0.1",
  "port": 1545,
  "available": true,
  "rac_path": "C:\\Program Files\\1cv8\\<version>\\bin\\rac.exe"
}
```

---

#### discovery

Обнаружение кластеров для Zabbix LLD (Low Level Discovery).

```bash
python -m zbx_1c discovery [--config .env]
```

**Пример вывода:**
```json
{
  "data": [
    {
      "{#CLUSTER.ID}": "<cluster-id>",
      "{#CLUSTER.NAME}": "Локальный кластер",
      "{#CLUSTER.HOST}": "<rac-host>",
      "{#CLUSTER.PORT}": 1541
    }
  ]
}
```

---

#### clusters

Список доступных кластеров.

```bash
python -m zbx_1c clusters [--config .env] [--json-output]
```

**Пример вывода (текст):**
```
📊 Доступные кластеры 1С:

1. Локальный кластер
   ID: <cluster-id>
   Host: <rac-host>:1541
   Status: unknown
```

**Пример вывода (JSON):**
```json
[
  {
    "id": "<cluster-id>",
    "name": "Локальный кластер",
    "host": "<rac-host>",
    "port": 1541,
    "status": "unknown"
  }
]
```

---

#### infobases

Получение информационных баз кластера.

```bash
python -m zbx_1c infobases <cluster_id> [--config .env]
```

**Пример:**
```bash
python -m zbx_1c infobases <cluster-id>
```

**Пример вывода:**
```json
[
  {
    "infobase": "<infobase-id>",
    "name": "<infobase-name>",
    "descr": "<infobase-description>"
  },
  ...
]
```

---

#### sessions

Получение сессий кластера.

```bash
python -m zbx_1c sessions <cluster_id> [--config .env]
```

**Пример вывода:**
```json
[
  {
    "session": "<session-id>",
    "session-id": 22,
    "infobase": "<infobase-id>",
    "user-name": "<username>",
    "host": "<client-host>",
    "app-id": "Designer",
    "started-at": "2026-02-12T16:08:30",
    "last-active-at": "2026-02-16T23:15:04",
    "hibernate": "no",
    ...
  }
]
```

---

#### jobs

Получение фоновых заданий кластера.

```bash
python -m zbx_1c jobs <cluster_id> [--config .env]
```

**Пример вывода:**
```json
[]
```

---

#### metrics

Получение метрик кластера (для Zabbix).

```bash
python -m zbx_1c metrics [cluster_id] [--config .env]
```

**С cluster_id:**
```json
{
  "cluster": {
    "id": "<cluster-id>",
    "name": "Локальный кластер",
    "status": "unknown"
  },
  "metrics": [
    {"key": "zbx1cpy.cluster.total_sessions", "value": 3},
    {"key": "zbx1cpy.cluster.active_sessions", "value": 3},
    {"key": "zbx1cpy.cluster.total_jobs", "value": 0},
    {"key": "zbx1cpy.cluster.active_jobs", "value": 0}
  ]
}
```

**Без cluster_id:** метрики для всех кластеров.

---

#### all

Получение всей информации о кластере.

```bash
python -m zbx_1c all <cluster_id> [--config .env]
```

**Пример вывода:**
```json
{
  "cluster": {...},
  "infobases": [...],
  "sessions": [...],
  "jobs": [...],
  "statistics": {
    "total_infobases": 29,
    "total_sessions": 3,
    "active_sessions": 3,
    "total_jobs": 0,
    "active_jobs": 0
  },
  "timestamp": "2026-02-16T23:15:00"
}
```

---

#### test

Тестирование подключения к 1С.

```bash
python -m zbx_1c test [--config .env]
```

**Пример вывода:**
```
🔧 Тестирование подключения к 1С...

📁 RAC path: C:\Program Files\1cv8\<version>\bin\rac.exe
   ✅ RAC executable found

🌐 RAS: 127.0.0.1:1545
   ✅ RAS is available

📊 Clusters found: 1
   - Локальный кластер (<cluster-id>)
     ✅ Metrics collected: 3 sessions, 3 active, 0 jobs

✅ Все проверки пройдены успешно
```

---

### CLI команды для сессий

Модуль `zbx_1c.monitoring.session.collector` предоставляет дополнительные команды:

#### list

Список всех сессий кластера.

```bash
python -m zbx_1c.monitoring.session.collector list <cluster_id> [--json-output]
```

---

#### active

Список активных сессий.

```bash
python -m zbx_1c.monitoring.session.collector active <cluster_id> [--threshold 5]
```

**Параметры:**
- `--threshold`, `-t`: Порог активности в минутах (по умолчанию: 5)

---

#### summary

Сводная информация о сессиях.

```bash
python -m zbx_1c.monitoring.session.collector summary <cluster_id>
```

**Пример вывода:**
```json
{
  "cluster_id": "<cluster-id>",
  "timestamp": "2026-02-16T23:15:12",
  "total_sessions": 3,
  "active_sessions": 3,
  "hibernated_sessions": 0,
  "unique_users": 2,
  "users": {
    "<user1>": 1,
    "<user2>": 2
  },
  "applications": {
    "Designer": 2,
    "1CV8C": 1
  }
}
```

---

#### count

Количество сессий (для Zabbix).

```bash
python -m zbx_1c.monitoring.session.collector count <cluster_id>
```

**Пример вывода:**
```json
{
  "cluster_id": "<cluster-id>",
  "total_sessions": 3,
  "active_sessions": 3
}
```

---

## REST API

### Запуск сервера

```bash
uvicorn zbx_1c.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Эндпоинты

#### GET /

Корневой эндпоинт.

**Ответ:**
```json
{
  "name": "Zabbix-1C Integration",
  "version": "0.1.0",
  "status": "running"
}
```

---

#### GET /health

Проверка здоровья приложения.

**Ответ:**
```json
{
  "status": "healthy",
  "rac_path": "C:\\Program Files\\1cv8\\<version>\\bin\\rac.exe",
  "rac_host": "127.0.0.1",
  "rac_port": 1545
}
```

---

#### GET /clusters/discovery

Обнаружение кластеров (LLD).

**Ответ:**
```json
{
  "data": [
    {
      "{#CLUSTER.ID}": "<cluster-id>",
      "{#CLUSTER.NAME}": "Локальный кластер",
      "{#CLUSTER.HOST}": "<rac-host>",
      "{#CLUSTER.PORT}": 1541
    }
  ]
}
```

---

#### GET /clusters

Список всех кластеров.

**Ответ:**
```json
[
  {
    "id": "<cluster-id>",
    "name": "Локальный кластер",
    "host": "<rac-host>",
    "port": 1541,
    "status": "unknown"
  }
]
```

---

#### GET /clusters/{cluster_id}/metrics

Метрики кластера.

**Ответ:**
```json
{
  "cluster": {
    "id": "<cluster-id>",
    "name": "Локальный кластер",
    "status": "unknown"
  },
  "metrics": {
    "total_sessions": 3,
    "active_sessions": 3,
    "total_jobs": 0,
    "active_jobs": 0
  }
}
```

---

#### GET /clusters/{cluster_id}/sessions

Сессии кластера.

**Параметры:**
- `cluster_id` (path): ID кластера
- `infobase` (query, опционально): Фильтр по ИБ

**Ответ:**
```json
[
  {
    "session": "...",
    "session-id": 1,
    "user-name": "...",
    ...
  }
]
```

---

#### GET /clusters/{cluster_id}/jobs

Фоновые задания кластера.

**Параметры:**
- `cluster_id` (path): ID кластера
- `infobase` (query, опционально): Фильтр по ИБ

---

#### GET /ras/status

Статус RAS сервиса.

**Ответ:**
```json
{
  "host": "127.0.0.1",
  "port": 1545,
  "available": true,
  "rac_path": "C:\\Program Files\\1cv8\\<version>\\bin\\rac.exe"
}
```

---

## Внутренние API модулей

### RACClient

```python
from zbx_1c.utils.rac_client import RACClient

rac = RACClient(settings)

# Выполнение команды
result = rac.execute([
    str(settings.rac_path),
    "cluster",
    "list",
    f"{settings.rac_host}:{settings.rac_port}",
])

# result: Dict с ключами:
# - returncode: int
# - stdout: str
# - stderr: str
```

---

### ClusterManager

```python
from zbx_1c.monitoring.cluster.manager import ClusterManager

manager = ClusterManager(settings)

# Обнаружение кластеров
clusters = manager.discover_clusters()  # List[Dict]

# Информационные базы
infobases = manager.get_infobases(cluster_id)  # List[Dict]

# Сессии
sessions = manager.get_sessions(cluster_id)  # List[Dict]

# Задания
jobs = manager.get_jobs(cluster_id)  # List[Dict]

# Метрики
metrics = manager.get_cluster_metrics(cluster_id)  # Dict
```

---

### SessionCollector

```python
from zbx_1c.monitoring.session.collector import SessionCollector

collector = SessionCollector(settings)

# Все сессии
sessions = collector.get_sessions(cluster_id)  # List[Dict]

# Активные сессии
active = collector.get_active_sessions(cluster_id, threshold_minutes=5)

# Сводка
summary = collector.get_sessions_summary(cluster_id)  # Dict
```

---

### Утилиты

```python
# Парсинг вывода rac
from zbx_1c.utils.converters import parse_rac_output

data = parse_rac_output(stdout_text)  # List[Dict]

# Форматирование для LLD
from zbx_1c.utils.converters import format_lld_data

lld = format_lld_data(clusters)  # {"data": [...]}

# Форматирование метрик
from zbx_1c.utils.converters import format_metrics

metrics = format_metrics(
    cluster_id="...",
    cluster_name="...",
    total_sessions=10,
    active_sessions=5,
    total_jobs=2,
    active_jobs=1,
)
```

---

## Коды возврата

| Код | Описание |
|-----|----------|
| 0 | Успех |
| 1 | Ошибка (RAS недоступен, кластер не найден, и т.д.) |

---

## Обработка ошибок

Все команды возвращают JSON даже при ошибке:

```json
{"error": "Cluster not found"}
```

Логи записываются в `logs/` директорию.
