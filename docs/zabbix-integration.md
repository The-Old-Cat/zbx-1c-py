# Интеграция с Zabbix

## Обзор

Проект zbx-1c-py обеспечивает полную интеграцию 1С:Предприятия с системой мониторинга Zabbix через:

1. **UserParameter** - вызов Python скриптов из Zabbix Agent
2. **LLD (Low Level Discovery)** - автоматическое обнаружение кластеров
3. **Шаблоны** - готовые элементы данных, триггеры, графики
4. **REST API** - для интеграции через Zabbix HTTP checks

---

## Архитектура интеграции

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Zabbix    │ ───► │ Zabbix Agent │ ───► │  zbx-1c-py  │
│   Server    │      │  (UserParam) │      │   (Python)  │
└─────────────┘      └──────────────┘      └─────────────┘
                           │                      │
                           │                      ▼
                           │              ┌───────────────┐
                           │              │  RAC/rac.exe  │
                           │              │ 1С:Предприятие│
                           │              └───────────────┘
                           ▼
                    ┌──────────────┐
                    │1С:Предприятие│
                    │   RAS 1545   │
                    └──────────────┘
```

---

## Установка и настройка

### Шаг 1: Установка Python и зависимостей

```bash
# Установка uv (рекомендуется)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Установка проекта
cd .\Automation\zbx-1c-py
uv sync
```

### Шаг 2: Настройка .env

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
RAC_PATH=C:/Program Files/1cv8/х.х.х.х/bin/rac.exe
RAC_HOST=127.0.0.1
RAC_PORT=1545
USER_NAME=admin
USER_PASS=password
LOG_PATH=G:/Automation/zbx-1c-py/logs
DEBUG=False
```

### Шаг 3: Генерация UserParameter

```bash
# Через entry point (после установки)
zbx-1c-generate-userparam

# Или через uv (для разработки)
uv run zbx-1c-generate-userparam
```

Скрипт создаст файл `zabbix/userparameters/userparameter_1c.conf`.

### Шаг 4: Копирование конфигурации в Zabbix Agent

**Windows:**
```
C:\Program Files\Zabbix Agent\zabbix_agentd.conf.d\userparameter_1c.conf
```

**Linux:**
```
/etc/zabbix/zabbix_agentd.d/userparameter_1c.conf
```

### Шаг 5: Перезапуск Zabbix Agent

**Windows:**
```powershell
net stop "Zabbix Agent"
net start "Zabbix Agent"
```

**Linux:**
```bash
systemctl restart zabbix-agent
```

### Шаг 6: Импорт шаблона в Zabbix

1. В веб-интерфейсе Zabbix перейдите в **Data collection → Templates**
2. Нажмите **Import**
3. Выберите файл `zabbix/templates/template.xml`
4. Нажмите **Import**

### Шаг 7: Привязка шаблона к хосту

1. Перейдите в **Data collection → Hosts**
2. Выберите или создайте хост
3. На вкладке **Templates** добавьте шаблон **Template 1C Cluster Monitoring**
4. Настройте макросы (при необходимости):
   - `{$RAC_HOST}` - хост RAS (по умолчанию: 127.0.0.1)
   - `{$RAC_PORT}` - порт RAS (по умолчанию: 1545)
   - `{$CLUSTER_ID}` - ID кластера (для LLD не требуется)

---

## UserParameter

### Сгенерированный файл (Windows пример)

```conf
# Configuration generated for Windows OS
# Detected Zabbix Agent version: agent
# Generated on: 2026-02-16 23:34:30
# Project root: g:\Automation\zbx-1c-py
# Mode: entry_points

# Discovery: обнаружение кластеров (LLD)
UserParameter=zbx1cpy.clusters.discovery, cmd /c chcp 65001 >nul & set PYTHONIOENCODING=utf-8 & "g:\Automation\zbx-1c-py\.venv\Scripts\python.exe" -m zbx_1c discovery

# Metrics: сбор метрик с параметром кластера
UserParameter=zbx1cpy.metrics[*], cmd /c chcp 65001 >nul & set PYTHONIOENCODING=utf-8 & "g:\Automation\zbx-1c-py\.venv\Scripts\python.exe" -m zbx_1c metrics $1

# Test: тестовый параметр
UserParameter=test.echo[*], "g:\Automation\zbx-1c-py\.venv\Scripts\python.exe" -c "import sys; print(sys.executable)"
```

### Сгенерированный файл (Linux пример)

```conf
# Configuration generated for Linux OS
# Detected Zabbix Agent version: agent2
# Generated on: 2026-02-16 23:34:30
# Project root: /opt/zbx-1c-py
# Mode: entry_points

# Discovery: обнаружение кластеров (LLD)
UserParameter=zbx1cpy.clusters.discovery, PYTHONIOENCODING=utf-8 /opt/zbx-1c-py/.venv/bin/python -m zbx_1c discovery

# Metrics: сбор метрик с параметром кластера
UserParameter=zbx1cpy.metrics[*], PYTHONIOENCODING=utf-8 /opt/zbx-1c-py/.venv/bin/python -m zbx_1c metrics $1

# Test: тестовый параметр
UserParameter=test.echo[*], /opt/zbx-1c-py/.venv/bin/python -c "import sys; print(sys.executable)"
```

**Примечание:** На Linux пути не содержат кавычек, если не содержат пробелов.

---

## Элементы данных (Items)

### Discovery

| Ключ | Тип | Описание |
|------|-----|----------|
| `zbx1cpy.clusters.discovery` | Zabbix agent | Обнаружение кластеров 1С (LLD) |

### Метрики кластера

| Ключ | Тип данных | Единицы | Описание |
|------|------------|---------|----------|
| `zbx1cpy.metrics[{#CLUSTER.ID}]` | Numeric | | Метрики кластера (через LLD) |
| `zbx1cpy.cluster.total_sessions` | Numeric | | Всего сессий |
| `zbx1cpy.cluster.active_sessions` | Numeric | | Активных сессий |
| `zbx1cpy.cluster.total_jobs` | Numeric | | Всего заданий |
| `zbx1cpy.cluster.active_jobs` | Numeric | | Активных заданий |

### Сессии

| Ключ | Тип данных | Описание |
|------|------------|----------|
| `1c.sessions.count[{#CLUSTER.ID}]` | Numeric | Количество сессий |

---

## Low Level Discovery (LLD)

### Правило обнаружения

- **Name**: 1C Cluster Discovery
- **Type**: Zabbix agent
- **Key**: `zbx1cpy.clusters.discovery`
- **Update interval**: 5m

### Макросы LLD

| Макрос | Описание |
|--------|----------|
| `{#CLUSTER.ID}` | UUID кластера |
| `{#CLUSTER.NAME}` | Имя кластера |
| `{#CLUSTER.HOST}` | Хост кластера |
| `{#CLUSTER.PORT}` | Порт кластера |

### Прототипы элементов данных

Создаются автоматически для каждого обнаруженного кластера:

- `1C Cluster: {#CLUSTER.NAME} - Total Sessions`
- `1C Cluster: {#CLUSTER.NAME} - Active Sessions`
- `1C Cluster: {#CLUSTER.NAME} - Total Jobs`
- `1C Cluster: {#CLUSTER.NAME} - Active Jobs`

---

## Триггеры

| Название | Выражение | Приоритет |
|----------|-----------|-----------|
| 1C Cluster {#CLUSTER.NAME}: No active sessions | `last(/Host/zbx1cpy.cluster.active_sessions[{#CLUSTER.ID}])=0` | Warning |
| 1C Cluster {#CLUSTER.NAME}: Too many sessions | `last(/Host/zbx1cpy.cluster.total_sessions[{#CLUSTER.ID}])>50` | Average |
| 1C Cluster {#CLUSTER.NAME}: Active jobs stuck | `last(/Host/zbx1cpy.cluster.active_jobs[{#CLUSTER.ID}])>10` | Average |

---

## Графики

### 1C Cluster Sessions

- `zbx1cpy.cluster.total_sessions[{#CLUSTER.ID}]` (line)
- `zbx1cpy.cluster.active_sessions[{#CLUSTER.ID}]` (line)

### 1C Cluster Jobs

- `zbx1cpy.cluster.total_jobs[{#CLUSTER.ID}]` (line)
- `zbx1cpy.cluster.active_jobs[{#CLUSTER.ID}]` (line)

---

## Альтернативные способы интеграции

### Через REST API

Если Zabbix Server имеет доступ к API:

1. Настройте HTTP agent item:
   - **Type**: HTTP agent
   - **URL**: `http://localhost:8000/clusters/discovery`
   - **Update interval**: 5m

2. Используйте JSONPath для парсинга:
   - `$.data[*]` для LLD

### Через External Check

Для запуска на Zabbix Server:

```bash
# /etc/zabbix/externalscripts/1c_discovery.py
#!/usr/bin/env python3
import subprocess
import json

result = subprocess.run(
    ["python", "-m", "zbx_1c", "discovery"],
    capture_output=True,
    text=True
)
print(result.stdout)
```

---

## Проверка работы

### Тестирование UserParameter

**Windows:**
```powershell
# Discovery
"C:\Program Files\Zabbix Agent\zabbix_agentd.exe" -t zbx1cpy.clusters.discovery

# Metrics
"C:\Program Files\Zabbix Agent\zabbix_agentd.exe" -t zbx1cpy.metrics[f93863ed-3fdb-4e01-a74c-e112c81b053b]
```

**Linux:**
```bash
# Discovery
zabbix_get -s localhost -k zbx1cpy.clusters.discovery

# Metrics
zabbix_get -s localhost -k zbx1cpy.metrics[f93863ed-3fdb-4e01-a74c-e112c81b053b]
```

### Проверка в Zabbix

1. Перейдите в **Data collection → Hosts**
2. Выберите хост
3. Перейдите на вкладку **Items**
4. Проверьте **Last value** для элементов
5. Проверьте **Latest data** для получения данных в реальном времени

---

## Устранение проблем

### UserParameter не работает

1. Проверьте логи Zabbix Agent:
   ```
   C:\Program Files\Zabbix Agent\zabbix_agentd.log
   /var/log/zabbix/zabbix_agentd.log
   ```

2. Проверьте права доступа к Python скрипту

3. Убедитесь что путь к Python указан полностью

### RAC не найден

1. Проверьте путь в `.env`
2. Убедитесь что rac.exe существует
3. Проверьте права доступа

### Нет данных от кластера

1. Проверьте доступность RAS:
   ```bash
   python -m zbx_1c check-ras
   ```

2. Проверьте учетные данные в `.env`

3. Проверьте логи:
   ```
   logs/zbx-1c-*.log
   ```

---

## Макросы на уровне шаблона

| Макрос | Значение по умолчанию | Описание |
|--------|----------------------|----------|
| `{$RAC_HOST}` | 127.0.0.1 | Хост RAS сервера |
| `{$RAC_PORT}` | 1545 | Порт RAS сервера |
| `{$RAC_TIMEOUT}` | 30 | Таймаут подключения (сек) |
| `{$CLUSTER_ID}` | | ID кластера (опционально) |

---

## Производительность

### Рекомендуемые интервалы опроса

| Тип | Интервал |
|-----|----------|
| Discovery | 5m |
| Метрики | 1m |
| Сессии | 2m |

### Оптимизация

1. Используйте кэширование в приложении
2. Настройте правильный таймаут
3. Используйте активные проверки для больших кластеров

---

## Безопасность

1. Не храните пароли в репозитории
2. Используйте `.env` файл с правами 600
3. Настройте firewall для RAS порта
4. Используйте отдельные учетные записи для мониторинга

---

## Мониторинг самого zbx-1c-py

### Элементы для мониторинга

- `zbx1c.ras.available` - доступность RAS
- `zbx1c.clusters.count` - количество кластеров
- `zbx1c.last.discovery` - время последнего обнаружения

### Логи

Настройте мониторинг логов через `log[]` item:
```
log["G:\Automation\zbx-1c-py\logs\zbx-1c-*.log",ERROR]
```
