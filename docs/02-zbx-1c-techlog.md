# zbx-1c-techlog

Мониторинг 1С:Предприятия через техжурнал для системы мониторинга Zabbix.

## Возможности

- ✅ Сбор метрик из техжурнала 1С
- ✅ Мониторинг ошибок и предупреждений
- ✅ Отслеживание блокировок и deadlock
- ✅ Мониторинг длительных вызовов и медленного SQL
- ✅ Отправка метрик в Zabbix через zabbix_sender или API
- ✅ Кроссплатформенность (Windows, Linux, macOS)

## Установка

```bash
pip install -e .
```

## Быстрый старт

1. **Скопируйте конфигурацию:**
   ```bash
   cp ../../.env.techlog.example ../../.env.techlog
   ```

2. **Настройте `.env.techlog`:**
   ```env
   TECHJOURNAL_LOG_BASE=C:/1c_log
   LOG_PATH=G:/Automation/zbx-1c-py/logs/techlog
   ZABBIX_SERVER=127.0.0.1
   ZABBIX_PORT=10051
   ```

3. **Проверьте логи:**
   ```bash
   zbx-1c-techlog check
   ```

## Команды

| Команда | Описание |
|---------|----------|
| `zbx-1c-techlog collect` | Сбор метрик из техжурнала |
| `zbx-1c-techlog send` | Отправка метрик в Zabbix |
| `zbx-1c-techlog summary` | Текстовая сводка |
| `zbx-1c-techlog check` | Проверка доступности логов |

## Примеры

```bash
# Сбор метрик за 5 минут в JSON
zbx-1c-techlog collect --period 5 --json-output

# Отправка в Zabbix
zbx-1c-techlog send --period 5

# Текстовая сводка
zbx-1c-techlog summary --period 15
```

## Структура логов 1С

Техжурнал должен содержать следующие поддиректории:

```
C:/1c_log/
├── core/      # Ошибки и предупреждения
├── perf/      # Долгие вызовы (>200 мс)
├── locks/     # Блокировки (>500 мс), deadlock, timeout
├── sql/       # Медленные SQL-запросы (>80 мс)
└── zabbix/    # Критичные события для Zabbix
```

## Документация

Полная документация: [DEPLOYMENT.md](../DEPLOYMENT.md)
