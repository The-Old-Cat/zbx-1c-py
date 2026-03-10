# Настройка технического журнала 1С (logcfg.xml)

Этот документ описывает процесс настройки и развёртывания конфигурации технического журнала 1С для мониторинга через Zabbix.

## 📋 Обзор

Конфигурация `logcfg.xml` определяет, какие события сервер 1С должен записывать в технический журнал. В данном проекте используются **4 основных категории логов**:

| Категория | Путь | События | Назначение |
|-----------|------|---------|------------|
| **Ошибки** | `{{LOG_BASE}}\errors` | `EXCP`, `ATTN` | Мониторинг ошибок в Zabbix |
| **Блокировки** | `{{LOG_BASE}}\locks` | `TLOCK` (>200 мс), `TDEADLOCK`, `TTIMEOUT` | Алёрты на блокировки |
| **Долгие вызовы** | `{{LOG_BASE}}\slow_calls` | `CALL` (>2 сек) | Выявление проблем производительности |
| **Медленный SQL** | `{{LOG_BASE}}\slow_sql` | `SDBL` (>100 мс) | Оптимизация запросов |
| **Аналитика** | `{{LOG_ANALYTICS}}\errors_full` | `EXCP` (полный стек) | Отладка и расследование инцидентов |

---

## 🚀 Быстрый старт

### Шаг 1. Настройка переменных окружения

Скопируйте `.env.example` в `.env` и отредактируйте пути:

```ini
# Базовый путь для логов Zabbix
# Windows: 1C_LOG_BASE=C:/1c_log/zabbix
# Linux:   1C_LOG_BASE=/var/log/1c/zabbix
1C_LOG_BASE=<PATH_TO_LOGS>

# Путь для аналитических логов
# Windows: 1C_LOG_ANALYTICS=C:/1c_log/analytics
# Linux:   1C_LOG_ANALYTICS=/var/log/1c/analytics
1C_LOG_ANALYTICS=<PATH_TO_ANALYTICS>

# Путь к целевому logcfg.xml на сервере 1С
# Windows: 1C_LOGCFG_TARGET=C:/Program Files/1cv8/conf/logcfg.xml
# Linux:   1C_LOGCFG_TARGET=/etc/1c/1cv8/conf/logcfg.xml
1C_LOGCFG_TARGET=<PATH_TO_LOGCFG>

# Путь к шаблону (относительно проекта)
LOGCFG_TEMPLATE=config/logcfg.xml

```

### Шаг 2. Деплой конфигурации

```bash
# Установка зависимостей (если ещё не установлены)
uv sync

# Режим dry-run (проверка без записи)
uv run zbx-1c-deploy-logcfg --dry-run

# Обычный деплой (с бэкапом и созданием директорий)
uv run zbx-1c-deploy-logcfg

# Без бэкапа
uv run zbx-1c-deploy-logcfg --no-backup

# Без создания директорий (если уже созданы)
uv run zbx-1c-deploy-logcfg --no-create-dirs

# Свой шаблон
uv run zbx-1c-deploy-logcfg --template my-logcfg.xml
```

**После установки пакета** (`pip install -e .` или `uv sync`) можно запускать напрямую:

```bash
zbx-1c-deploy-logcfg --dry-run
```

**Важно:** Скрипт автоматически создаёт все директории для логов, указанные в шаблоне `logcfg.xml`. Если директории уже существуют, они не будут изменены.

### Шаг 3. Перезапуск сервера 1С

После копирования `logcfg.xml` **перезапустите службу сервера 1С**:

```powershell
# Windows
net stop "1C:Enterprise 8.3 Server Agent"
net start "1C:Enterprise 8.3 Server Agent"

# Linux (systemd)
sudo systemctl restart srv1cv83

# Linux (init.d)
sudo service srv1cv83 restart
```

### Шаг 4. Настройка ротации логов

Для автоматической очистки старых логов используйте скрипт `cleanup_logs`:

```bash
# Проверка (dry-run)
zbx-1c-cleanup-logs --dry-run --verbose

# Очистка логов старше 7 дней
zbx-1c-cleanup-logs

# Очистка с настройками (30 дней, макс. 500 МБ, 5 файлов)
zbx-1c-cleanup-logs --days 30 --max-size 500 --max-files 5
```

**Автоматизация:**

**Windows (Task Scheduler):**
```powershell
# Создать задачу на ежедневное выполнение в 03:00
schtasks /Create /TN "1C_TechLog_Cleanup" /TR "zbx-1c-cleanup-logs --days 7" /SC DAILY /ST 03:00 /RU SYSTEM
```

**Linux (cron):**
```bash
# Добавить в crontab (ежедневно в 03:00)
0 3 * * * /path/to/venv/bin/zbx-1c-cleanup-logs --days 7
```

### Шаг 5. Проверка

Убедитесь, что логи создаются:

```powershell
# Windows
dir C:\1c_log\zabbix\errors

# Linux
ls -la /var/log/1c/zabbix/errors/
```

---

## 📁 Структура файлов

```
<PROJECT_DIR>/
├── config/
│   └── logcfg.xml              # Шаблон конфигурации (в git)
├── scripts/
│   └── deploy_logcfg.py        # Скрипт деплоя
├── .env                        # Переменные окружения (в .gitignore)
├── .env.example                # Пример переменных
└── docs/
    └── logcfg-setup.md         # Эта инструкция
```

---

## 🔧 Детали конфигурации

### Команды скрипта

| Команда | Описание |
|---------|----------|
| `zbx-1c-deploy-logcfg` | Обычный деплой с бэкапом и созданием директорий |
| `zbx-1c-deploy-logcfg --dry-run` | Проверка без внесения изменений |
| `zbx-1c-deploy-logcfg --no-backup` | Деплой без бэкапа |
| `zbx-1c-deploy-logcfg --no-create-dirs` | Не создавать директории автоматически |
| `zbx-1c-deploy-logcfg --template X.xml` | Использовать свой шаблон |

### Пороги срабатывания

| Событие | Порог | Обоснование |
|---------|-------|-------------|
| Блокировки (TLOCK) | >200 мс | Оптимальный порог для продакшена |
| Долгие вызовы (CALL) | >2 сек | Проблемные операции |
| Медленный SQL (SDBL) | >100 мс | Статистика без текста запросов |

### История файлов

- **Zabbix-логи**: `history="2"` — хранятся 2 файла (экономия места)
- **Аналитика**: `history="24"` — хранятся 24 файла (для расследований)

### Отключённые опции

```xml
<dump create="false"/>                    <!-- Отключены автодампы -->
<query:plansql location=""/>              <!-- Отключены планы SQL -->
```

---

## 🛠️ Troubleshooting

### Логи не создаются

1. Проверьте права доступа к директориям логов
2. Убедитесь, что служба 1С запущена от пользователя с правами записи
3. Проверьте синтаксис `logcfg.xml`:
   ```bash
   zbx-1c-deploy-logcfg --dry-run
   ```

### Ошибка: "Permission denied"

**Windows:**
```powershell
# Запуск от имени администратора
zbx-1c-deploy-logcfg
```

**Linux:**
```bash
sudo chown -R usr1cv8:grp1cv8 /var/log/1c
sudo chmod -R 755 /var/log/1c
```

### Рассинхронизация шаблона и сервера

Если на сервере вручную изменили `logcfg.xml`:

```bash
# Принудительный деплой шаблона
zbx-1c-deploy-logcfg --no-backup
```

---

## 📊 Интеграция с Zabbix

После настройки журнала используйте скрипты чтения логов для отправки данных в Zabbix:

```bash
# Ошибки за последние 5 минут
zbx-1c-log-errors --count

# Блокировки за последние 5 минут
zbx-1c-log-locks --count

# Долгие вызовы
zbx-1c-log-slow-calls --count

# Медленный SQL
zbx-1c-log-slow-sql --count
```

### UserParameter для Zabbix Agent

```ini
# /etc/zabbix/zabbix_agentd.d/userparameter_1c_log.conf
UserParameter=1c.log.errors.count,zbx-1c-log-errors --count --minutes 5
UserParameter=1c.log.locks.count,zbx-1c-log-locks --count --minutes 5
UserParameter=1c.log.slow_calls.count,zbx-1c-log-slow-calls --count --minutes 5
UserParameter=1c.log.slow_sql.count,zbx-1c-log-slow-sql --count --minutes 5

# Получение данных в JSON (для отладки)
UserParameter=1c.log.errors.json,zbx-1c-log-errors --format json --minutes 5
UserParameter=1c.log.locks.json,zbx-1c-log-locks --format json --minutes 5
```

### Ключи для Zabbix

| Ключ | Описание |
|------|----------|
| `1c.log.errors.count` | Количество ошибок за период |
| `1c.log.locks.count` | Количество блокировок за период |
| `1c.log.slow_calls.count` | Количество долгих вызовов за период |
| `1c.log.slow_sql.count` | Количество медленных SQL за период |

---

## 📝 Примечания

1. **Не храните `descr` в Zabbix-логах** — слишком большой объём данных
2. **Используйте аналитические логи** для расследования инцидентов
3. **Регулярно очищайте старые логи** (скрипт `cleanup_logs.py`)
4. **Тестируйте изменения** на staging перед продакшеном

---

## 🔗 См. также

- [Официальная документация 1С: Технический журнал](https://its.1c.ru/db/v8std/content/686)
- [Настройка мониторинга Zabbix](zabbix-setup.md)
- [Скрипты чтения логов](read-logs.md)
