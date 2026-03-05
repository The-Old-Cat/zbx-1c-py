# Руководство по миграции на модульную архитектуру

## Обзор

Проект `zbx-1c-py` был разделен на два независимых пакета для гибкого развертывания.

| Старая структура | Новая структура |
|------------------|-----------------|
| `src/zbx_1c/` (монолит) | `packages/zbx-1c-rac/` |
| | `packages/zbx-1c-techlog/` |

## Что изменилось

### 1. Разделение зависимостей

**Было:**
```toml
dependencies = [
    "loguru", "pydantic", "pydantic-settings",
    "psutil", "fastapi", "uvicorn", "click"
]
# ~10 пакетов
```

**Стало:**

**zbx-1c-rac:**
```toml
dependencies = [
    "loguru", "pydantic", "pydantic-settings",
    "psutil", "click"
]
# ~5 пакетов
```

**zbx-1c-techlog:**
```toml
dependencies = [
    "loguru", "pydantic", "pydantic-settings", "click"
]
# ~4 пакета
```

### 2. Разделение конфигурации

**Было:** Единый `.env`

**Стало:**
- `.env.rac` — для RAC-мониторинга
- `.env.techlog` — для техжурнала

### 3. Изменение CLI команд

**Было:**
```bash
zbx-1c check-ras
zbx-1c discovery
zbx-1c techjournal
```

**Стало:**
```bash
# RAC-мониторинг
zbx-1c-rac check
zbx-1c-rac discovery

# Техжурнал
zbx-1c-techlog collect
zbx-1c-techlog send
```

## Миграция: пошаговое руководство

### Шаг 1: Оценка текущего использования

Определите, какой функционал вы используете:

- **Только RAC** (сессии, задания, кластеры) → устанавливайте `zbx-1c-rac`
- **Только техжурнал** (ошибки, блокировки, SQL) → устанавливайте `zbx-1c-techlog`
- **Оба модуля** → устанавливайте оба пакета

### Шаг 2: Резервное копирование

```bash
# Сохраните текущую конфигурацию
cp .env .env.backup
```

### Шаг 3: Установка новых пакетов

```bash
# Перейдите в директорию проекта
cd g:\Automation\zbx-1c-py

# Установите пакеты
pip install -e ./packages/zbx-1c-rac
pip install -e ./packages/zbx-1c-techlog  # если нужен техжурнал
```

### Шаг 4: Миграция конфигурации

**Для RAC:**
```bash
# Создайте новый конфиг
cp .env.rac.example .env.rac

# Перенесите настройки из старого .env
# RAC_PATH, RAC_HOST, RAC_PORT, USER_NAME, USER_PASS
```

**Для техжурнала:**
```bash
# Создайте новый конфиг
cp .env.techlog.example .env.techlog

# Перенесите настройки из старого .env
# TECHJOURNAL_LOG_BASE, ZABBIX_SERVER, ZABBIX_PORT
```

### Шаг 5: Обновление Zabbix UserParameter

**Было:**
```ini
UserParameter=zbx1cpy.clusters.discovery,zbx-1c discovery
UserParameter=zbx1cpy.metrics[*],zbx-1c metrics $1
UserParameter=zbx1cpy.techjournal,zbx-1c techjournal
```

**Стало:**
```ini
# RAC-мониторинг
UserParameter=zbx1cpy.rac.discovery,zbx-1c-rac discovery
UserParameter=zbx1cpy.rac.metrics[*],zbx-1c-rac metrics $1

# Техжурнал
UserParameter=zbx1cpy.techjournal.collect,zbx-1c-techlog collect --json-output
```

### Шаг 6: Тестирование

```bash
# Проверка RAC
zbx-1c-rac check-config
zbx-1c-rac discovery

# Проверка техжурнала
zbx-1c-techlog check
zbx-1c-techlog collect --period 5
```

## Обратная совместимость

Старая структура (`src/zbx_1c/`) сохраняется для обратной совместимости.
Вы можете продолжить использовать её, но рекомендуется миграция.

## Преимущества новой архитектуры

✅ **Меньше зависимостей** — устанавливайте только нужные пакеты  
✅ **Независимое развертывание** — RAC и техжурнал не зависят друг от друга  
✅ **Раздельные конфигурации** — нет конфликтов настроек  
✅ **Гибкость** — можно использовать оба пакета вместе или по отдельности  
✅ **Проще тестировать** — каждый пакет тестируется независимо  

## Часто задаваемые вопросы

### Можно ли оставить старую структуру?

Да, `src/zbx_1c/` сохраняется. Но новые функции будут добавляться только в модульные пакеты.

### Что делать если я использую только RAC?

Установите только `zbx-1c-rac`:
```bash
pip install -e ./packages/zbx-1c-rac
```

### Что делать если я использую только техжурнал?

Установите только `zbx-1c-techlog`:
```bash
pip install -e ./packages/zbx-1c-techlog
```

### Можно ли использовать оба пакета вместе?

Да! Установите оба:
```bash
pip install -e ./packages/zbx-1c-rac -e ./packages/zbx-1c-techlog
```

### Как обновить скрипты Zabbix?

Замените команды в UserParameter:
- `zbx-1c` → `zbx-1c-rac` (для RAC)
- `zbx-1c techjournal` → `zbx-1c-techlog collect` (для техжурнала)

## Поддержка

Вопросы и предложения:
- Email: ar-kovale@yandex.ru
- GitHub Issues: https://github.com/your-repo/zbx-1c/issues
