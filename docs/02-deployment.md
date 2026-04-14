# Развертывание пакета zbx-1c-techlog

## 📦 Обзор

Пакет **zbx-1c-techlog** для мониторинга 1С:Предприятия через техжурнал в системе Zabbix.

| Пакет | Назначение | Зависимости |
|-------|------------|-------------|
| **zbx-1c-techlog** | Мониторинг через техжурнал 1С (ошибки, блокировки, SQL) | ~4 пакета |

### Преимущества

✅ **Минимум зависимостей** — только необходимые пакеты
✅ **Простая конфигурация** — `.env.techlog` для всех настроек
✅ **Гибкость** — мониторинг ошибок, блокировок, медленного SQL

---

## 🚀 Установка

### Мониторинг техжурнала

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

## ⚙️ Настройка конфигурации

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
│   └── zbx-1c-techlog/          # Пакет мониторинга техжурнала
│       ├── pyproject.toml       # Зависимости и настройки
│       ├── README.md            # Документация пакета
│       ├── tests/               # Тесты пакета
│       └── src/zbx_1c_techlog/
│           ├── cli/             # CLI команды
│           ├── core/            # Конфигурация
│           └── reader/          # Парсинг и сбор метрик
│
├── scripts/                     # Скрипты CI/CD и разработки
│   ├── ci/                      # CI/CD скрипты (build, test)
│   ├── deploy/                  # Скрипты развёртывания
│   └── dev/                     # Скрипты для разработки
│
├── zabbix/                      # Интеграция с Zabbix
│   └── userparameters/          # UserParameter для Zabbix Agent
├── docs/                        # Документация
├── logs/                        # Логи (создаётся автоматически)
├── config/                      # Конфигурация 1С (logcfg.xml)
├── .env.example                 # Общий пример конфигурации
├── .env.techlog.example         # Пример конфигурации техжурнала
└── README.md
```

---

## 🔧 Разработка

### Добавление зависимостей

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
uv run --package zbx-1c-techlog zbx-1c-techlog check
```

---

## ❓ FAQ

### Как обновить пакет?

```bash
# Через pip
pip install -e ./packages/zbx-1c-techlog --upgrade

# Через uv
uv pip install -e ./packages/zbx-1c-techlog --upgrade
```

### Где хранятся логи?

По умолчанию: `logs/techlog/`

Путь настраивается в `.env.techlog`.

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
