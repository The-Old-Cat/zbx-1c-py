# Отчёт о кроссплатформенности проекта zbx-1c-py

## ✅ Уже реализовано

### 1. Конфигурация (`src/zbx_1c/core/config.py`)
- ✅ Использование `pathlib.Path` для кроссплатформенных путей
- ✅ Автоматический поиск `rac` в PATH через `shutil.which()`
- ✅ Создание директории логов автоматически
- ✅ Валидация порта

### 2. Утилиты (`src/zbx_1c/utils/`)
- ✅ `fs.py` - поиск rac.exe для Windows/Linux/macOS
- ✅ `converters.py` - кодировки CP866 для Windows, UTF-8 для Linux/macOS
- ✅ `net.py` - кроссплатформенная проверка портов
- ✅ `rac_client.py` - декодирование вывода с учётом ОС

### 3. CLI (`src/zbx_1c/cli/commands.py`)
- ✅ `safe_output()` - корректный вывод JSON для Windows (через buffer)
- ✅ `safe_print()` - защита от UnicodeEncodeError

### 4. Генератор конфигов (CLI команда)

**Команда:** `zbx-1c-generate-userparam`

- ✅ Раздельная генерация для Windows/Linux
- ✅ Определение версии Zabbix Agent
- ✅ Смена рабочей директории для Windows

---

## ⚠️ Проблемы и рекомендации

### 1. Пути в UserParameter (критично)

**Проблема:** В сгенерированном конфиге используются абсолютные пути к `.venv`, что не работает при переносе.

**Решение:**
```conf
# Windows - использовать entry points после установки
UserParameter=zbx1cpy.clusters.discovery,zbx-1c-discovery
UserParameter=zbx1cpy.metrics[*],zbx-1c-metrics $1

# Linux - аналогично
UserParameter=zbx1cpy.clusters.discovery,zbx-1c-discovery
UserParameter=zbx1cpy.metrics[*],zbx-1c-metrics $1
```

### 2. Кодировка в Linux

**Проблема:** В Linux может потребоваться явная установка локали.

**Решение для Linux конфигов:**
```conf
UserParameter=zbx1cpy.clusters.discovery,LANG=C.UTF-8 PYTHONIOENCODING=utf-8 python3 -m zbx_1c discovery
UserParameter=zbx1cpy.metrics[*],LANG=C.UTF-8 PYTHONIOENCODING=utf-8 python3 -m zbx_1c metrics $1
```

### 3. Поиск RAC в Linux

**Проблема:** В `fs.py` пути к rac захардкожены.

**Текущие пути:**
```python
linux_paths = [
    "/opt/1C/v8.3/x86_64/rac",
    "/opt/1cv8/x86_64/rac",
    "/usr/bin/rac",
]
```

**Рекомендация:** Добавить поиск через `find` или конфигурируемый путь.

### 4. Служебные символы в shell

**Проблема:** В Linux специальные символы `$1` могут интерпретироваться shell.

**Решение:** Использовать одинарные кавычки для UserParameter:
```conf
UserParameter=zbx1cpy.metrics[*],'/usr/bin/python3' -m zbx_1c metrics '$1'
```

### 5. Логирование

**Проблема:** Путь к логам `./logs` относительный, что может работать по-разному.

**Рекомендация:** Использовать абсолютные пути или стандартные директории:
```python
# Linux: /var/log/zbx-1c/
# Windows: %APPDATA%/zbx-1c/logs/
# macOS: ~/Library/Logs/zbx-1c/
```

### 6. Тестовый параметр

**Проблема:** Разные команды для Windows/Linux.

**Текущее решение в генераторе:**
```python
# Windows
UserParameter=zbx1cpy.test, cmd /c ... python -c "print('OK')"

# Linux  
UserParameter=zbx1cpy.test, python -c "print('OK')"
```

✅ Уже корректно реализовано.

---

## 📋 Чек-лист для развёртывания

### Windows
- [ ] Установить Python 3.10+
- [ ] Создать виртуальное окружение: `python -m venv .venv`
- [ ] Установить зависимости: `.venv\Scripts\pip install -e .`
- [ ] Сгенерировать конфиг: `zbx-1c-generate-userparam`
- [ ] Скопировать конфиг в `<ZABBIX_AGENT_DIR>\zabbix_agent2.d\`
- [ ] Перезапустить Zabbix Agent 2
- [ ] Проверить: `zabbix_get.exe -s localhost -k "zbx1cpy.test"`

### Linux
- [ ] Установить Python 3.10+: `apt install python3.10 python3.10-venv`
- [ ] Создать виртуальное окружение: `python3.10 -m venv .venv`
- [ ] Установить зависимости: `.venv/bin/pip install -e .`
- [ ] Сгенерировать конфиг: `zbx-1c-generate-userparam`
- [ ] Скопировать конфиг в `/etc/zabbix/zabbix_agentd.d/`
- [ ] Перезапустить Zabbix Agent: `systemctl restart zabbix-agent`
- [ ] Проверить: `zabbix_get -s localhost -k "zbx1cpy.test"`

### macOS (если поддерживается)
- [ ] Установить Python через Homebrew: `brew install python@3.10`
- [ ] Аналогично Linux

---

## 🔧 Исправления в коде

### 1. generate_userparam_config.py - добавить поддержку entry points

```python
# После установки pip install -e . использовать entry points
UserParameter=zbx1cpy.clusters.discovery,zbx-1c-discovery
UserParameter=zbx1cpy.metrics[*],zbx-1c-metrics $1
```

### 2. commands.py - универсальный safe_output

Уже реализовано корректно:
```python
if sys.platform == "win32":
    sys.stdout.buffer.write((json_str + '\n').encode('utf-8'))
    sys.stdout.buffer.flush()
else:
    click.echo(json_str)
```

### 3. fs.py - улучшить поиск rac для Linux

Добавить поиск в дополнительных путях и через which:
```python
# Уже реализовано через shutil.which("rac")
```

---

## ✅ Итог

Проект **в целом кроссплатформенный**, основные моменты учтены:

| Компонент | Windows | Linux | macOS |
|-----------|---------|-------|-------|
| Конфигурация | ✅ | ✅ | ✅ |
| Кодировки | ✅ CP866 | ✅ UTF-8 | ✅ UTF-8 |
| Пути к файлам | ✅ pathlib | ✅ pathlib | ✅ pathlib |
| RAC поиск | ✅ | ⚠️ | ⚠️ |
| UserParameter | ✅ | ✅ | ✅ |
| JSON вывод | ✅ | ✅ | ✅ |
| Логирование | ⚠️ | ⚠️ | ⚠️ |
| Entry points | ✅ | ✅ | ✅ |

**✅ Реализовано:**
1. Entry points для кроссплатформенного запуска (после `pip install -e .`)
2. Генератор конфигов с поддержкой Windows/Linux
3. Автоматическое определение кодировки

**⚠️ Требует внимания:**
1. Документировать пути RAC для Linux/macOS
2. Улучшить обработку путей к логам

---

## 🚀 Быстрый старт

### Windows

```powershell
# 1. Установка
python -m venv .venv
.\.venv\Scripts\pip install -e .

# 2. Генерация конфига
.\.venv\Scripts\python scripts\generate_userparam_config.py

# 3. Копирование конфига (от администратора)
Copy-Item "zabbix\userparameters\userparameter_1c.conf" `
    -Destination "<ZABBIX_AGENT_DIR>\zabbix_agent2.d\" -Force

# 4. Перезапуск службы
Restart-Service "Zabbix Agent 2"

# 5. Проверка
& "<ZABBIX_AGENT_DIR>\zabbix_get.exe" -s localhost -k "zbx1cpy.test"
& "<ZABBIX_AGENT_DIR>\zabbix_get.exe" -s localhost -k "zbx1cpy.clusters.discovery"
& "<ZABBIX_AGENT_DIR>\zabbix_get.exe" -s localhost -k "zbx1cpy.metrics[<cluster_id>]"
```

### Linux

```bash
# 1. Установка
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 2. Генерация конфига
zbx-1c-generate-userparam

# 3. Копирование конфига
sudo cp zabbix/userparameters/userparameter_1c.conf /etc/zabbix/zabbix_agentd.d/

# 4. Перезапуск службы
sudo systemctl restart zabbix-agent

# 5. Проверка
zabbix_get -s localhost -k "zbx1cpy.test"
zabbix_get -s localhost -k "zbx1cpy.clusters.discovery"
zabbix_get -s localhost -k "zbx1cpy.metrics[<cluster_id>]"
```

### Проверка entry points

```bash
# Должны работать после установки pip install -e .
zbx-1c-discovery
zbx-1c-metrics <cluster_id>
zbx-1c-test
```
