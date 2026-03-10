# zbx-1c-py

Кроссплатформенный инструмент для интеграции 1С:Предприятия с системой мониторинга Zabbix.

## 📚 Документация

**Вся документация в [`docs/`](docs/) с единой нумерацией:**

| № | Документ | Описание |
|---|----------|----------|
| 01 | [docs/01-quickstart.md](docs/01-quickstart.md) | Быстрый старт |
| 02 | [docs/02-deployment.md](docs/02-deployment.md) | Развёртывание |
| 04 | [docs/04-zabbix-integration.md](docs/04-zabbix-integration.md) | Интеграция с Zabbix |

**Полный список:** [docs/README.md](docs/README.md)

---

## ⚠️ Важно: Модульная архитектура

Проект разделён на **два независимых пакета** для гибкого развёртывания:

| Пакет | Назначение | Документация |
|-------|------------|--------------|
| **[packages/zbx-1c-rac](packages/zbx-1c-rac/)** | Мониторинг через RAC | [docs/02-zbx-1c-rac.md](docs/02-zbx-1c-rac.md) |
| **[packages/zbx-1c-techlog](packages/zbx-1c-techlog/)** | Мониторинг через техжурнал | [docs/02-zbx-1c-techlog.md](docs/02-zbx-1c-techlog.md) |

---

## 🚀 Быстрый старт

### Мониторинг через RAC

```bash
cd packages/zbx-1c-rac
pip install -e .
cp ../../.env.rac.example ../../.env.rac
zbx-1c-rac check-config
```

### Мониторинг через техжурнал

```bash
cd packages/zbx-1c-techlog
pip install -e .
cp ../../.env.techlog.example ../../.env.techlog
zbx-1c-techlog check
```

### Оба пакета вместе

```bash
pip install -e ./packages/zbx-1c-rac -e ./packages/zbx-1c-techlog
```

**📖 Полная инструкция:** [docs/01-quickstart.md](docs/01-quickstart.md)

```
│   ├── README.md
│   ├── deploy/                  # Скрипты развёртывания
│   │   └── .gitkeep
│   └── dev/                     # Скрипты разработки
│       └── .gitkeep
├── data/                        # Данные
│   └── .gitkeep
├── docs/                        # Документация
├── logs/                        # Логи
│   └── .gitkeep
├── zabbix/                      # Конфигурация Zabbix
│   ├── templates/               # Шаблоны Zabbix
│   └── userparameters/          # UserParameter для Zabbix Agent
│       └── .gitkeep
├── .env.example                 # Пример конфигурации
├── pyproject.toml               # Конфигурация проекта
├── README.md
└── LICENSE
```

---

## 🛠 Установка и настройка

### Требования

- Python 3.10+
- Утилита `rac` / `rac.exe` (Remote Administration Console) для 1С
- Доступ к серверу администрирования 1С (RAS)
- Учетные данные администратора кластера 1С (опционально)

### Установка зависимостей

**Вариант 1: Через uv (рекомендуется)**

```bash
# Синхронизация зависимостей и установка пакета
uv sync

# Или только установка пакета без sync
uv pip install -e .

# Запуск без установки (разработка)
uv run zbx-1c check-ras
```

**Вариант 2: Через pip**

```bash
# Установка пакета
pip install -e .

# Для разработки с dev-зависимостями
pip install -e ".[dev]"
```

**Вариант 3: Через `pip` с `uv`**

```bash
# Установка зависимостей через uv pip
uv pip install -e ".[dev]"
```

### Конфигурация

1. Создайте файл `.env` на основе примера:

```bash
cp .env.example .env
```

2. Отредактируйте `.env`, указав свои значения:

```ini
# Путь к утилите rac (различается в зависимости от ОС)
# Windows:
# RAC_PATH=C:/Program Files/1cv8/8.3.x.x/bin/rac.exe
# Linux:
# RAC_PATH=/opt/1C/v8.3/x.x.x.x/rac
# macOS:
# RAC_PATH=/Applications/1C/Enterprise Platform/x.x.x.x/rac

# Хост и порт RAS-сервиса
RAC_HOST=127.0.0.1
RAC_PORT=1545

# Параметры аутентификации (опционально)
USER_NAME=<username>
USER_PASS=<password>

# Путь к директории для логов
LOG_PATH=./logs

# Режим отладки
DEBUG=False

# Таймауты (секунды)
RAC_TIMEOUT=30
COMMAND_TIMEOUT=60

# Время жизни кэша (секунды)
CACHE_TTL=300
```

---

## ▶️ Использование

### CLI команды

#### Способы запуска

После установки `pip install -e .` доступны три способа запуска CLI:

**1. Через основные entry points (рекомендуется для продакшена):**

```bash
zbx-1c <command> [options]           # Основная команда
zbx-1c-check-ras                      # Проверка RAS
zbx-1c-discovery                      # Обнаружение кластеров
zbx-1c-clusters                       # Список кластеров
zbx-1c-metrics [cluster_id]           # Метрики
zbx-1c-status <cluster_id>            # Статус кластера
zbx-1c-infobases <cluster_id>         # Информационные базы
zbx-1c-sessions <cluster_id>          # Сессии
zbx-1c-jobs <cluster_id>              # Фоновые задания
zbx-1c-all <cluster_id>               # Вся информация о кластере
zbx-1c-memory                         # Память процессов 1С
zbx-1c-test                           # Тест подключения
zbx-1c-monitor [cluster_id]           # Мониторинг (алиас metrics)
zbx-1c-check-config                   # Проверка конфигурации
```

**2. Как Python-модуль:**

```bash
python -m zbx_1c <command> [options]
```

**3. Через uv (для разработки и тестирования):**

```bash
# Основная команда с подкомандами
uv run zbx-1c <command> [options]
uv run zbx-1c check-ras
uv run zbx-1c discovery
uv run zbx-1c metrics <cluster-id>

# Отдельные entry points
uv run zbx-1c-check-ras
uv run zbx-1c-discovery
uv run zbx-1c-clusters
uv run zbx-1c-metrics [cluster_id]
uv run zbx-1c-status <cluster_id>
uv run zbx-1c-infobases <cluster_id>
uv run zbx-1c-sessions <cluster_id>
uv run zbx-1c-jobs <cluster_id>
uv run zbx-1c-all <cluster_id>
uv run zbx-1c-memory
uv run zbx-1c-test
uv run zbx-1c-monitor [cluster_id]
uv run zbx-1c-check-config

# С указанием конфигурации
uv run zbx-1c-check-ras --config .env.prod
uv run zbx-1c metrics --config /path/to/.env
```

> **Примечание:** Использование `uv run` предпочтительно в среде разработки, так как команда автоматически создаст виртуальное окружение и запустит проект без явной установки.

---

### 📋 Справочник всех команд

#### Общая информация

| Команда | Entry point | Описание | Аргументы |
|---------|-------------|----------|-----------|
| `check-ras` | `zbx-1c-check-ras` | Проверка доступности RAS сервиса | — |
| `check-config` | `zbx-1c-check-config` | Проверка корректности конфигурации | — |
| `discovery` | `zbx-1c-discovery` | Обнаружение кластеров для Zabbix LLD | — |
| `clusters` | `zbx-1c-clusters` | Список доступных кластеров | — |
| `infobases` | `zbx-1c-infobases` | Получение информационных баз | `<cluster_id>` |
| `sessions` | `zbx-1c-sessions` | Получение сессий кластера | `<cluster_id>` |
| `jobs` | `zbx-1c-jobs` | Получение фоновых заданий | `<cluster_id>` |
| `metrics` | `zbx-1c-metrics` | Получение метрик (для Zabbix) | `[cluster_id]` |
| `status` | `zbx-1c-status` | Статус кластера | `<cluster_id>` |
| `all` | `zbx-1c-all` | Вся информация о кластере | `<cluster_id>` |
| `memory` | `zbx-1c-memory` | Память процессов 1С (rphost, rmngr, ragent) | — |
| `test` | `zbx-1c-test` | Тестирование подключения | — |
| `monitor` | `zbx-1c-monitor` | Мониторинг (алиас `metrics`) | `[cluster_id]` |

---

### 🔍 Подробное описание команд

#### `check-ras` — Проверка доступности RAS сервиса

Проверяет сетевую доступность сервиса RAS (Remote Administration Service) 1С.

**Синоним:** `zbx-1c-check-ras`

**Опции:**
| Опция | Краткая | Описание | По умолчанию |
|-------|---------|----------|--------------|
| `--config` | `-c` | Путь к файлу конфигурации `.env` | `.env` |

**Примеры:**
```bash
# Проверка с конфигурацией по умолчанию
zbx-1c-check-ras

# Проверка с указанием конфигурации
zbx-1c check-ras --config /path/to/.env

# Краткая форма
zbx-1c check-ras -c .env.prod
```

**Пример вывода:**
```json
{
  "host": "127.0.0.1",
  "port": 1545,
  "available": true,
  "rac_path": "C:/Program Files/1cv8/<version>/bin/rac.exe"
}
```

**Коды возврата:**
- `0` — RAS доступен
- `1` — RAS недоступен или ошибка выполнения

---

#### `check-config` — Проверка корректности конфигурации

Выполняет полную проверку конфигурации проекта: наличие rac, доступность RAS, права на запись логов.

**Синоним:** `zbx-1c-check-config`

**Опции:**
| Опция | Краткая | Описание | По умолчанию |
|-------|---------|----------|--------------|
| `--config` | `-c` | Путь к файлу конфигурации `.env` | `.env` |

**Примеры:**
```bash
# Проверка конфигурации
zbx-1c-check-config

# Через основную команду
zbx-1c check-config

# С указанием конфигурации
zbx-1c check-config --config /path/to/.env
```

**Пример вывода:**
```
============================================================
РЕЗУЛЬТАТЫ ПРОВЕРКИ КОНФИГУРАЦИИ
============================================================

[+] RAC_PATH        - Файл доступен: C:/Program Files/1cv8/<version>/bin/rac.exe
[+] LOG_PATH        - Директория для логов доступна: logs
[+] RAC_HOST        - Хост RAS: 127.0.0.1
[+] RAC_PORT        - Порт RAS: 1545
[+] RAS_CONNECTION  - Подключение к RAS успешно установлено
------------------------------------------------------------
Проверок пройдено: 5/5
:) Вся конфигурация корректна!
```

**Проверяемые параметры:**
| Параметр | Описание |
|----------|----------|
| `RAC_PATH` | Наличие и доступность исполняемого файла rac |
| `LOG_PATH` | Доступность директории для записи логов |
| `RAC_HOST` | Корректность хоста RAS |
| `RAC_PORT` | Корректность порта RAS |
| `RAS_CONNECTION` | Подключение к RAS сервису |

**Коды возврата:**
- `0` — все проверки пройдены
- `1` — обнаружены проблемы с конфигурацией

---

#### `discovery` — Обнаружение кластеров (LLD)

Обнаруживает все доступные кластеры 1С и выводит результат в формате JSON для Zabbix Low Level Discovery.

**Синоним:** `zbx-1c-discovery`

**Опции:**
| Опция | Краткая | Описание | По умолчанию |
|-------|---------|----------|--------------|
| `--config` | `-c` | Путь к файлу конфигурации `.env` | `.env` |

**Примеры:**
```bash
# Обнаружение кластеров
zbx-1c-discovery

# Через основную команду
zbx-1c discovery

# С указанием конфигурации
zbx-1c discovery -c /etc/zabbix/.env
```

**Пример вывода:**
```json
{
  "data": [
    {
      "id": "<cluster-id-1>",
      "name": "Production Cluster",
      "host": "127.0.0.1",
      "port": 1545,
      "status": "unknown"
    },
    {
      "id": "<cluster-id-2>",
      "name": "Test Cluster",
      "host": "127.0.0.1",
      "port": 1545,
      "status": "unknown"
    }
  ]
}
```

**Использование в Zabbix:**
```
UserParameter=zbx1cpy.clusters.discovery,zbx-1c-discovery
```

---

#### `clusters` — Список кластеров

Выводит список доступных кластеров 1С в текстовом или JSON формате.

**Опции:**
| Опция | Краткая | Описание | По умолчанию |
|-------|---------|----------|--------------|
| `--config` | `-c` | Путь к файлу конфигурации `.env` | `.env` |
| `--json-output` | — | Вывод в формате JSON | `false` |

**Примеры:**
```bash
# Текстовый вывод
zbx-1c clusters

# JSON вывод
zbx-1c clusters --json-output

# С конфигурацией
zbx-1c clusters -c .env.prod --json-output
```

**Пример текстового вывода:**
```
📊 Доступные кластеры 1С:

1. Production Cluster
   ID: <cluster-id-1>
   Host: 127.0.0.1:1545
   Status: unknown

2. Test Cluster
   ID: <cluster-id-2>
   Host: 127.0.0.1:1545
   Status: unknown
```

**Пример JSON вывода:**
```json
[
  {
    "id": "<cluster-id>",
    "name": "Production Cluster",
    "host": "127.0.0.1",
    "port": 1545,
    "status": "unknown"
  }
]
```

---

#### `infobases <cluster_id>` — Информационные базы

Получает список информационных баз указанного кластера.

**Синоним:** `zbx-1c-infobases`

**Аргументы:**
| Аргумент | Описание |
|----------|----------|
| `cluster_id` | UUID кластера 1С (можно указать в кавычках или без) |

**Опции:**
| Опция | Краткая | Описание | По умолчанию |
|-------|---------|----------|--------------|
| `--config` | `-c` | Путь к файлу конфигурации `.env` | `.env` |

**Примеры:**
```bash
# Получение информационных баз
zbx-1c infobases <cluster-id>

# С кавычками (если ID содержит спецсимволы)
zbx-1c infobases "<cluster-id>"

# Через entry point
zbx-1c-infobases <cluster-id>

# С конфигурацией
zbx-1c infobases <cluster-id> -c .env.prod
```

**Пример вывода:**
```json
[
  {
    "infobase": "<infobase-id-1>",
    "name": "<infobase-name-1>",
    "descr": "<infobase-description-1>",
    "dbms": "<dbms-type>",
    "dbserver": "<db-server-host>",
    "dbname": "<database-name-1>"
  },
  {
    "infobase": "<infobase-id-2>",
    "name": "<infobase-name-2>",
    "descr": "<infobase-description-2>",
    "dbms": "<dbms-type>",
    "dbserver": "<db-server-host>",
    "dbname": "<database-name-2>"
  }
]
```

---

#### `sessions <cluster_id>` — Сессии

Получает список активных сессий указанного кластера.

**Синоним:** `zbx-1c-sessions`

**Аргументы:**
| Аргумент | Описание |
|----------|----------|
| `cluster_id` | UUID кластера 1С |

**Опции:**
| Опция | Краткая | Описание | По умолчанию |
|-------|---------|----------|--------------|
| `--config` | `-c` | Путь к файлу конфигурации `.env` | `.env` |

**Примеры:**
```bash
# Получение сессий
zbx-1c sessions <cluster-id>

# Через entry point
zbx-1c-sessions <cluster-id>
```

**Пример вывода:**
```json
[
  {
    "session-id": "1",
    "user": "<username>",
    "app": "1CV8C",
    "infobase": "<infobase-name-1>",
    "host": "<client-host>",
    "started-at": "2024-01-15T10:30:00",
    "last-active": "2024-01-15T14:25:00",
    "hibernate": "no"
  },
  {
    "session-id": "2",
    "user": "<username>",
    "app": "Designer",
    "infobase": "<infobase-name-2>",
    "host": "<client-host>",
    "started-at": "2024-01-15T09:00:00",
    "last-active": "2024-01-15T14:20:00",
    "hibernate": "no"
  }
]
```

---

#### `jobs <cluster_id>` — Фоновые задания

Получает список фоновых заданий указанного кластера.

**Синоним:** `zbx-1c-jobs`

**Аргументы:**
| Аргумент | Описание |
|----------|----------|
| `cluster_id` | UUID кластера 1С |

**Опции:**
| Опция | Краткая | Описание | По умолчанию |
|-------|---------|----------|--------------|
| `--config` | `-c` | Путь к файлу конфигурации `.env` | `.env` |

**Примеры:**
```bash
# Получение фоновых заданий
zbx-1c jobs <cluster-id>

# Через entry point
zbx-1c-jobs <cluster-id>
```

**Пример вывода:**
```json
[
  {
    "job-id": "100",
    "infobase": "<infobase-name-1>",
    "started-at": "2024-01-15T12:00:00",
    "status": "running",
    "description": "<job-description-1>"
  },
  {
    "job-id": "101",
    "infobase": "<infobase-name-2>",
    "started-at": "2024-01-15T11:30:00",
    "status": "completed",
    "description": "<job-description-2>"
  }
]
```

---

#### `metrics [cluster_id]` — Метрики кластера

Получает метрики кластера для мониторинга в Zabbix. Если `cluster_id` не указан, собирает метрики для всех кластеров.

**Синоним:** `zbx-1c-metrics`

**Аргументы:**
| Аргумент | Обязательный | Описание |
|----------|--------------|----------|
| `cluster_id` | Нет | UUID кластера 1С. Если не указан — все кластеры |

**Опции:**
| Опция | Краткая | Описание | По умолчанию |
|-------|---------|----------|--------------|
| `--config` | `-c` | Путь к файлу конфигурации `.env` | `.env` |

**Примеры:**
```bash
# Метрики конкретного кластера
zbx-1c metrics <cluster-id>

# Метрики всех кластеров
zbx-1c metrics

# Через entry point
zbx-1c-metrics <cluster-id>
```

**Пример вывода (один кластер):**
```json
{
  "cluster": {
    "id": "<cluster-id>",
    "name": "Production Cluster",
    "status": "unknown"
  },
  "metrics": {
    "total_sessions": 15,
    "active_sessions": 12,
    "total_jobs": 3,
    "active_jobs": 1,
    "session_limit": 20,
    "session_percent": 75.0,
    "working_servers": 2,
    "total_servers": 2
  }
}
```

**Пример вывода (все кластеры):**
```json
[
  {
    "cluster": {
      "id": "<cluster-id-1>",
      "name": "Production Cluster",
      "status": "unknown"
    },
    "metrics": {
      "total_sessions": 15,
      "active_sessions": 12,
      "total_jobs": 3,
      "active_jobs": 1,
      "session_limit": 20,
      "session_percent": 75.0,
      "working_servers": 2,
      "total_servers": 2
    }
  },
  {
    "cluster": {
      "id": "<cluster-id-2>",
      "name": "Test Cluster",
      "status": "unknown"
    },
    "metrics": {
      "total_sessions": 5,
      "active_sessions": 3,
      "total_jobs": 1,
      "active_jobs": 0,
      "session_limit": 10,
      "session_percent": 50.0,
      "working_servers": 1,
      "total_servers": 1
    }
  }
]
```

**Собираемые метрики:**

| Метрика | Описание |
|---------|----------|
| `total_sessions` | Общее количество сессий |
| `active_sessions` | **Активные** сессии (двухуровневый критерий: last-active-at ≤ 10 мин для Designer или ≤ 5 мин для остальных, либо hibernate=no + calls ≥ 1 + bytes ≥ 1024) |
| `total_jobs` | Общее количество фоновых заданий |
| `active_jobs` | Количество активных фоновых заданий (JobScheduler всегда активен, остальные по hibernate) |
| `session_limit` | Лимит сессий (сумма max-connections по всем ИБ) |
| `session_percent` | Процент заполнения сессий |
| `working_servers` | Количество рабочих серверов 1С |
| `total_servers` | Общее количество серверов кластера |
| `server_memory_percent` | Процент использования памяти всеми серверами кластера |
| `servers_restarted_recently` | Количество серверов, перезапущенных за последние 5 минут |

**Использование в Zabbix:**
```
UserParameter=zbx1cpy.metrics[*],zbx-1c-metrics $1
```

---

#### `status <cluster_id>` — Статус кластера

Получает статус указанного кластера в текстовом формате для использования в Zabbix UserParameter.

**Синоним:** `zbx-1c-status`

**Аргументы:**
| Аргумент | Описание |
|----------|----------|
| `cluster_id` | UUID кластера 1С |

**Опции:**
| Опция | Краткая | Описание | По умолчанию |
|-------|---------|----------|--------------|
| `--config` | `-c` | Путь к файлу конфигурации `.env` | `.env` |

**Примеры:**
```bash
# Статус конкретного кластера
zbx-1c status <cluster-id>

# Через entry point
zbx-1c-status <cluster-id>

# С конфигурацией
zbx-1c status <cluster-id> -c .env.prod
```

**Пример вывода:**
```
available
```

**Возможные значения:**
- `available` — кластер доступен (порт отвечает)
- `unavailable` — кластер недоступен (порт не отвечает)
- `unknown` — не удалось определить статус (ошибка или кластер не найден)

**Использование в Zabbix:**
```ini
UserParameter=zbx1cpy.cluster.status[*],zbx-1c-status $1
```

**Настройка элемента данных:**
| Параметр | Значение |
|----------|----------|
| **Type** | Zabbix agent |
| **Key** | `zbx1cpy.cluster.status[{#ID}]` |
| **Type of information** | Text |
| **Preprocessing** | Map value: available→1, unavailable→0, unknown→2 |

---

#### `all <cluster_id>` — Полная информация о кластере

Получает всю доступную информацию о кластере: данные кластера, информационные базы, сессии, задания и статистику.

**Аргументы:**
| Аргумент | Описание |
|----------|----------|
| `cluster_id` | UUID кластера 1С |

**Опции:**
| Опция | Краткая | Описание | По умолчанию |
|-------|---------|----------|--------------|
| `--config` | `-c` | Путь к файлу конфигурации `.env` | `.env` |

**Примеры:**
```bash
# Полная информация о кластере
zbx-1c all <cluster-id>

# С конфигурацией
zbx-1c all <cluster-id> -c .env.prod
```

**Пример вывода:**
```json
{
  "cluster": {
    "id": "<cluster-id>",
    "name": "Production Cluster",
    "host": "127.0.0.1",
    "port": 1545,
    "status": "unknown"
  },
  "infobases": [
    {
      "infobase": "<infobase-id>",
      "name": "<infobase-name>"
    }
  ],
  "sessions": [
    {
      "session-id": "1",
      "user": "<username>",
      "app": "1CV8C"
    }
  ],
  "jobs": [
    {
      "job-id": "100",
      "status": "running"
    }
  ],
  "statistics": {
    "total_infobases": 3,
    "total_sessions": 15,
    "active_sessions": 12,
    "total_jobs": 3,
    "active_jobs": 1
  },
  "timestamp": "2024-01-15T14:30:00.123456"
}
```

---

#### `test` — Тестирование подключения

Выполняет полную проверку подключения к 1С: проверяет наличие утилиты `rac`, доступность RAS, обнаружение кластеров и сбор метрик.

**Синоним:** `zbx-1c-test`

**Опции:**
| Опция | Краткая | Описание | По умолчанию |
|-------|---------|----------|--------------|
| `--config` | `-c` | Путь к файлу конфигурации `.env` | `.env` |

**Примеры:**
```bash
# Тестирование подключения
zbx-1c test

# Через entry point
zbx-1c-test

# С конфигурацией
zbx-1c test -c .env.prod
```

**Пример вывода:**
```
🔧 Тестирование подключения к 1С...

📁 RAC path: C:/Program Files/1cv8/<version>/bin/rac.exe
   ✅ RAC executable found

🌐 RAS: 127.0.0.1:1545
   ✅ RAS is available

📊 Clusters found: 2
   - Production Cluster (<cluster-id-1>)
     ✅ Metrics collected: 15 sessions, 12 active, 3 jobs
   - Test Cluster (<cluster-id-2>)
     ✅ Metrics collected: 5 sessions, 3 active, 1 jobs

✅ Все проверки пройдены успешно
```

**Коды возврата:**
- `0` — все проверки пройдены
- `1` — ошибка подключения или сбора данных

---

#### `monitor` — Мониторинг (алиас `metrics`)

Алиас команды `metrics` для обратной совместимости.

**Синоним:** `zbx-1c-monitor`

См. документацию команды [`metrics`](#metrics-cluster_id--метрики-кластера).

---

#### `techjournal` — Мониторинг техжурнала 1С

Сбор метрик из логов техжурнала 1С (ошибки, блокировки, долгие вызовы, медленный SQL).

**Синоним:** `zbx-1c-techjournal`

**Опции:**
| Опция | Краткая | Описание | По умолчанию |
|-------|---------|----------|--------------|
| `--config` | `-c` | Путь к файлу конфигурации `.env` | `.env` |
| `--period` | `-p` | Период сбора метрик (минуты) | `5` |
| `--json-output` | — | Вывод в формате JSON | `false` |

**Примеры:**
```bash
# Текстовая сводка
zbx-1c techjournal

# JSON вывод
zbx-1c techjournal --json-output

# Сбор метрик за 15 минут
zbx-1c techjournal --period 15

# Через entry point
zbx-1c-techjournal --period 10
```

**Пример вывода (текст):**
```
============================================================
МОНИТОРИНГ ТЕХЖУРНАЛА 1С
============================================================
Период: 5 мин
Время сбора: 2024-01-15 14:30:00
------------------------------------------------------------
Всего событий: 42
Критичные события: 5
------------------------------------------------------------
СОБЫТИЯ:
  Ошибки (EXCP):        3
  Предупреждения (ATTN): 2
  Deadlock (TDEADLOCK): 1
  Timeout (TTIMEOUT):   1
  Блокировки (TLOCK):   5
  Долгие вызовы (CALL): 15
  Медленный SQL:        15
  События кластера:     0
  Админ.события:        0
  └─ Средняя длительность блокировок: 650.5 мс
  └─ Средняя длительность вызовов: 320.25 мс
  └─ Средняя длительность SQL: 125.8 мс
============================================================
```

**Пример вывода (JSON):**
```json
{
  "timestamp": "2024-01-15T14:30:00",
  "period_seconds": 300,
  "logs_base_path": "<PATH_TO_LOGS>",
  "total_events": 42,
  "critical_events": 5,
  "errors.count": 3,
  "errors.users": 2,
  "errors.avg_duration_ms": 0.0,
  "warnings.count": 2,
  "deadlocks.count": 1,
  "timeouts.count": 1,
  "long_locks.count": 5,
  "long_locks.avg_duration_ms": 650.5,
  "long_calls.count": 15,
  "long_calls.avg_duration_ms": 320.25,
  "slow_sql.count": 15,
  "slow_sql.avg_duration_ms": 125.8,
  "cluster_events.count": 0,
  "admin_events.count": 0
}
```

**Собираемые метрики:**

| Метрика | Описание |
|---------|----------|
| `total_events` | Общее количество событий |
| `critical_events` | Критичные события (EXCP, TDEADLOCK, TTIMEOUT) |
| `errors.count` | Количество ошибок |
| `errors.users` | Количество уникальных пользователей с ошибками |
| `warnings.count` | Количество предупреждений |
| `deadlocks.count` | Количество deadlock'ов |
| `timeouts.count` | Количество таймаутов |
| `long_locks.count` | Количество длительных блокировок (>500 мс) |
| `long_locks.avg_duration_ms` | Средняя длительность блокировок |
| `long_calls.count` | Количество долгих вызовов (>200 мс) |
| `long_calls.avg_duration_ms` | Средняя длительность вызовов |
| `slow_sql.count` | Количество медленных SQL-запросов (>80 мс) |
| `slow_sql.avg_duration_ms` | Средняя длительность SQL-запросов |

**Использование в Zabbix:**
```ini
UserParameter=zbx1cpy.techjournal[*],zbx-1c-techjournal --json-output
```

---

### 🔧 Общие опции для всех команд

| Опция | Краткая | Описание | По умолчанию |
|-------|---------|----------|--------------|
| `--config` | `-c` | Путь к файлу конфигурации `.env` | `.env` |
| `--help` | `-h` | Показать справку и выйти | — |

---

### 📁 Конфигурационный файл `.env`

Все команды используют конфигурацию из файла `.env` (по умолчанию в текущей директории).

**Пример `.env`:**
```env
# Путь к утилите rac
RAC_PATH=C:/Program Files/1cv8/<version>/bin/rac.exe

# Хост и порт RAS-сервиса
RAC_HOST=127.0.0.1
RAC_PORT=1545

# Параметры аутентификации в кластере (опционально)
USER_NAME=<username>
USER_PASS=<password>

# Таймаут подключения к RAS (секунды)
RAC_TIMEOUT=30

# Таймаут выполнения команд rac (секунды)
RAC_COMMAND_TIMEOUT=60

# Уровень логирования
LOG_LEVEL=INFO
LOG_PATH=./logs
```

**Переменные окружения:**

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `RAC_PATH` | Путь к утилите `rac` / `rac.exe` | Зависит от ОС |
| `RAC_HOST` | Хост RAS-сервиса | `127.0.0.1` |
| `RAC_PORT` | Порт RAS-сервиса | `1545` |
| `USER_NAME` | Имя пользователя кластера | — |
| `USER_PASS` | Пароль пользователя кластера | — |
| `RAC_TIMEOUT` | Таймаут подключения (сек) | `30` |
| `RAC_COMMAND_TIMEOUT` | Таймаут команды (сек) | `60` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `LOG_PATH` | Путь к логам | `./logs` |

---

### 💡 Примеры использования

#### Быстрая диагностика

```bash
# Через entry points (продакшен)
zbx-1c-check-config
zbx-1c-check-ras
zbx-1c clusters
zbx-1c metrics

# Через uv (разработка)
uv run zbx-1c-check-config
uv run zbx-1c-check-ras
uv run zbx-1c clusters
uv run zbx-1c metrics
```

#### Мониторинг конкретного кластера

```bash
# Через entry points
zbx-1c metrics <cluster-id>
zbx-1c sessions <cluster-id>
zbx-1c jobs <cluster-id>

# Через uv
uv run zbx-1c metrics <cluster-id>
uv run zbx-1c sessions <cluster-id>
uv run zbx-1c jobs <cluster-id>
```

#### Полная информация о кластере

```bash
# Через entry points
zbx-1c all <cluster-id>

# Через uv
uv run zbx-1c all <cluster-id>
```

#### Тестирование подключения

```bash
# Через entry points
zbx-1c-test

# Через uv
uv run zbx-1c-test
```

#### Интеграция со скриптами

```bash
# Получить количество активных сессий (для bash)
SESSIONS=$(zbx-1c metrics $CLUSTER_ID | jq '.metrics.active_sessions')

# Через uv
SESSIONS=$(uv run zbx-1c metrics $CLUSTER_ID | jq '.metrics.active_sessions')

# Проверить доступность RAS (для PowerShell)
$available = (zbx-1c-check-ras | ConvertFrom-Json).available
if ($available) { Write-Host "RAS is up" }

# Через uv
$available = (uv run zbx-1c-check-ras | ConvertFrom-Json).available
if ($available) { Write-Host "RAS is up" }
```

#### Использование с разными конфигурациями

```bash
# Продакшен окружение
zbx-1c metrics --config .env.prod
uv run zbx-1c metrics --config .env.prod

# Тестовое окружение
zbx-1c discovery -c .env.test
uv run zbx-1c discovery -c .env.test
```

---

### 🐛 Отладка

Для включения подробного логирования установите в `.env`:

```env
DEBUG=True
LOG_LEVEL=DEBUG
```

Логи будут записаны в директорию, указанную в `LOG_PATH` (по умолчанию `./logs`).

### REST API

Запуск FastAPI приложения:

```bash
uvicorn zbx_1c.api.main:app --reload --host 0.0.0.0 --port 8000
```

#### Доступные эндпоинты

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/` | Корневой эндпоинт |
| GET | `/health` | Проверка здоровья приложения |
| GET | `/clusters/discovery` | Обнаружение кластеров (LLD) |
| GET | `/clusters` | Список всех кластеров |
| GET | `/clusters/{cluster_id}/metrics` | Метрики кластера |
| GET | `/clusters/{cluster_id}/sessions` | Сессии кластера |
| GET | `/clusters/{cluster_id}/jobs` | Фоновые задания кластера |
| GET | `/ras/status` | Статус RAS сервиса |

---

## 📊 Собираемые метрики

### Метрики кластера

| Ключ | Описание | Критерии |
|------|----------|----------|
| `zbx1cpy.cluster.total_sessions` | Общее количество сессий | Все сессии из `rac session list` |
| `zbx1cpy.cluster.active_sessions` | Количество **активных** сессий | **Двухуровневый критерий**:<br>1️⃣ **last-active-at ≤ порог** → активна<br>2️⃣ **last-active-at > порог** → строгая проверка:<br>   • `hibernate == "no"`<br>   • `calls-last-5min >= 1`<br>   • `bytes-last-5min >= 1024 байт`<br><br>**Пороги по типам**:<br>• `Designer` (Конфигуратор): **10 минут**<br>• Остальные: **5 минут** |
| `zbx1cpy.cluster.total_jobs` | Общее количество фоновых заданий | Все задания из `rac session list` с `app-id` = BackgroundJob / SystemBackgroundJob / JobScheduler |
| `zbx1cpy.cluster.active_jobs` | Количество активных фоновых заданий | **По типу задания**:<br>• `JobScheduler`: **всегда активен**<br>• `SystemBackgroundJob`: `hibernate == "no"`<br>• `BackgroundJob`: `hibernate == "no"` |
| `zbx1cpy.cluster.long_running_jobs` | Количество длительных фоновых заданий | Задания типов:<br>• `BackgroundJob`: фоновые задания пользователей<br>• `SystemBackgroundJob`: системные фоновые задания<br><br>Исключение: `JobScheduler` не считается длительным |
| `zbx1cpy.cluster.stuck_jobs` | Количество «зависших» заданий | Задание считается зависшим, если:<br>1. Тип: `BackgroundJob` или `SystemBackgroundJob`<br>2. Статус: активное (`hibernate == "no"`)<br>3. Время выполнения: **> 30 минут** |
| `zbx1cpy.cluster.max_job_duration` | Максимальное время выполнения заданий | Максимальная длительность среди активных заданий (в минутах) |
| `zbx1cpy.cluster.session_limit` | Лимит сессий (сумма по ИБ) | Берется из `SESSION_LIMIT` в `.env` (количество лицензий) |
| `zbx1cpy.cluster.session_percent` | Процент заполнения сессий | `total_sessions / session_limit * 100` |
| `zbx1cpy.cluster.working_servers` | Количество рабочих серверов | Серверы со статусом `working` |
| `zbx1cpy.cluster.total_servers` | Общее количество серверов | Все серверы кластера |
| `zbx1cpy.cluster.server_memory_used` | Фактическое использование памяти | Суммарная память всех процессов rphost (КБ) |
| `zbx1cpy.cluster.server_memory_limit` | Лимит памяти кластера | Лимит памяти из настроек рабочих серверов (КБ). `0` = лимит не задан |
| `zbx1cpy.cluster.server_memory_percent` | Процент использования памяти | `(server_memory_used / server_memory_limit) * 100`. `0` = лимит не задан |
| `zbx1cpy.cluster.memory_limit_set` | Флаг заданного лимита памяти | `1` = лимит задан, `0` = лимит не задан |
| `zbx1cpy.cluster.servers_restarted_recently` | Количество перезапусков серверов | Серверы, перезапущенные за последние 5 минут |

> **Примечание:** Метрика `active_sessions` использует **двухуровневый критерий** активности:
> 1. **last-active-at ≤ порог** → сессия активна (быстрая проверка)
> 2. **last-active-at > порог** → строгая проверка (hibernate + calls + bytes)
>
> **Пороги last-active-at:**
> - **Designer (Конфигуратор)**: 10 минут (разработчик может читать код без вызовов)
> - **Остальные**: 5 минут (стандартная сессия)

### Метрики сессий

- Session ID
- Пользователь
- Приложение (Designer, 1CV8C, и т.д.)
- Информационная база
- Хост подключения
- Время начала сессии
- Время последней активности
- Статус (hibernate)
- Статистика вызовов и трафика

### Метрики информационных баз

- Имя и описание ИБ
- Количество сессий (всего/активных)
- Количество уникальных пользователей
- Типы подключенных приложений
- Интенсивность вызовов
- Объем трафика
- Активные фоновые задания
- Блоровки

---

## 🔧 Интеграция с Zabbix

### Настройка Zabbix Agent

#### Пример конфигурации Zabbix Agent

Пример файла конфигурации Zabbix Agent представлен в [`zabbix/zabbix_agentd.conf.example`](zabbix/zabbix_agentd.conf.example).

**Основные параметры:**

```conf
# Путь к файлу лога
LogFile=C:\Program Files\Zabbix Agent\zabbix_agentd.log

# Адрес Zabbix сервера
Server=127.0.0.1,<IP-АДРЕС_ВАШЕГО_СЕРВЕРА_ZABBIX>

# Адрес для активных проверок
ServerActive=<IP-АДРЕС_ВАШЕГО_СЕРВЕРА_ZABBIX>

# Имя хоста (должно совпадать с Zabbix)
Hostname=<ИМЯ_ВАШЕГО_ХОСТА_В_ZABBIX>

# Таймаут выполнения проверок (увеличить для скриптов 1С)
Timeout=30

# Разрешить выполнение команд
AllowKey=system.run[*]

# Директория для дополнительных конфигов (включая userparameter_1c.conf)
Include=C:\Program Files\Zabbix Agent\zabbix_agentd.d
```

**Рекомендуемые настройки для мониторинга 1С:**

| Параметр | Значение | Описание |
|----------|----------|----------|
| `Timeout` | `30` | Увеличенный таймаут для выполнения скриптов rac |
| `LogRemoteCommands` | `1` | Логирование выполняемых команд (для отладки) |
| `DebugLevel` | `3` | Уровень логирования для отладки проблем |
| `Include` | `zabbix_agentd.d\` | Директория для подключения UserParameter |

**Полный пример** см. в файле [`zabbix/zabbix_agentd.conf.example`](zabbix/zabbix_agentd.conf.example).

---

#### 1. Установка пакета

**Вариант 1: Через uv (рекомендуется)**
```bash
uv sync
# или
uv pip install -e .
```

**Вариант 2: Через pip**
```bash
pip install -e .
```

#### 2. Генерация конфигурации UserParameter

```bash
# Через entry point (после установки)
zbx-1c-generate-userparam

# Или через uv (для разработки)
uv run zbx-1c-generate-userparam
```

#### 3. Копирование файла конфигурации

**Windows (от администратора):**
```powershell
Copy-Item "zabbix\userparameters\userparameter_1c.conf" `
    -Destination "C:\Program Files\Zabbix Agent 2\zabbix_agent2.d\" -Force
```

**Linux:**
```bash
sudo cp zabbix/userparameters/userparameter_1c.conf /etc/zabbix/zabbix_agentd.d/
```

> **Важно:** Отредактируйте пути к Python и проекту в файле `userparameter_1c.conf` под вашу среду!

#### 4. Перезапуск Zabbix Agent

**Windows:**
```powershell
Restart-Service "Zabbix Agent 2"
```

**Linux:**
```bash
sudo systemctl restart zabbix-agent
```

#### 5. Проверка

```bash
# Windows
& "<ZABBIX_AGENT_DIR>\zabbix_get.exe" -s localhost -k "zbx1cpy.clusters.discovery"
& "<ZABBIX_AGENT_DIR>\zabbix_get.exe" -s localhost -k "zbx1cpy.cluster.status[<cluster_id>]"
& "<ZABBIX_AGENT_DIR>\zabbix_get.exe" -s localhost -k "zbx1cpy.metrics[<cluster_id>]"

# Linux
zabbix_get -s localhost -k "zbx1cpy.clusters.discovery"
zabbix_get -s localhost -k "zbx1cpy.cluster.status[<cluster_id>]"
zabbix_get -s localhost -k "zbx1cpy.metrics[<cluster_id>]"
```

### UserParameter

Файл `userparameter_1c.conf` содержит (используются полные пути к Python):

```conf
# Windows (Zabbix Agent 2)
# Формат: cd /d "проект" && "python.exe" -m zbx_1c <command>
# cd /d обеспечивает корректную кодировку UTF-8

# LLD Discovery: обнаружение кластеров
UserParameter=zbx1cpy.clusters.discovery,cd /d "<PROJECT_DIR>" && "<PYTHON_EXE>" -m zbx_1c discovery

# Статус кластера (для Item Prototype)
UserParameter=zbx1cpy.cluster.status[*],cd /d "<PROJECT_DIR>" && "<PYTHON_EXE>" -m zbx_1c status $1

# Метрики кластера
UserParameter=zbx1cpy.metrics[*],cd /d "<PROJECT_DIR>" && "<PYTHON_EXE>" -m zbx_1c metrics $1

# Метрики всех кластеров (для Master Item)
UserParameter=zbx1cpy.metrics.all,cd /d "<PROJECT_DIR>" && "<PYTHON_EXE>" -m zbx_1c metrics

# Проверка RAS
UserParameter=zbx1cpy.ras.check,cd /d "<PROJECT_DIR>" && "<PYTHON_EXE>" -m zbx_1c check-ras
```

**Для Linux** используйте `zbx-1c-generate-userparam --force-os linux`:

```conf
# Linux (Zabbix Agent 2)
PYTHON_EXE=/opt/zbx-1c-py/.venv/bin/python
PROJECT_DIR=/opt/zbx-1c-py

# LLD Discovery
UserParameter=zbx1cpy.clusters.discovery,LANG=C.UTF-8 PYTHONIOENCODING=utf-8 cd "${PROJECT_DIR}" && "${PYTHON_EXE}" -m zbx_1c discovery

# Статус кластера
UserParameter=zbx1cpy.cluster.status[*],LANG=C.UTF-8 PYTHONIOENCODING=utf-8 cd "${PROJECT_DIR}" && "${PYTHON_EXE}" -m zbx_1c status $1

# Метрики кластера
UserParameter=zbx1cpy.metrics[*],LANG=C.UTF-8 PYTHONIOENCODING=utf-8 cd "${PROJECT_DIR}" && "${PYTHON_EXE}" -m zbx_1c metrics $1
```

**Автоматическая генерация:**

```bash
# Сгенерировать конфиг для текущей ОС
zbx-1c-generate-userparam

# Сгенерировать для Linux
zbx-1c-generate-userparam --force-os linux

# Свой путь вывода
zbx-1c-generate-userparam -o /etc/zabbix/zabbix_agent2.d/userparameter_1c.conf
```

**Важно:** 
- Windows: Используйте `cd /d` вместо `chcp 65001` для корректной кодировки
- Linux: Используйте `LANG=C.UTF-8 PYTHONIOENCODING=utf-8` для UTF-8 вывода

### Импорт шаблона Zabbix

1. Импортируйте шаблон из `zabbix/templates/template.xml`
2. Свяжите шаблон с хостом
3. Настройте макросы (при необходимости)

**Примечание:** Для автоматического обнаружения кластеров используйте LLD (Low Level Discovery) с ключом `zbx1cpy.clusters.discovery`.

---

## 🧪 Запуск тестов

**Вариант 1: Через uv (рекомендуется)**
```bash
# Все тесты
uv run pytest

# С покрытием
uv run pytest --cov=zbx_1c

# Конкретный тест
uv run pytest tests/test_basic.py -v

# С verbose выводом
uv run pytest -v
```

**Вариант 2: Через pytest**
```bash
# Все тесты
pytest

# С покрытием
pytest --cov=zbx_1c

# Конкретный тест
pytest tests/test_basic.py -v
```

---

## 📦 Сборка проекта

**Вариант 1: Через uv (рекомендуется)**
```bash
# Создание дистрибутива
uv build

# Сборка и публикация
uv build && uv publish
```

**Вариант 2: Через build**
```bash
# Создание дистрибутива
python -m build

# Или через uv
uv build
```

---

## 🔐 Проверка безопасности

**Вариант 1: Через uv (рекомендуется)**
```bash
# Аудит уязвимостей
uv run pip-audit

# Проверка кода
uv run ruff check src
uv run pyright src
```

**Вариант 2: Прямой запуск**
```bash
# Аудит уязвимостей
pip-audit

# Проверка кода
ruff check src
pyright src
```

---

## 📓 Мониторинг через техжурнал 1С

### 📖 Описание

Модуль мониторинга через техжурнал 1С предоставляет возможность сбора метрик из логов техжурнала 
и отправки их в Zabbix. Это позволяет отслеживать:

- **Ошибки (EXCP)** — критичные ошибки платформы 1С
- **Предупреждения (ATTN)** — предупреждения и заметки
- **Блокировки (TLOCK, TDEADLOCK, TTIMEOUT)** — длительные блокировки, deadlock'и, таймауты
- **Долгие вызовы (CALL)** — вызовы методов с длительностью >200 мс
- **Медленный SQL (SDBL, DBMSSQL)** — медленные SQL-запросы >80 мс
- **События кластера (CLSTR, ADMIN)** — события управления кластером

### 🔧 Настройка техжурнала 1С

1. **Скопируйте конфигурационный файл:**

   ```bash
   cp config/logcfg.xml /path/to/1c/config/
   ```

2. **Отредактируйте пути в logcfg.xml:**

   Замените переменные `{{LOG_BASE}}` и `{{LOG_ANALYTICS}}` на реальные пути:

   ```xml
   <!-- Windows -->
   <log location="C:/1c_log/core" history="24">
   
   <!-- Linux -->
   <log location="/var/log/1c/core" history="24">
   ```

   Или используйте переменные окружения для подстановки.

3. **Настройте сервер 1С:**

   - Откройте консоль администрирования 1С:Предприятия
   - Перейдите в свойства кластера
   - Укажите путь к `logcfg.xml`
   - Перезапустите службу 1С:Предприятия

4. **Проверьте создание логов:**

   Убедитесь, что в указанной директории создаются поддиректории:
   - `core/` — ошибки и события кластера
   - `perf/` — долгие вызовы
   - `locks/` — блокировки
   - `sql/` — медленные SQL-запросы
   - `zabbix/` — критичные события для мониторинга

### 📊 Сбор метрик

**Команды CLI:**

```bash
# Текстовая сводка
zbx-1c techjournal

# JSON для Zabbix
zbx-1c techjournal --json-output

# Сбор за 15 минут
zbx-1c techjournal --period 15
```

**Отправка в Zabbix:**

```bash
# Отправка метрик
zbx-1c techjournal send

# Dry-run (проверка без отправки)
zbx-1c techjournal send --dry-run
```

### ⚙️ Конфигурация (.env)

```env
# Путь к логам техжурнала
# Windows: TECHJOURNAL_LOG_BASE=C:/1c_log
# Linux:   TECHJOURNAL_LOG_BASE=/var/log/1c
TECHJOURNAL_LOG_BASE=<PATH_TO_LOGS>

# Путь к аналитическим логам
# Windows: TECHJOURNAL_LOG_ANALYTICS=C:/1c_log_analytics
# Linux:   TECHJOURNAL_LOG_ANALYTICS=/var/log/1c_analytics
TECHJOURNAL_LOG_ANALYTICS=<PATH_TO_ANALYTICS>

# Период сбора метрик (минуты)
TECHJOURNAL_PERIOD_MINUTES=5

# Zabbix
# Windows: ZABBIX_SERVER=127.0.0.1
# Linux:   ZABBIX_SERVER=zabbix.example.com
ZABBIX_SERVER=<ZABBIX_SERVER>
ZABBIX_PORT=10051

# Путь к утилите zabbix_sender (опционально)
# Windows: ZABBIX_SENDER_PATH=C:/Program Files/Zabbix Agent/zabbix_sender.exe
# Linux:   ZABBIX_SENDER_PATH=/usr/bin/zabbix_sender
# ZABBIX_SENDER_PATH=

ZABBIX_USE_API=false
```

### 📈 Метрики для Zabbix

| Ключ Zabbix | Описание |
|-------------|----------|
| `zbx1cpy.techjournal.total_events` | Всего событий |
| `zbx1cpy.techjournal.critical_events` | Критичные события |
| `zbx1cpy.techjournal.errors.count` | Ошибки |
| `zbx1cpy.techjournal.deadlocks.count` | Deadlock'и |
| `zbx1cpy.techjournal.timeouts.count` | Таймауты |
| `zbx1cpy.techjournal.long_locks.count` | Длительные блокировки |
| `zbx1cpy.techjournal.long_calls.count` | Долгие вызовы |
| `zbx1cpy.techjournal.slow_sql.count` | Медленный SQL |

### 📋 Пример UserParameter для Zabbix Agent

Готовый файл конфигурации: `zabbix/userparameters/userparameter_techjournal.conf`

```ini
# Linux: /etc/zabbix/zabbix_agentd.d/userparameter_techjournal.conf
# Windows: C:\Program Files\Zabbix Agent\zabbix_agentd.conf.d\userparameter_techjournal.conf

# Общее количество событий
UserParameter=zbx1cpy.techjournal.total,zbx-1c techjournal --json-output --period 5 | jq '.total_events // 0'

# Ошибки
UserParameter=zbx1cpy.techjournal.errors,zbx-1c techjournal --json-output --period 5 | jq '.["errors.count"] // 0'

# Deadlock'и
UserParameter=zbx1cpy.techjournal.deadlocks,zbx-1c techjournal --json-output --period 5 | jq '.["deadlocks.count"] // 0'

# Блокировки
UserParameter=zbx1cpy.techjournal.locks,zbx-1c techjournal --json-output --period 5 | jq '.["long_locks.count"] // 0'

# Долгие вызовы
UserParameter=zbx1cpy.techjournal.slowcalls,zbx-1c techjournal --json-output --period 5 | jq '.["long_calls.count"] // 0'

# Медленный SQL
UserParameter=zbx1cpy.techjournal.slowsql,zbx-1c techjournal --json-output --period 5 | jq '.["slow_sql.count"] // 0'

# С аргументом (период в минутах)
UserParameter=zbx1cpy.techjournal.total[*],zbx-1c techjournal --json-output --period $1 | jq '.total_events // 0'
```

---

## 📝 Лицензия

MIT License - см. файл [LICENSE](LICENSE)

---

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Add amazing feature'`)
4. Отправьте в репозиторий (`git push origin feature/amazing-feature`)
5. Создайте Pull Request

---

