# Развертывание пакетов zbx-1c-rac и zbx-1c-techlog

## 📦 Обзор архитектуры

Проект разделен на **два независимых пакета**:

| Пакет | Назначение | Зависимости |
|-------|------------|-------------|
| **zbx-1c-rac** | Мониторинг через RAC (сессии, задания, кластеры) | ~5 пакетов |
| **zbx-1c-techlog** | Мониторинг через техжурнал 1С (ошибки, блокировки, SQL) | ~4 пакета |

### Преимущества разделения

✅ **Независимое развертывание** — устанавливайте только нужный пакет  
✅ **Минимум зависимостей** — никаких лишних пакетов  
✅ **Разные конфигурации** — `.env.rac` и `.env.techlog` не конфликтуют  
✅ **Гибкость** — можно использовать оба пакета вместе или по отдельности

---

## 🚀 Установка

### Вариант 1: Только мониторинг RAC

```bash
# Перейдите в директорию пакета
cd packages/zbx-1c-rac

# Установите пакет
pip install -e .

# Или через uv
uv pip install -e .
```

**Проверка установки:**
```bash
zbx-1c-rac --help
zbx-1c-rac check-config
```

---

### Вариант 2: Только мониторинг техжурнала

```bash
# Перейдите в директорию пакета
cd packages/zbx-1c-techlog

# Установите пакет
pip install -e .

# Или через uv
uv pip install -e .
```

**Проверка установки:**
```bash
zbx-1c-techlog --help
zbx-1c-techlog check
```

---

### Вариант 3: Оба пакета вместе

```bash
# Установите оба пакета
pip install -e ./packages/zbx-1c-rac -e ./packages/zbx-1c-techlog

# Или через uv
uv pip install -e ./packages/zbx-1c-rac -e ./packages/zbx-1c-techlog
```

**Проверка установки:**
```bash
zbx-1c-rac --help
zbx-1c-techlog --help
```

---

## ⚙️ Настройка конфигурации

### Для zbx-1c-rac

1. **Скопируйте пример конфигурации:**
   ```bash
   cp .env.rac.example .env.rac
   ```

2. **Отредактируйте `.env.rac`:**
   ```env
   # Путь к rac (укажите вашу версию 1С)
   RAC_PATH=C:/Program Files/1cv8/8.3.27.1786/bin/rac.exe

   # RAS сервис
   RAC_HOST=127.0.0.1
   RAC_PORT=1545

   # Аутентификация (если требуется)
   USER_NAME=admin
   USER_PASS=password

   # Логи
   LOG_PATH=G:/Automation/zbx-1c-py/logs/rac
   ```

3. **Проверьте конфигурацию:**
   ```bash
   zbx-1c-rac check-config
   ```

---

### Для zbx-1c-techlog

1. **Скопируйте пример конфигурации:**
   ```bash
   cp .env.techlog.example .env.techlog
   ```

2. **Отредактируйте `.env.techlog`:**
   ```env
   # Путь к техжурналу 1С
   TECHJOURNAL_LOG_BASE=C:/1c_log

   # Логи самого мониторинга
   LOG_PATH=G:/Automation/zbx-1c-py/logs/techlog

   # Zabbix (опционально)
   ZABBIX_SERVER=127.0.0.1
   ZABBIX_PORT=10051
   ```

3. **Проверьте логи:**
   ```bash
   zbx-1c-techlog check
   ```

---

## 📋 Доступные команды

### zbx-1c-rac

| Команда | Описание |
|---------|----------|
| `zbx-1c-rac check` | Проверка доступности RAS |
| `zbx-1c-rac check-config` | Проверка конфигурации |
| `zbx-1c-rac discovery` | Обнаружение кластеров (LLD для Zabbix) |
| `zbx-1c-rac clusters` | Список кластеров |
| `zbx-1c-rac metrics [cluster_id]` | Метрики кластера |
| `zbx-1c-rac status <cluster_id>` | Статус кластера |
| `zbx-1c-rac infobases <cluster_id>` | Информационные базы |
| `zbx-1c-rac sessions <cluster_id>` | Сессии кластера |
| `zbx-1c-rac jobs <cluster_id>` | Фоновые задания |
| `zbx-1c-rac test` | Тестирование подключения |

**Примеры:**
```bash
# Проверка RAS
zbx-1c-rac check

# Обнаружение кластеров для Zabbix
zbx-1c-rac discovery

# Метрики конкретного кластера
zbx-1c-rac metrics abc123-def456-ghi789

# Все команды с --help
zbx-1c-rac <command> --help
```

---

### zbx-1c-techlog

| Команда | Описание |
|---------|----------|
| `zbx-1c-techlog collect` | Сбор метрик из техжурнала |
| `zbx-1c-techlog send` | Отправка метрик в Zabbix |
| `zbx-1c-techlog summary` | Текстовая сводка |
| `zbx-1c-techlog check` | Проверка доступности логов |

**Примеры:**
```bash
# Сбор метрик за 5 минут
zbx-1c-techlog collect --period 5

# Сбор метрик в JSON для Zabbix
zbx-1c-techlog collect --period 5 --json-output

# Отправка в Zabbix
zbx-1c-techlog send --period 5

# Проверка логов
zbx-1c-techlog check
```

---

## 🔗 Интеграция с Zabbix

### Для zbx-1c-rac

**UserParameter в zabbix_agentd.conf:**
```ini
# Обнаружение кластеров
UserParameter=zbx1cpy.rac.discovery,zbx-1c-rac discovery

# Метрики кластера
UserParameter=zbx1cpy.rac.metrics[*],zbx-1c-rac metrics $1

# Статус кластера
UserParameter=zbx1cpy.rac.status[*],zbx-1c-rac status $1

# Проверка RAS
UserParameter=zbx1cpy.rac.check,zbx-1c-rac check
```

---

### Для zbx-1c-techlog

**UserParameter в zabbix_agentd.conf:**
```ini
# Сбор метрик техжурнала
UserParameter=zbx1cpy.techjournal.collect,zbx-1c-techlog collect --json-output

# Отправка через zabbix_sender (внешняя проверка)
# Настраивается как External Check в Zabbix
```

**Внешняя проверка (External Check):**
```bash
# Скрипт для отправки в Zabbix
zbx-1c-techlog send --period 5
```

---

## 🗂 Структура проекта

```
g:\Automation\zbx-1c-py\
├── packages/
│   ├── zbx-1c-rac/              # Пакет мониторинга через RAC
│   │   ├── pyproject.toml       # Зависимости и настройки
│   │   └── src/zbx_1c_rac/
│   │       ├── cli/             # CLI команды
│   │       ├── core/            # Конфигурация
│   │       ├── monitoring/      # Мониторинг (сессии, задания)
│   │       └── utils/           # Утилиты (rac_client, converters)
│   │
│   └── zbx-1c-techlog/          # Пакет мониторинга техжурнала
│       ├── pyproject.toml       # Зависимости и настройки
│       └── src/zbx_1c_techlog/
│           ├── cli/             # CLI команды
│           ├── core/            # Конфигурация
│           └── reader/          # Парсинг и сбор метрик
│
├── shared/                      # Общие утилиты
│   ├── core/
│   │   ├── logging.py           # Логирование
│   │   └── config.py            # Базовая конфигурация
│   └── zabbix/
│       └── sender.py            # Отправка в Zabbix
│
├── .env.rac.example             # Пример конфигурации RAC
├── .env.techlog.example         # Пример конфигурации техжурнала
└── README.md
```

---

## 🔧 Разработка

### Добавление зависимостей

**Для zbx-1c-rac:**
```toml
# packages/zbx-1c-rac/pyproject.toml
[project]
dependencies = [
    "loguru>=0.7.2",
    "pydantic>=2.6.0",
    # Добавьте вашу зависимость
]
```

**Для zbx-1c-techlog:**
```toml
# packages/zbx-1c-techlog/pyproject.toml
[project]
dependencies = [
    "loguru>=0.7.2",
    "pydantic>=2.6.0",
    # Добавьте вашу зависимость
]
```

### Запуск без установки

```bash
# Через uv run
uv run --package zbx-1c-rac zbx-1c-rac check
uv run --package zbx-1c-techlog zbx-1c-techlog check
```

---

## ❓ FAQ

### Можно ли использовать оба пакета вместе?

Да! Установите оба пакета:
```bash
pip install -e ./packages/zbx-1c-rac -e ./packages/zbx-1c-techlog
```

Конфигурации разделены (`.env.rac` и `.env.techlog`), поэтому конфликтов не будет.

### Как обновить пакеты?

```bash
# Через pip
pip install -e ./packages/zbx-1c-rac --upgrade
pip install -e ./packages/zbx-1c-techlog --upgrade

# Через uv
uv pip install -e ./packages/zbx-1c-rac --upgrade
uv pip install -e ./packages/zbx-1c-techlog --upgrade
```

### Где хранятся логи?

По умолчанию:
- **zbx-1c-rac**: `logs/rac/`
- **zbx-1c-techlog**: `logs/techlog/`

Пути настраиваются в соответствующих `.env` файлах.

### Что делать если rac не найден?

Убедитесь, что:
1. 1С установлена на сервере
2. Путь `RAC_PATH` указан верно в `.env.rac`
3. У пользователя есть права на выполнение rac

### Как отладить проблемы с техжурналом?

```bash
# Проверьте наличие логов
zbx-1c-techlog check

# Запустите с отладкой
zbx-1c-techlog collect --period 5 --debug
```

---

## 📞 Поддержка

Вопросы и предложения направляйте на:
- Email: ar-kovale@yandex.ru
- GitHub Issues: https://github.com/your-repo/zbx-1c/issues
