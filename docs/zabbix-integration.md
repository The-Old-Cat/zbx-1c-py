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
C:\Program Files\Zabbix Agent 2\zabbix_agent2.d\userparameter_1c.conf
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

### Доступные ключи

#### Discovery

| Ключ | Описание |
|------|----------|
| `zbx1cpy.clusters.discovery` | Обнаружение кластеров 1С (LLD) |

#### Метрики кластера

| Ключ | Описание |
|------|----------|
| `zbx1cpy.metrics[{#CLUSTER.ID}]` | Метрики кластера (сессии, задания) |
| `zbx1cpy.metrics.all` | Метрики всех кластеров (для Master Item) |
| `zbx1cpy.cluster.status[{#CLUSTER.ID}]` | Статус кластера: available/unavailable/unknown |

#### Память процессов 1С

| Ключ | Единицы | Описание |
|------|---------|----------|
| `zbx1cpy.memory.all` | КБ (JSON) | Вся память процессов: rphost, rmngr, ragent, total |
| `zbx1cpy.memory.rphost` | КБ | Память рабочих процессов rphost |
| `zbx1cpy.memory.rmngr` | КБ | Память менеджера кластера rmngr |
| `zbx1cpy.memory.ragent` | КБ | Память агента ragent |
| `zbx1cpy.memory.total` | КБ | Общая память всех процессов 1С |

#### Прямые метрики (для старых версий Zabbix)

| Ключ | Описание |
|------|----------|
| `zbx1cpy.cluster.total_sessions[{#CLUSTER.ID}]` | Всего сессий |
| `zbx1cpy.cluster.active_sessions[{#CLUSTER.ID}]` | Активных сессий |
| `zbx1cpy.cluster.total_jobs[{#CLUSTER.ID}]` | Всего заданий |
| `zbx1cpy.cluster.active_bg_jobs[{#CLUSTER.ID}]` | Активных фоновых заданий |
| `zbx1cpy.cluster.session_limit[{#CLUSTER.ID}]` | Лимит сессий |
| `zbx1cpy.cluster.session_percent[{#CLUSTER.ID}]` | Процент использования сессий |
| `zbx1cpy.cluster.working_servers[{#CLUSTER.ID}]` | Рабочих серверов |
| `zbx1cpy.cluster.total_servers[{#CLUSTER.ID}]` | Всего серверов |

#### Служебные

| Ключ | Описание |
|------|----------|
| `zbx1cpy.ras.check` | Проверка доступности RAS |
| `zbx1cpy.test` | Тестовый параметр |

---

## Low Level Discovery (LLD)

### Правило обнаружения

- **Name**: 1C Clusters Discovery
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
| `{#CLUSTER.STATUS}` | Статус кластера |

---

## Элементы данных (Items)

### Зависимые элементы (Dependent Items)

Шаблон использует зависимые элементы от `zbx1cpy.metrics[{#CLUSTER.ID}]`:

| Ключ | Тип данных | Единицы | Описание |
|------|------------|---------|----------|
| `zbx1cpy.cluster.total_sessions[{#CLUSTER.ID}]` | Numeric | | Всего сессий |
| `zbx1cpy.cluster.active_sessions[{#CLUSTER.ID}]` | Numeric | | Активных сессий |
| `zbx1cpy.cluster.total_jobs[{#CLUSTER.ID}]` | Numeric | | Всего заданий |
| `zbx1cpy.cluster.active_bg_jobs[{#CLUSTER.ID}]` | Numeric | | Активных фоновых заданий |
| `zbx1cpy.cluster.session_limit[{#CLUSTER.ID}]` | Numeric | | Лимит сессий |
| `zbx1cpy.cluster.session_percent[{#CLUSTER.ID}]` | Numeric | % | Процент использования |
| `zbx1cpy.cluster.working_servers[{#CLUSTER.ID}]` | Numeric | | Рабочих серверов |
| `zbx1cpy.cluster.total_servers[{#CLUSTER.ID}]` | Numeric | | Всего серверов |

### Память процессов

| Ключ | Тип данных | Единицы | Описание |
|------|------------|---------|----------|
| `zbx1cpy.memory.rphost` | Numeric | КБ | Память rphost |
| `zbx1cpy.memory.rmngr` | Numeric | КБ | Память rmngr |
| `zbx1cpy.memory.ragent` | Numeric | КБ | Память ragent |
| `zbx1cpy.memory.total` | Numeric | КБ | Общая память |

---

## Триггеры

| Название | Выражение | Приоритет |
|----------|-----------|-----------|
| 1C: Cluster {#CLUSTER.NAME} unavailable | `last(/zbx1cpy.cluster.status[{#CLUSTER.ID}])="unavailable"` | High |
| 1C: Session usage on {#CLUSTER.NAME} > 80% | `last(/zbx1cpy.cluster.session_percent[{#CLUSTER.ID}])>80` | Warning |
| 1C: No active sessions on {#CLUSTER.NAME} | `last(/zbx1cpy.cluster.active_sessions[{#CLUSTER.ID}])=0` | Warning |
| 1C: Stuck jobs on {#CLUSTER.NAME} | `last(/zbx1cpy.cluster.active_bg_jobs[{#CLUSTER.ID}])>10` | Average |

---

## Проверка работы

### Тестирование UserParameter

**Windows:**
```powershell
# Discovery
zabbix_get -s localhost -k zbx1cpy.clusters.discovery

# Metrics
zabbix_get -s localhost -k zbx1cpy.metrics[f93863ed-3fdb-4e01-a74c-e112c81b053b]

# Memory
zabbix_get -s localhost -k zbx1cpy.memory.total
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
   C:\Program Files\Zabbix Agent 2\zabbix_agent2.log
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
log["G:\Automation\zbx-1c-py\logs\zbx-1c-*.log",ERROR]
```
