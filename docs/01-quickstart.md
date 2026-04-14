# Быстрый старт zbx-1c-py

## 📋 Требования

- Python 3.10+
- 1С:Предприятие 8.3+ (сервер с настроенным техжурналом)
- Zabbix Agent (опционально)

---

## 🚀 Установка

### Мониторинг через техжурнал

```bash
# Перейдите в директорию пакета
cd packages/zbx-1c-techlog

# Установите пакет
pip install -e .

# Скопируйте пример конфигурации
cp ../../.env.techlog.example ../../.env.techlog

# Отредактируйте .env.techlog
# TECHJOURNAL_LOG_BASE, LOG_PATH

# Проверьте логи
zbx-1c-techlog check
```

**Проверка:**
```bash
zbx-1c-techlog --help
zbx-1c-techlog collect --period 5
```

---

## ⚙️ Настройка конфигурации

### Для zbx-1c-techlog

**Файл:** `.env.techlog`

```env
# Путь к техжурналу 1С
TECHJOURNAL_LOG_BASE=C:/1c_log
TECHJOURNAL_LOG_ANALYTICS=C:/1c_log_analytics

# Логи самого мониторинга
LOG_PATH=./logs

# Zabbix (опционально)
ZABBIX_SERVER=127.0.0.1
ZABBIX_PORT=10051

# Период сбора метрик (минуты)
TECHJOURNAL_PERIOD_MINUTES=5
```

---

## 🔍 Проверка работы

### Тестирование zbx-1c-techlog

```bash
# Проверка доступности логов
zbx-1c-techlog check

# Сбор метрик за 5 минут
zbx-1c-techlog collect --period 5

# Сбор метрик в JSON
zbx-1c-techlog collect --period 5 --json-output

# Текстовая сводка
zbx-1c-techlog summary
```

---

## 📊 Интеграция с Zabbix

### 1. Генерация UserParameter

```bash
python -m zbx_1c_techlog.cli.generate_userparam
```

### 2. Копирование конфига

**Windows:**
```powershell
Copy-Item "zabbix/userparameters/userparameter_techjournal.conf" `
    "C:\Program Files\Zabbix Agent\zabbix_agentd.d\" -Force
```

**Linux:**
```bash
sudo cp zabbix/userparameters/userparameter_techjournal.conf \
        /etc/zabbix/zabbix_agentd.d/
```

### 3. Перезапуск агента

**Windows:**
```powershell
net stop "Zabbix Agent" && net start "Zabbix Agent"
```

**Linux:**
```bash
sudo systemctl restart zabbix-agent
```

### 4. Проверка

```bash
zabbix_get -s localhost -k z1c.techjournal.collect
```

---

## 📚 Полная документация

- **[02-deployment.md](02-deployment.md)** — Полное руководство по развёртыванию
- **[02-zbx-1c-techlog.md](02-zbx-1c-techlog.md)** — Документация по техжурналу
- **[04-logcfg-setup.md](04-logcfg-setup.md)** — Настройка техжурнала 1С

---

## ❓ FAQ

### Где хранятся логи?

По умолчанию: `./logs/`

Путь настраивается в `.env.techlog`.

### Как обновить пакет?

```bash
pip install -e ./packages/zbx-1c-techlog --upgrade
```

### Как отладить проблемы с техжурналом?

```bash
# Проверьте наличие логов
zbx-1c-techlog check

# Запустите с отладкой
zbx-1c-techlog collect --period 5 --debug
```
