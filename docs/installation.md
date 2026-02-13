# Установка и развертывание

## Требования к системе

### Минимальные требования
- Python 3.8 или выше
- Операционная система: Windows, Linux или macOS
- Доступ к серверу 1С с включенным RAS (Remote Administration Service)
- Утилита `uv` для управления зависимостями (рекомендуется)

### Зависимости
- `uv` - менеджер зависимостей Python (альтернатива pip/pipenv/poetry)
- `rac` - утилита командной строки для администрирования кластеров 1С (разные версии для разных ОС)
- `loguru` - библиотека для логирования
- `pydantic-settings` - библиотека для управления настройками
- `pytest` - фреймворк для тестирования (для разработки)

## Установка uv (рекомендуется)

Если вы еще не установили `uv`, выполните:

**Windows**:
```powershell
pip install uv
```

**Linux/macOS**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Или через pip:
```bash
pip install uv
```

## Установка проекта

### 1. Клонирование репозитория
```bash
git clone https://github.com/username/zbx-1c-py.git
cd zbx-1c-py
```

### 2. Установка зависимостей
```bash
uv sync
```

Эта команда установит все необходимые зависимости в изолированное окружение, полностью изолированное от системного Python.

### 3. Альтернативный способ: использование pip
Если вы предпочитаете использовать pip вместо uv:

```bash
pip install -e .
```

**Примечание**: При использовании pip проект будет зависеть от системного Python и установленных в нем пакетов. Рекомендуется использовать uv для полной изоляции проекта.

## Запуск проекта с использованием uv

Проект полностью изолирован от системного Python и использует uv для управления зависимостями и запуска приложения. Это обеспечивает стабильность и воспроизводимость работы на любой операционной системе.

### Запуск приложения
```bash
uv run python -m src.zbx_1c_py.main --discovery
```

### Проверка конфигурации
```bash
uv run scripts/check_config.py
```

### Запуск тестов
```bash
uv run pytest
```

### Запуск в продакшене
Для продакшена рекомендуется использовать uv в изолированном режиме:
```bash
# Установка проекта в изолированное окружение
uv sync --locked

# Запуск приложения
uv run python -m src.zbx_1c_py.main --check-ras
```

## Управление зависимостями с помощью uv

### Обновление зависимостей
```bash
uv sync --upgrade
```

### Проверка уязвимостей
```bash
uv run pip-audit
```

### Создание lock-файла
```bash
uv lock
```

### Установка конкретной версии Python
Если нужно использовать конкретную версию Python:
```bash
uv python install 3.11
uv sync
```

## Настройка конфигурации

### 1. Создание файла .env
Создайте файл `.env` в корне проекта на основе примера:

```bash
cp .env.example .env
```

### 2. Настройка параметров
Откройте файл `.env` и настройте параметры подключения к 1С:

```env
# Путь к утилите rac (различается в зависимости от ОС)
# Windows:
# RAC_PATH=C:/Program Files/1cv8/rac.exe
# Linux:
# RAC_PATH=/opt/1C/v8.3/x.x.x.x/rac
# macOS:
# RAC_PATH=/Applications/1C/Enterprise Platform/x.x.x.x/rac

# Хост и порт RAS-сервиса
RAC_HOST=127.0.0.1
RAC_PORT=1545

# Параметры аутентификации (опционально)
USER_NAME=your_username
USER_PASS=your_password

# Путь к директории для логов
LOG_PATH=./logs

# Режим отладки
DEBUG=false
```

## Проверка установки

### 1. Проверка конфигурации
```bash
uv run scripts/check_config.py
```

### 2. Проверка доступности RAS
```bash
uv run src/zbx_1c_py/main.py --check-ras
```

### 3. Проверка обнаружения кластеров
```bash
uv run src/zbx_1c_py/main.py --discovery
```

## Кроссплатформенные особенности

### Установка на Windows
- Убедитесь, что путь к `rac.exe` указан правильно (обычно в `C:/Program Files/1cv8/x.x.x.x/rac.exe`)
- Проверьте, что у пользователя есть права на выполнение файла
- Используйте прямые или косые слэши в путях

### Установка на Linux
- Убедитесь, что исполняемый файл `rac` имеет права на выполнение: `chmod +x /path/to/rac`
- Проверьте, что путь к 1С соответствует установленной версии
- Убедитесь, что пользователь Zabbix Agent может получить доступ к исполняемому файлу

### Установка на macOS
- Убедитесь, что 1С установлена и доступна в PATH
- Проверьте права доступа к исполняемому файлу `rac`
- Убедитесь, что все зависимости Python установлены корректно

### Пути к исполняемым файлам
- **Windows**: `C:/Program Files/1cv8/x.x.x.x/rac.exe`
- **Linux**: `/opt/1C/v8.3/x.x.x.x/rac`
- **macOS**: `/Applications/1C/Enterprise Platform/x.x.x.x/rac`

## Развертывание в продакшене

### 1. Подготовка к развертыванию
- Убедитесь, что все зависимости установлены
- Проверьте настройки безопасности
- Протестируйте работу скрипта в тестовой среде
- Убедитесь, что проект работает на целевой операционной системе

### 2. Установка в систему
Для установки в систему можно использовать следующий подход:

```bash
# Создание виртуального окружения
python -m venv production_env

# Активация окружения
source production_env/bin/activate  # Linux/macOS
# или
production_env\Scripts\activate  # Windows

# Установка зависимостей
pip install .

# Проверка работы
python -m src.zbx_1c_py.main --check-ras
```

### 3. Настройка как службы (Linux)
Для автоматического запуска скрипта можно создать systemd-службу:

Создайте файл `/etc/systemd/system/zbx-1c-monitor.service`:

```ini
[Unit]
Description=Zabbix 1C Monitoring Script
After=network.target

[Service]
Type=oneshot
User=zabbix
Group=zabbix
WorkingDirectory=/path/to/zbx-1c-py
ExecStart=/usr/bin/python3 /path/to/zbx-1c-py/src/zbx_1c_py/main.py --check-ras
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl daemon-reload
sudo systemctl enable zbx-1c-monitor
```

### 4. Настройка как задачи планировщика (Windows)
Для Windows можно создать задачу в планировщике заданий, которая будет периодически выполнять проверки.

### 5. Запуск на macOS
На macOS можно использовать launchd для автоматического запуска скрипта:

Создайте файл `~/Library/LaunchAgents/com.zbx-1c-py.monitor.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.zbx-1c-py.monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/path/to/zbx-1c-py/src/zbx_1c_py/main.py</string>
        <string>--check-ras</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StartInterval</key>
    <integer>300</integer>
</dict>
</plist>
```

Затем:
```bash
launchctl load ~/Library/LaunchAgents/com.zbx-1c-py.monitor.plist
```

## Обновление проекта

### 1. Обновление кода
```bash
git pull origin main
```

### 2. Обновление зависимостей
```bash
uv sync --upgrade
```

### 3. Проверка после обновления
```bash
uv run pytest
uv run src/zbx_1c_py/main.py --check-ras
```

## Удаление проекта

### 1. Удаление зависимостей
```bash
uv pip uninstall zbx-1c-py
```

### 2. Удаление файлов
```bash
rm -rf /path/to/zbx-1c-py
```

## Устранение неполадок

### Проблемы с установкой зависимостей
- Убедитесь, что используется совместимая версия Python
- Попробуйте обновить pip: `python -m pip install --upgrade pip`
- Проверьте доступ к интернету для скачивания пакетов

### Кроссплатформенные проблемы
- **Windows**: Убедитесь, что пути указаны с правильными разделителями
- **Linux**: Проверьте права доступа к исполняемым файлам
- **macOS**: Убедитесь, что 1С правильно установлена и сертификаты доверия настроены

### Проблемы с доступом к 1С
- Проверьте настройки RAS-сервиса
- Убедитесь, что учетные данные верны
- Проверьте сетевое подключение к серверу 1С
- Убедитесь, что используется правильный порт
- Проверьте, что исполняемый файл `rac` доступен и может быть запущен

### Проблемы с выполнением скрипта
- Проверьте права доступа к файлам
- Убедитесь, что все зависимости установлены
- Проверьте настройки конфигурации
- Изучите лог-файлы в указанной директории
- Убедитесь, что проект запускается в правильной операционной системе