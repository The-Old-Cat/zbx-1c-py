# Кроссплатформенность zbx-1c-rac

## ✅ Поддерживаемые платформы

- **Windows** (x64) - ✅ Полная поддержка
- **Linux** (x64, x86) - ✅ Полная поддержка  
- **macOS** (x64, ARM) - ⚠️ Ограниченная поддержка (требуется 1C Server для macOS)

---

## 🔧 Изменения для кроссплатформенности

### 1. Путь к RAC (`config.py`)

```python
def get_default_rac_path() -> Path:
    """Получить путь к rac с учетом ОС"""
    import shutil
    which_rac = shutil.which("rac")
    if which_rac:
        return Path(which_rac)
    
    if sys.platform == "win32":
        # Windows
        default_paths = [
            Path("C:/Program Files/1cv8/8.3.27.1786/bin/rac.exe"),
            Path("C:/Program Files (x86)/1cv8/8.3.27.1786/bin/rac.exe"),
            Path("rac.exe"),
        ]
    else:
        # Linux
        default_paths = [
            Path("/opt/1C/v8.3/x86_64/rac"),
            Path("/opt/1C/v8.3/i386/rac"),
            Path("/usr/bin/rac"),
            Path("rac"),
        ]
    
    for path in default_paths:
        if path.exists():
            return path
    
    return default_paths[0]
```

**Типовые пути к 1C:**

| ОС | Путь |
|----|------|
| Windows | `C:/Program Files/1cv8/8.3.x.x/bin/rac.exe` |
| Linux | `/opt/1C/v8.3/x86_64/rac` |
| Linux (32-bit) | `/opt/1C/v8.3/i386/rac` |

---

### 2. Кодировка вывода (`converters.py`)

```python
def decode_output(data: bytes) -> str:
    import sys
    
    if sys.platform == "win32":
        # Windows: OEM кодировка (CP866 для Russian)
        encodings = ["cp866", "cp1251", "utf-8", "latin-1"]
    else:
        # Linux/macOS: UTF-8
        encodings = ["utf-8", "cp1251", "latin-1"]
    
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue

    return data.decode("utf-8", errors="replace")
```

---

### 3. Имена процессов 1С (`manager.py`)

```python
if sys.platform == "win32":
    # Windows
    process_names = {
        "rphost": ["rphost", "1cv8c", "1cv8"],
        "rmngr": ["rmngr", "ragent"],
        "ragent": ["ragent"],
    }
else:
    # Linux
    process_names = {
        "rphost": ["rphost", "1cv8c", "1cv8"],
        "rmngr": ["rmngr", "ragent"],
        "ragent": ["ragent"],
    }
```

**Имена процессов 1С:**

| Процесс | Windows | Linux |
|---------|---------|-------|
| Рабочий процесс | `rphost`, `1cv8c`, `1cv8.exe` | `rphost`, `1cv8c` |
| Менеджер кластеров | `rmngr`, `ragent.exe` | `rmngr`, `ragent` |
| Агент кластеров | `ragent.exe` | `ragent` |

---

### 4. CLI вывод (`__main__.py`)

```python
def safe_output(data, **kwargs):
    """Безопасный вывод JSON в консоль"""
    json_str = json.dumps(data, ensure_ascii=False, **kwargs)
    if sys.platform == "win32":
        sys.stdout.buffer.write((json_str + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()
    else:
        click.echo(json_str)
```

---

## 📋 Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `RAC_PATH` | Путь к rac | Авто (поиск в PATH) |
| `RAC_HOST` | Хост RAS | `127.0.0.1` |
| `RAC_PORT` | Порт RAS | `1545` |
| `USER_NAME` | Пользователь 1С | - |
| `USER_PASS` | Пароль 1С | - |
| `LOG_PATH` | Путь к логам | `./logs` |
| `DEBUG` | Режим отладки | `False` |
| `RAC_TIMEOUT` | Таймаут RAC | `30` |
| `SESSION_LIMIT` | Лимит сессий | `100` |

---

## 🚀 Установка

### Windows

```powershell
# Установка пакета
pip install -e packages/zbx-1c-rac

# Копирование UserParameter
Copy-Item "zabbix\userparameters\userparameter_1c_rac.conf" `
          "C:\Program Files\Zabbix Agent\zabbix_agentd.d\"

# Перезапуск агента
Restart-Service "Zabbix Agent"
```

### Linux

```bash
# Установка пакета
pip install -e packages/zbx-1c-rac

# Копирование UserParameter
sudo cp zabbix/userparameters/userparameter_1c_rac.conf \
        /etc/zabbix/zabbix_agentd.d/

# Перезапуск агента
sudo systemctl restart zabbix-agent
```

---

## 🧪 Тестирование

### Проверка пути к rac

```bash
# Windows
where rac

# Linux
which rac
```

### Тест discovery

```bash
# Windows
zbx-1c-rac-discovery

# Linux
zbx-1c-rac-discovery
```

### Тест подключения

```bash
# Windows
zbx-1c-rac-check

# Linux
zbx-1c-rac-check
```

---

## ⚠️ Известные ограничения

### Windows
- Требуется 1C:Enterprise Server 8.3+
- Кодировка OEM (CP866) для вывода rac
- Пути содержат пробелы (Program Files)

### Linux
- Требуется 1C:Enterprise Server 8.3+ для Linux
- Может потребоваться установка локалей: `locale-gen ru_RU.UTF-8`
- Права доступа к процессам 1C

### macOS
- Официально не поддерживается 1C Server для macOS
- Требуется запуск 1C Server в Docker или VM

---

## 📝 Changelog

### 2026-03-10
- ✅ Добавлена поддержка кроссплатформенных путей к rac
- ✅ Автоматическое определение кодировки (CP866 для Windows, UTF-8 для Linux)
- ✅ Обновлены имена процессов для разных ОС
- ✅ LLD макросы: `{#CLUSTER_ID}`, `{#CLUSTER_NAME}`, `{#CLUSTER_HOST}`, `{#CLUSTER_PORT}`, `{#CLUSTER_STATUS}`

---

## 📞 Поддержка

При возникновении проблем на конкретной платформе:
1. Проверьте путь к rac: `which rac` или `where rac`
2. Проверьте кодировку: `locale` (Linux) или `chcp` (Windows)
3. Проверьте права доступа к процессам 1C
