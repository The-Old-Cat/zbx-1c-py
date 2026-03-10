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
# RAC_PATH - путь к утилите rac
# Windows: RAC_PATH=C:/Program Files/1cv8/<version>/bin/rac.exe
# Linux:   RAC_PATH=/opt/1c/v8.3/<version>/rac
RAC_PATH=<PATH_TO_RAC>

RAC_HOST=127.0.0.1
RAC_PORT=1545
USER_NAME=<username>
USER_PASS=<password>

# LOG_PATH - путь для логов проекта
# Windows: LOG_PATH=./logs
# Linux:   LOG_PATH=/var/log/zbx-1c
LOG_PATH=<PATH_TO_LOGS>

DEBUG=False
SESSION_LIMIT=100
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
<ZABBIX_AGENT_DIR>\zabbix_agent2.d\userparameter_1c.conf
```

**Linux:**
```
/etc/zabbix/zabbix_agent2.d/userparameter_1c.conf
```

### Шаг 5: Перезапуск Zabbix Agent

**Windows:**
```powershell
Restart-Service zabbix-agent2
```

**Linux:**
```bash
systemctl restart zabbix-agent2
```

### Шаг 6: Импорт шаблона в Zabbix

1. В веб-интерфейсе Zabbix перейдите в **Data collection → Templates**
2. Нажмите **Import**
3. Выберите файл `zabbix/templates/templates.yaml`
4. Нажмите **Import**

### Шаг 7: Привязка шаблона к хосту

1. Перейдите в **Data collection → Hosts**
2. Выберите или создайте хост
3. На вкладке **Templates** добавьте шаблон **1C Enterprise Monitoring**
4. Настройте макросы (при необходимости):
   - `{$RAC_HOST}` - хост RAS (по умолчанию: 127.0.0.1)
   - `{$RAC_PORT}` - порт RAS (по умолчанию: 1545)
   - `{$SESSION_LIMIT}` - лимит сессий из .env (по умолчанию: 100)

---

## UserParameter

### Доступные ключи (zbx-1c-rac)

#### Discovery

| Ключ | Описание | Пример вывода |
|------|----------|---------------|
| `z1c.rac.discovery` | Обнаружение кластеров 1С (LLD) | `{"data":[{"{#CLUSTER_ID}":"...","{#CLUSTER_NAME}":"..."}]}` |

#### Метрики кластера

| Ключ | Описание | Пример |
|------|----------|--------|
| `z1c.rac.metrics[{#CLUSTER_ID}]` | Метрики кластера (JSON) | `{"cluster":{...},"metrics":{...}}` |
| `z1c.rac.metrics.all` | Метрики всех кластеров (Master Item) | `[{"cluster":{...}},...]` |
| `z1c.rac.status[{#CLUSTER_ID}]` | Статус кластера | `available` |

#### Проверки

| Ключ | Описание | Пример |
|------|----------|--------|
| `z1c.rac.check` | Проверка доступности RAS | `{"host":"...","port":...,"available":true}` |
| `z1c.rac.config.check` | Проверка конфигурации | — |
| `z1c.rac.test` | Тестовый параметр | `OK` |

#### Память процессов 1С

| Ключ | Единицы | Описание |
|------|---------|----------|
| `z1c.rac.memory.all` | МБ (JSON) | Вся память процессов: rphost, rmngr, ragent, total |
| `z1c.rac.memory.rphost` | МБ | Память рабочих процессов rphost |
| `z1c.rac.memory.rmngr` | МБ | Память менеджера кластера rmngr |
| `z1c.rac.memory.ragent` | МБ | Память агента ragent |
| `z1c.rac.memory.total` | МБ | Общая память всех процессов 1С |

#### Прямые метрики

| Ключ | Описание |
|------|----------|
| `z1c.rac.sessions.total[{#CLUSTER_ID}]` | Всего сессий |
| `z1c.rac.sessions.active[{#CLUSTER_ID}]` | Активных сессий |
| `z1c.rac.sessions.limit[{#CLUSTER_ID}]` | Лимит сессий |
| `z1c.rac.sessions.percent[{#CLUSTER_ID}]` | Процент использования сессий |
| `z1c.rac.jobs.total[{#CLUSTER_ID}]` | Всего заданий |
| `z1c.rac.jobs.active[{#CLUSTER_ID}]` | Активных фоновых заданий |
| `z1c.rac.servers.working[{#CLUSTER_ID}]` | Рабочих серверов |
| `z1c.rac.servers.total[{#CLUSTER_ID}]` | Всего серверов |
| `z1c.rac.infobases.total[{#CLUSTER_ID}]` | Всего информационных баз |

---

## Low Level Discovery (LLD)

### Правило обнаружения

- **Name**: 1C RAC Clusters Discovery
- **Type**: Zabbix agent
- **Key**: `z1c.rac.discovery`
- **Update interval**: 1h
- **Keep lost resources period**: 7d

### Макросы LLD

| Макрос | Описание | Пример |
|--------|----------|--------|
| `{#CLUSTER_ID}` | UUID кластера | `f93863ed-3fdb-4e01-a74c-e112c81b053b` |
| `{#CLUSTER_NAME}` | Имя кластера | `"Локальный кластер"` |
| `{#CLUSTER_HOST}` | Хост RAS | `srv-pinavto01` |
| `{#CLUSTER_PORT}` | Порт RAS | `1541` |
| `{#CLUSTER_STATUS}` | Статус кластера | `available` |

---

## Элементы данных (Items)

### Зависимые элементы (Dependent Items)

Шаблон использует зависимые элементы от `z1c.rac.metrics[{#CLUSTER_ID}]`:

| Ключ | Тип данных | Единицы | Описание |
|------|------------|---------|----------|
| `z1c.rac.sessions.total[{#CLUSTER_ID}]` | Numeric | | Всего сессий |
| `z1c.rac.sessions.active[{#CLUSTER_ID}]` | Numeric | | Активных сессий |
| `z1c.rac.jobs.total[{#CLUSTER_ID}]` | Numeric | | Всего заданий |
| `z1c.rac.jobs.active[{#CLUSTER_ID}]` | Numeric | | Активных фоновых заданий |
| `z1c.rac.sessions.limit[{#CLUSTER_ID}]` | Numeric | | Лимит сессий |
| `z1c.rac.sessions.percent[{#CLUSTER_ID}]` | Numeric | % | Процент использования |
| `z1c.rac.servers.working[{#CLUSTER_ID}]` | Numeric | | Рабочих серверов |
| `z1c.rac.servers.total[{#CLUSTER_ID}]` | Numeric | | Всего серверов |

### Память процессов

| Ключ | Тип данных | Единицы | Описание |
|------|------------|---------|----------|
| `z1c.rac.memory.rphost` | Numeric | МБ | Память rphost |
| `z1c.rac.memory.rmngr` | Numeric | МБ | Память rmngr |
| `z1c.rac.memory.ragent` | Numeric | МБ | Память ragent |
| `z1c.rac.memory.total` | Numeric | МБ | Общая память |

---

## Триггеры

| Название | Выражение | Приоритет |
|----------|-----------|-----------|
| 1C: Cluster {#CLUSTER_NAME} unavailable | `last(/z1c.rac.status[{#CLUSTER_ID}])="unavailable"` | High |
| 1C: Session usage on {#CLUSTER_NAME} > 80% | `last(/z1c.rac.sessions.percent[{#CLUSTER_ID}])>80` | Warning |
| 1C: No active sessions on {#CLUSTER_NAME} | `last(/z1c.rac.sessions.active[{#CLUSTER_ID}])=0` | Warning |
| 1C: Stuck jobs on {#CLUSTER_NAME} | `last(/z1c.rac.jobs.active[{#CLUSTER_ID}])>10` | Average |

---

## Проверка работы

### Тестирование UserParameter

**Windows:**
```powershell
# Discovery
zabbix_get -s 127.0.0.1 -k z1c.rac.discovery

# Metrics
zabbix_get -s 127.0.0.1 -k z1c.rac.metrics[<cluster-id>]

# Memory
zabbix_get -s 127.0.0.1 -k z1c.rac.memory.total

# Status
zabbix_get -s 127.0.0.1 -k z1c.rac.status[<cluster-id>]
```

**Linux:**
```bash
# Discovery
zabbix_get -s localhost -k z1c.rac.discovery

# Metrics
zabbix_get -s localhost -k z1c.rac.metrics[<cluster-id>]

# Memory
zabbix_get -s localhost -k z1c.rac.memory.total
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
   <ZABBIX_AGENT_DIR>\zabbix_agent2.log
   /var/log/zabbix/zabbix_agent2.log
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
| `{$SESSION_LIMIT}` | 100 | Лимит сессий (из .env) |

---

## Производительность

### Рекомендуемые интервалы опроса

| Тип | Интервал |
|-----|----------|
| Discovery | 5m |
| Метрики кластера | 1m |
| Память процессов | 1m |
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

- `zbx1cpy.ras.check` - доступность RAS
- `zbx1cpy.clusters.discovery` - количество кластеров

### Логи

Настройте мониторинг логов через `log[]` item:
```
log["<LOG_PATH>\\zbx-1c-*.log",ERROR]
```
