# zbx-1c-py

Кроссплатформенный инструмент для интеграции 1С:Предприятия с системой мониторинга Zabbix.

## 📚 Документация

**Вся документация в [`docs/`](docs/) с единой нумерацией:**

| № | Документ | Описание |
|---|----------|----------|
| 01 | [docs/01-quickstart.md](docs/01-quickstart.md) | Быстрый старт |
| 02 | [docs/02-deployment.md](docs/02-deployment.md) | Развёртывание |

**Полный список:** [docs/README.md](docs/README.md)

---

Проект предоставляет инструменты для интеграции 1С:Предприятия с системой мониторинга Zabbix.

---

## 🚀 Быстрый старт

### Мониторинг через техжурнал

```bash
cd packages/zbx-1c-techlog
pip install -e .
cp ../../.env.techlog.example ../../.env.techlog
zbx-1c-techlog check
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
- Сервер 1С:Предприятие с настроенным техжурналом

### Установка зависимостей

**Вариант 1: Через uv (рекомендуется)**

```bash
# Синхронизация зависимостей и установка пакета
uv sync

# Или только установка пакета без sync
uv pip install -e .

# Запуск без установки (разработка)
uv run zbx-1c techjournal
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
# ===========================================
# ЕДИНЫЙ КОНФИГ — все компоненты
# ===========================================

# Пути к логам техжурнала 1С
TECHJOURNAL_LOG_BASE=C:/1c_log
TECHJOURNAL_LOG_ANALYTICS=C:/1c_log_analytics

# Период сбора метрик (минуты)
TECHJOURNAL_PERIOD_MINUTES=5

# Сервер 1С
SERVER_1C_HOST=localhost
SERVER_1C_PORT=1545

# Zabbix
ZABBIX_SERVER=127.0.0.1
ZABBIX_PORT=10051

# Публикация 1С
PUBLISH_MODE=FULL
PUBLISH_ROOT=/htdocs
TECH_SUFFIX=_mg

# Apache
APACHE_VERSION=2.4.66
APACHE_INSTALL_PATH_WIN=C:/Apache24
APACHE_INSTALL_PATH_LINUX=/etc/apache2

# Логи
LOG_LEVEL=INFO
LOG_PATH=./logs
DEBUG=False
```

---

## ▶️ Использование

### CLI команды

#### Способы запуска

После установки `pip install -e .` доступны способы запуска CLI:

**1. Как Python-модуль:**

```bash
python -m zbx_1c techjournal [options]
```

**2. Через uv (для разработки и тестирования):**

```bash
# Текстовая сводка
uv run zbx-1c techjournal

# JSON вывод
uv run zbx-1c techjournal --json-output

# Сбор метрик за 15 минут
uv run zbx-1c techjournal --period 15

# С указанием конфигурации
uv run zbx-1c techjournal --config /path/to/.env
```

---

### 📋 Справочник команд

#### Общая информация

| Команда | Описание | Аргументы |
|---------|----------|-----------|
| `techjournal` | Мониторинг техжурнала 1С (ошибки, блокировки, долгие вызовы, медленный SQL) | — |
| `check-config` | Проверка корректности конфигурации | — |

---

### 🔍 Подробное описание команд

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

#### `check-config` — Проверка корректности конфигурации

Выполняет полную проверку конфигурации проекта: пути к логам техжурнала, права на запись.

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
# Путь к логам техжурнала 1С
TECHJOURNAL_LOG_BASE=C:/1c_log
TECHJOURNAL_LOG_ANALYTICS=C:/1c_log_analytics

# Период сбора метрик (минуты)
TECHJOURNAL_PERIOD_MINUTES=5

# Zabbix сервер
ZABBIX_SERVER=127.0.0.1
ZABBIX_PORT=10051

# Уровень логирования
LOG_LEVEL=INFO
LOG_PATH=./logs

# Режим отладки
DEBUG=False
```

**Переменные окружения:**

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `TECHJOURNAL_LOG_BASE` | Путь к логам техжурнала 1С | — |
| `TECHJOURNAL_LOG_ANALYTICS` | Путь к аналитическим логам | — |
| `TECHJOURNAL_PERIOD_MINUTES` | Период сбора метрик (минуты) | `5` |
| `SERVER_1C_HOST` | Адрес сервера 1С | `localhost` |
| `SERVER_1C_PORT` | Порт сервера 1С | `1545` |
| `PUBLISH_MODE` | Режим публикации (FULL/THIN) | `FULL` |
| `PUBLISH_ROOT` | Корневая директория публикации | `/htdocs` |
| `TECH_SUFFIX` | Суффикс для технических имён | `_mg` |
| `ZABBIX_SERVER` | Адрес Zabbix сервера | `127.0.0.1` |
| `ZABBIX_PORT` | Порт Zabbix сервера | `10051` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `LOG_PATH` | Путь к логам | `./logs` |
| `DEBUG` | Режим отладки | `False` |

---

### 💡 Примеры использования

#### Быстрая диагностика

```bash
# Проверка конфигурации
zbx-1c check-config

# Сбор метрик техжурнала
uv run zbx-1c techjournal
uv run zbx-1c techjournal --json-output
```

#### Мониторинг техжурнала

```bash
# Текстовая сводка
zbx-1c techjournal

# JSON вывод для Zabbix
zbx-1c techjournal --json-output

# Сбор метрик за 15 минут
zbx-1c techjournal --period 15

# С указанием конфигурации
zbx-1c techjournal --config .env.prod
```

#### Интеграция со скриптами

```bash
# Получить количество ошибок (для bash)
ERRORS=$(zbx-1c techjournal --json-output --period 5 | jq '.["errors.count"] // 0')

# Через uv
ERRORS=$(uv run zbx-1c techjournal --json-output --period 5 | jq '.["errors.count"] // 0')
```

---

### 🐛 Отладка

Для включения подробного логирования установите в `.env`:

```env
DEBUG=True
LOG_LEVEL=DEBUG
```

Логи будут записаны в директорию, указанную в `LOG_PATH` (по умолчанию `./logs`).

---

## 📊 Собираемые метрики (техжурнал)

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

# Таймаут выполнения проверок (увеличить для скриптов)
Timeout=30

# Разрешить выполнение команд
AllowKey=system.run[*]

# Директория для дополнительных конфигов (включая userparameter_techjournal.conf)
Include=C:\Program Files\Zabbix Agent\zabbix_agentd.d
```

**Рекомендуемые настройки:**

| Параметр | Значение | Описание |
|----------|----------|----------|
| `Timeout` | `30` | Увеличенный таймаут для выполнения скриптов |
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

#### 2. Копирование файла конфигурации

**Windows (от администратора):**
```powershell
Copy-Item "zabbix\userparameters\userparameter_techjournal.conf" `
    -Destination "C:\Program Files\Zabbix Agent 2\zabbix_agent2.d\" -Force
```

**Linux:**
```bash
sudo cp zabbix/userparameters/userparameter_techjournal.conf /etc/zabbix/zabbix_agentd.d/
```

> **Важно:** Отредактируйте пути к Python и проекту в файле конфигурации под вашу среду!

#### 3. Перезапуск Zabbix Agent

**Windows:**
```powershell
Restart-Service "Zabbix Agent 2"
```

**Linux:**
```bash
sudo systemctl restart zabbix-agent
```

#### 4. Проверка

```bash
# Windows
& "<ZABBIX_AGENT_DIR>\zabbix_get.exe" -s localhost -k "zbx1cpy.techjournal.total"

# Linux
zabbix_get -s localhost -k "zbx1cpy.techjournal.total"
```

### UserParameter

Файл `userparameter_techjournal.conf` содержит:

```conf
# Windows (Zabbix Agent 2)
# Формат: cd /d "проект" && "python.exe" -m zbx_1c <command>

# Общее количество событий
UserParameter=zbx1cpy.techjournal.total,cd /d "<PROJECT_DIR>" && "<PYTHON_EXE>" -m zbx_1c techjournal --json-output --period 5 | jq '.total_events // 0'

# Ошибки
UserParameter=zbx1cpy.techjournal.errors,cd /d "<PROJECT_DIR>" && "<PYTHON_EXE>" -m zbx_1c techjournal --json-output --period 5 | jq '.["errors.count"] // 0'

# Deadlock'и
UserParameter=zbx1cpy.techjournal.deadlocks,cd /d "<PROJECT_DIR>" && "<PYTHON_EXE>" -m zbx_1c techjournal --json-output --period 5 | jq '.["deadlocks.count"] // 0'

# Блокировки
UserParameter=zbx1cpy.techjournal.locks,cd /d "<PROJECT_DIR>" && "<PYTHON_EXE>" -m zbx_1c techjournal --json-output --period 5 | jq '.["long_locks.count"] // 0'

# Долгие вызовы
UserParameter=zbx1cpy.techjournal.slowcalls,cd /d "<PROJECT_DIR>" && "<PYTHON_EXE>" -m zbx_1c techjournal --json-output --period 5 | jq '.["long_calls.count"] // 0'

# Медленный SQL
UserParameter=zbx1cpy.techjournal.slowsql,cd /d "<PROJECT_DIR>" && "<PYTHON_EXE>" -m zbx_1c techjournal --json-output --period 5 | jq '.["slow_sql.count"] // 0'
```

**Для Linux** используйте префикс `LANG=C.UTF-8 PYTHONIOENCODING=utf-8`:

```conf
# Linux (Zabbix Agent 2)
PYTHON_EXE=/opt/zbx-1c-py/.venv/bin/python
PROJECT_DIR=/opt/zbx-1c-py

# Общее количество событий
UserParameter=zbx1cpy.techjournal.total,LANG=C.UTF-8 PYTHONIOENCODING=utf-8 cd "${PROJECT_DIR}" && "${PYTHON_EXE}" -m zbx_1c techjournal --json-output --period 5 | jq '.total_events // 0'
```

**Важно:**
- Windows: Используйте `cd /d` вместо `chcp 65001` для корректной кодировки
- Linux: Используйте `LANG=C.UTF-8 PYTHONIOENCODING=utf-8` для UTF-8 вывода

### Импорт шаблона Zabbix

1. Импортируйте шаблон из `zabbix/templates/template.xml`
2. Свяжите шаблон с хостом
3. Настройте макросы (при необходимости)

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
