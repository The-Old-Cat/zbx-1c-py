# Быстрый старт zbx-1c-py

## 📋 Требования

- Python 3.10+
- 1С:Предприятие 8.3+ (сервер)
- Zabbix Agent 

---

## 🚀 Установка

### Вариант 1: Мониторинг через RAC

```bash
# Перейдите в директорию пакета
cd packages/zbx-1c-rac

# Установите пакет
pip install -e .

# Скопируйте пример конфигурации
cp ../../.env.rac.example ../../.env.rac

# Отредактируйте .env.rac
# RAC_PATH, RAC_HOST, RAC_PORT

# Проверьте конфигурацию
zbx-1c-rac check-config
```

**Проверка:**
```bash
zbx-1c-rac --help
zbx-1c-rac discovery
```

---

### Вариант 2: Мониторинг через техжурнал

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

### Вариант 3: Оба пакета вместе

```bash
# Установите оба пакета
pip install -e ./packages/zbx-1c-rac -e ./packages/zbx-1c-techlog

# Проверка
zbx-1c-rac --help
zbx-1c-techlog --help
```

---

## ⚙️ Настройка конфигурации

### Для zbx-1c-rac

**Файл:** `.env.rac`

```env
# Путь к rac (укажите вашу версию 1С)
RAC_PATH=C:/Program Files/1cv8/8.3.27.1786/bin/rac.exe

# RAS сервис
RAC_HOST=127.0.0.1
RAC_PORT=1545

# Аутентификация администратора кластера (если требуется)
USER_NAME=admin
USER_PASS=password

# Логи (автоматически выбирается стандартная директория)
# LOG_PATH=/var/log/zbx-1c-rac/  # Linux
# LOG_PATH=%APPDATA%/zbx-1c-rac/logs/  # Windows
```

### Для zbx-1c-techlog

**Файл:** `.env.techlog`

```env
# Путь к техжурналу 1С
TECHJOURNAL_LOG_BASE=C:/1c_log

# Логи самого мониторинга
# LOG_PATH=/var/log/zbx-1c-techlog/  # Linux
# LOG_PATH=%APPDATA%/zbx-1c-techlog/logs/  # Windows
```

---

## 🔍 Проверка работы

### Тестирование zbx-1c-rac

```bash
# Проверка конфигурации
zbx-1c-rac check-config

# Проверка доступности RAS
zbx-1c-rac check

# Обнаружение кластеров
zbx-1c-rac discovery

# Список кластеров
zbx-1c-rac clusters

# Метрики кластера
zbx-1c-rac metrics <cluster_id>
```

### Тестирование zbx-1c-techlog

```bash
# Проверка доступности логов
zbx-1c-techlog check

# Сбор метрик за 5 минут
zbx-1c-techlog collect --period 5

# Сбор метрик в JSON
zbx-1c-techlog collect --period 5 --json-output
```

---

## 📊 Интеграция с Zabbix

### 1. Генерация UserParameter

```bash
# Для zbx-1c-rac
python -m zbx_1c_rac.cli.generate_userparam

# Для zbx-1c-techlog
python -m zbx_1c_techlog.cli.generate_userparam
```

### 2. Копирование конфига

**Windows:**
```powershell
Copy-Item "zabbix/userparameters/userparameter_rac.conf" `
    "C:\Program Files\Zabbix Agent\zabbix_agentd.d\" -Force
```

**Linux:**
```bash
sudo cp zabbix/userparameters/userparameter_rac.conf \
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
zabbix_get -s localhost -k z1c.rac.discovery
zabbix_get -s localhost -k z1c.rac.check
```

---

## 📚 Полная документация

- **[deployment.md](deployment.md)** — Полное руководство по развёртыванию
- **[zabbix-integration.md](zabbix-integration.md)** — Интеграция с Zabbix
- **[zbx-1c-rac.md](zbx-1c-rac.md)** — Документация по RAC
- **[zbx-1c-techlog.md](zbx-1c-techlog.md)** — Документация по техжурналу

---

## ❓ FAQ

### Где хранятся логи?

По умолчанию используются стандартные директории:
- **Windows:** `%APPDATA%/zbx-1c-rac/logs/`
- **Linux:** `/var/log/zbx-1c-rac/`

### Как обновить пакеты?

```bash
pip install -e ./packages/zbx-1c-rac --upgrade
pip install -e ./packages/zbx-1c-techlog --upgrade
```

### Что делать если rac не найден?

Убедитесь, что:
1. 1С установлена на сервере
2. Путь `RAC_PATH` указан верно в `.env.rac`
3. У пользователя есть права на выполнение rac
