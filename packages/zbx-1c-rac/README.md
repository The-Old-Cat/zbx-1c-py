# zbx-1c-rac

Мониторинг 1С:Предприятия через RAC (Remote Administration Console) для системы мониторинга Zabbix.

## Возможности

- ✅ Автоматическое обнаружение кластеров 1С (LLD)
- ✅ Сбор метрик сессий и фоновых заданий
- ✅ Мониторинг информационных баз
- ✅ Проверка доступности RAS (Remote Administration Service)
- ✅ Поддержка аутентификации в кластере 1С
- ✅ Кроссплатформенность (Windows, Linux, macOS)

## Установка

```bash
pip install -e .
```

## Быстрый старт

1. **Скопируйте конфигурацию:**
   ```bash
   cp ../../.env.rac.example ../../.env.rac
   ```

2. **Настройте `.env.rac`:**
   ```env
   RAC_PATH=C:/Program Files/1cv8/8.3.27.1786/bin/rac.exe
   RAC_HOST=127.0.0.1
   RAC_PORT=1545
   USER_NAME=admin
   USER_PASS=password
   ```

3. **Проверьте подключение:**
   ```bash
   zbx-1c-rac check-config
   ```

## Команды

| Команда | Описание |
|---------|----------|
| `zbx-1c-rac check` | Проверка доступности RAS |
| `zbx-1c-rac check-config` | Проверка конфигурации |
| `zbx-1c-rac discovery` | Обнаружение кластеров (LLD) |
| `zbx-1c-rac clusters` | Список кластеров |
| `zbx-1c-rac metrics [cluster_id]` | Метрики кластера |
| `zbx-1c-rac status <cluster_id>` | Статус кластера |
| `zbx-1c-rac test` | Тестирование подключения |

## Документация

Полная документация: [DEPLOYMENT.md](../DEPLOYMENT.md)
