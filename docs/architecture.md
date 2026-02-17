# Архитектура проекта zbx-1c-py

## Обзор

Проект zbx-1c-py представляет собой кроссплатформенный инструмент для интеграции 1С:Предприятия с системой мониторинга Zabbix. Архитектура построена по модульному принципу с четким разделением ответственности.

## Архитектурные принципы

1. **Модульность** - каждый компонент имеет свою область ответственности
2. **Слоистость** - разделение на уровни (API, CLI, Core, Monitoring, Utils)
3. **Зависимости** - зависимости направлены внутрь (от внешних слоев к внутренним)
4. **Тестируемость** - каждый модуль может быть протестирован изолированно
5. **Кроссплатформенность** - поддержка Windows, Linux, macOS

## Структура проекта

```
zbx-1c-py/
├── src/zbx_1c/                  # Главный пакет
│   ├── __init__.py              # Инициализация пакета
│   ├── __main__.py              # Точка входа для python -m
│   │
│   ├── api/                     # Уровень REST API
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI приложение
│   │   ├── routes.py            # Маршруты API
│   │   └── dependencies.py      # Зависимости (DI)
│   │
│   ├── cli/                     # Уровень CLI
│   │   ├── __init__.py
│   │   ├── commands.py          # Команды Click
│   │   └── zabbix_config.py     # Проверка конфига Zabbix
│   │
│   ├── core/                    # Ядро приложения
│   │   ├── __init__.py
│   │   ├── config.py            # Конфигурация (Settings)
│   │   ├── exceptions.py        # Исключения
│   │   ├── logging.py           # Логирование
│   │   └── models.py            # Модели данных
│   │
│   ├── monitoring/              # Модули мониторинга
│   │   ├── cluster/             # Управление кластерами
│   │   │   ├── manager.py       # ClusterManager
│   │   │   └── discovery.py     # Обнаружение кластеров
│   │   ├── infobase/            # Информационные базы
│   │   │   ├── finder.py        # Поиск ИБ
│   │   │   ├── analyzer.py      # Анализ нагрузки
│   │   │   └── monitor.py       # Мониторинг ИБ
│   │   ├── session/             # Сессии
│   │   │   ├── collector.py     # Сбор сессий
│   │   │   └── filters.py       # Фильтрация
│   │   └── jobs/                # Фоновые задания
│   │       └── reader.py        # Чтение заданий
│   │
│   └── utils/                   # Утилиты
│       ├── rac_client.py        # RAC клиент
│       ├── converters.py        # Парсинг вывода rac
│       ├── fs.py                # Файловая система
│       └── net.py               # Сеть
│
├── tests/                       # Тесты
├── scripts/                     # Скрипты
├── docs/                        # Документация
├── zabbix/                      # Интеграция с Zabbix
└── ...
```

## Уровни архитектуры

### 1. Уровень представления (API/CLI)

**API (`src/zbx_1c/api/`)**
- REST API на FastAPI
- Эндпоинты для внешних систем
- Валидация входных данных
- Форматирование ответов

**CLI (`src/zbx_1c/cli/`)**
- Команды для работы через терминал
- Интеграция с Click
- Поддержка JSON вывода
- Проверка конфигурации

### 2. Уровень бизнес-логики (Monitoring)

**Cluster (`src/zbx_1c/monitoring/cluster/`)**
- `ClusterManager` - управление кластерами
- `discover_clusters()` - обнаружение кластеров
- `get_infobases()` - получение ИБ
- `get_sessions()` - получение сессий
- `get_jobs()` - получение заданий
- `get_cluster_metrics()` - метрики кластера

**Infobase (`src/zbx_1c/monitoring/infobase/`)**
- `Finder` - поиск информационных баз
- `Analyzer` - анализ нагрузки
- `Monitor` - мониторинг ИБ

**Session (`src/zbx_1c/monitoring/session/`)**
- `SessionCollector` - сбор сессий
- `is_session_active()` - проверка активности
- `filter_active_sessions()` - фильтрация

**Jobs (`src/zbx_1c/monitoring/jobs/`)**
- `JobReader` - чтение фоновых заданий
- Фильтрация активных заданий

### 3. Уровень ядра (Core)

**Config (`src/zbx_1c/core/config.py`)**
- Класс `Settings` на базе Pydantic
- Загрузка из `.env` файла
- Валидация настроек
- Кэширование (`lru_cache`)

**Logging (`src/zbx_1c/core/logging.py`)**
- Настройка `loguru`
- Ротация логов
- Уровни логирования

**Models (`src/zbx_1c/core/models.py`)**
- Модели данных (ClusterInfo, SessionInfo, и т.д.)
- Валидация через Pydantic

### 4. Уровень утилит (Utils)

**RAC Client (`src/zbx_1c/utils/rac_client.py`)**
- Выполнение команд rac
- Декодирование вывода (cp866, cp1251, utf-8)
- Обработка ошибок

**Converters (`src/zbx_1c/utils/converters.py`)**
- `parse_rac_output()` - парсинг вывода rac
- `format_lld_data()` - формат для Zabbix LLD
- `format_metrics()` - формат метрик

**FS (`src/zbx_1c/utils/fs.py`)**
- Поиск rac в системе
- Работа с временными файлами
- Создание директорий

**Net (`src/zbx_1c/utils/net.py`)**
- Проверка доступности портов
- Валидация хостов

## Поток данных

### 1. Обнаружение кластеров (Discovery)

```
CLI/API → ClusterManager.discover_clusters()
    → RACClient.execute(["rac", "cluster", "list", "host:port"])
    → parse_clusters()
    → List[Dict] (кластеры)
```

### 2. Сбор метрик (Metrics)

```
CLI/API → ClusterManager.get_cluster_metrics(cluster_id)
    → get_sessions(cluster_id)
    → get_jobs(cluster_id)
    → Подсчет метрик
    → Dict (метрики)
```

### 3. Мониторинг сессий (Sessions)

```
CLI → SessionCollector.get_sessions(cluster_id)
    → RACClient.execute(["rac", "session", "list", "--cluster=...", "host:port"])
    → parse_sessions()
    → List[Dict] (сессии)
```

## Взаимодействие с 1С

### RAC (Remote Administration Client)

Проект использует утилиту rac для взаимодействия с 1С:

```python
# Формирование команды
cmd = [
    str(settings.rac_path),
    "cluster",
    "list",
    f"{settings.rac_host}:{settings.rac_port}",
]

# Выполнение
result = rac.execute(cmd)

# Парсинг
clusters = parse_clusters(result["stdout"])
```

### Формат вывода rac

```
cluster : f93863ed-3fdb-4e01-a74c-e112c81b053b
host    : srv-pinavto01
port    : 1541
name    : "Локальный кластер"
```

### Кодировки

Проект автоматически обрабатывает кодировки:
- **Windows**: cp866 (консоль), cp1251 (Windows)
- **Linux/macOS**: utf-8

## Кэширование

Для оптимизации используется кэширование:

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()

# В ClusterManager
self._clusters_cache: Optional[List[Dict]] = None

def discover_clusters(self, use_cache: bool = True):
    if use_cache and self._clusters_cache:
        return self._clusters_cache
    # ...
```

## Обработка ошибок

```python
try:
    result = rac.execute(cmd)
    if not result:
        logger.error("RAC command failed")
        return []
    if result["returncode"] != 0:
        logger.error(f"RAC error: {result['stderr']}")
        return []
    return parse_rac_output(result["stdout"])
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return []
```

## Расширяемость

### Добавление новой команды CLI

```python
@cli.command("new-command")
@click.argument("cluster_id")
def new_command(cluster_id: str):
    """Описание команды"""
    settings = load_settings()
    manager = ClusterManager(settings)
    result = manager.new_operation(cluster_id)
    click.echo(json.dumps(result))
```

### Добавление нового эндпоинта API

```python
@router.get("/new-endpoint")
async def new_endpoint(cluster_id: str = Path(...)):
    settings = get_settings()
    manager = ClusterManager(settings)
    return manager.new_operation(cluster_id)
```

## Тестирование

### Структура тестов

```
tests/
├── conftest.py              # Фикстуры
├── test_basic.py            # Базовые тесты
├── test_clusters.py         # Тесты кластеров
├── test_sessions.py         # Тесты сессий
├── test_config.py           # Тесты конфигурации
└── ...
```

### Пример теста

```python
def test_discover_clusters(settings):
    manager = ClusterManager(settings)
    clusters = manager.discover_clusters()
    assert len(clusters) > 0
    assert "id" in clusters[0]
    assert "name" in clusters[0]
```

## Безопасность

1. **Пароли** - не логируются, маскируются в ошибках
2. **Настройки** - загружаются из `.env` (не в репозитории)
3. **Валидация** - все входные данные валидируются через Pydantic

## Производительность

1. **Кэширование** - LRU кэш для настроек и кластеров
2. **Таймауты** - ограничение времени выполнения RAC команд
3. **Пакетный запрос** - один вызов = все метрики кластера

## Миграция

### С версии 0.0.x на 0.1.0

Изменения в архитектуре:
- Переход на модульную структуру
- Возврат `List[Dict]` вместо объектов
- Унификация CLI команд

Обновление импортов:
```python
# Было
from zbx_1c.monitoring.clusters import ClusterManager

# Стало
from zbx_1c.monitoring.cluster.manager import ClusterManager
```
