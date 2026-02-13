# API и интерфейсы

## Команды командной строки

### Режим обнаружения (--discovery)
**Назначение**: Получение списка кластеров 1С для Zabbix LLD (Low-Level Discovery)

**Команда**:
```bash
uv run src/zbx_1c_py/main.py --discovery
```

**Возвращаемое значение**: JSON-массив объектов с информацией о кластерах

**Пример ответа**:
```json
[
  {
    "{#CLUSTER_ID}": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
    "{#CLUSTER_NAME}": "Основной кластер"
  },
  {
    "{#CLUSTER_ID}": "b2c3d4e5-6789-01ab-cdef-2345678901bc",
    "{#CLUSTER_NAME}": "Резервный кластер"
  }
]
```

### Режим проверки RAS (--check-ras)
**Назначение**: Проверка доступности RAS-сервиса 1С

**Команда**:
```bash
uv run src/zbx_1c_py/main.py --check-ras
```

**Возвращаемое значение**: JSON-объект с информацией о статусе RAS

**Пример ответа**:
```json
{
  "available": true,
  "message": "RAS is reachable",
  "code": 0
}
```

**Пример ответа при ошибке**:
```json
{
  "available": false,
  "message": "RAC Error (Code 1): Connection refused",
  "code": 1
}
```

### Режим сбора метрик для кластера
**Назначение**: Сбор метрик для конкретного кластера 1С

**Команда**:
```bash
uv run src/zbx_1c_py/main.py <cluster_id>
```

**Параметры**:
- `<cluster_id>`: UUID кластера 1С

**Возвращаемое значение**: JSON-объект с метриками кластера

**Пример ответа**:
```json
{
  "cluster_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "cluster_name": "Основной кластер",
  "metrics": {
    "total_sessions": 25,
    "active_sessions": 8,
    "active_bg_jobs": 2,
    "status": 1
  }
}
```

### Режим по умолчанию
**Назначение**: Сбор метрик для первого доступного кластера

**Команда**:
```bash
uv run src/zbx_1c_py/main.py
```

**Возвращаемое значение**: JSON-объект с метриками первого кластера

## Запуск приложения с использованием uv

Проект полностью изолирован от системного Python и использует uv для управления зависимостями и запуска приложения. Это обеспечивает стабильность и воспроизводимость работы на любой операционной системе.

### Запуск приложения
```bash
uv run python -m src.zbx_1c_py.main --discovery
```

### Альтернативные способы запуска
```bash
# Запуск с указанием конкретного кластера
uv run python -m src.zbx_1c_py.main <cluster_id>

# Запуск проверки RAS
uv run python -m src.zbx_1c_py.main --check-ras
```

### Запуск в продакшене
Для продакшена рекомендуется использовать uv в изолированном режиме:
```bash
# Установка проекта в изолированное окружение
uv sync --locked

# Запуск приложения
uv run src/zbx_1c_py/main.py --discovery
```

## Кроссплатформенные особенности API

### Утилита rac
API взаимодействует с различными версиями утилиты rac в зависимости от операционной системы:
- **Windows**: `rac.exe`
- **Linux**: `rac`
- **macOS**: `rac`

### Пути к исполняемым файлам
- **Windows**: `C:/Program Files/1cv8/x.x.x.x/rac.exe`
- **Linux**: `/opt/1C/v8.3/x.x.x.x/rac`
- **macOS**: `/Applications/1C/Enterprise Platform/x.x.x.x/rac`

### Кодировка данных
API автоматически обрабатывает различия в кодировке:
- **Windows**: по умолчанию используется CP866 для 1С
- **Linux/macOS**: обычно используется UTF-8
- Проект автоматически обрабатывает различия в кодировке

## Внутренние API модулей

### Модуль clusters.py

#### `check_ras_availability() -> Dict[str, Any]`
Проверяет доступность RAS-сервиса.

**Возвращаемое значение**: Словарь с ключами:
- `available` (bool): Доступен ли сервис
- `message` (str): Сообщение о статусе
- `code` (int): Код результата

#### `get_all_clusters() -> List[Dict[str, Any]]`
Получает список всех доступных кластеров.

**Возвращаемое значение**: Список словарей с информацией о кластерах

#### `get_cluster_ids() -> List[str]`
Получает список UUID всех кластеров.

**Возвращаемое значение**: Список строк с UUID кластеров

#### `get_default_cluster() -> Optional[Dict[str, Any]]`
Получает первый кластер из списка.

**Возвращаемое значение**: Словарь с информацией о кластере или None

### Модуль session.py

#### `fetch_raw_sessions(cluster_uuid: str) -> List[Dict[str, Any]]`
Получает "сырые" данные о сессиях для указанного кластера.

**Параметры**:
- `cluster_uuid` (str): UUID кластера

**Возвращаемое значение**: Список словарей с информацией о сессиях

#### `get_session_command(cluster_uuid: str) -> List[str]`
Формирует команду для получения сессий.

**Параметры**:
- `cluster_uuid` (str): UUID кластера

**Возвращаемое значение**: Список строк команды

### Модуль session_active.py

#### `is_session_active(session: Dict[str, Any], threshold_minutes: int = 5) -> bool`
Проверяет, является ли сессия активной.

**Параметры**:
- `session` (Dict[str, Any]): Словарь с информацией о сессии
- `threshold_minutes` (int): Порог активности в минутах

**Возвращаемое значение**: True, если сессия активна, иначе False

#### `filter_active_sessions(sessions: List[Dict[str, Any]], threshold_minutes: int = 5) -> List[Dict[str, Any]]`
Фильтрует список сессий, оставляя только активные.

**Параметры**:
- `sessions` (List[Dict[str, Any]]): Список сессий
- `threshold_minutes` (int): Порог активности в минутах

**Возвращаемое значение**: Список активных сессий

### Модуль background_jobs.py

#### `is_background_job_active(job: Dict[str, Any], max_duration_minutes: int = 60) -> bool`
Проверяет, является ли фоновое задание активным.

**Параметры**:
- `job` (Dict[str, Any]): Словарь с информацией о задании
- `max_duration_minutes` (int): Максимальная длительность в минутах

**Возвращаемое значение**: True, если задание активно, иначе False

#### `filter_active_background_jobs(jobs: List[Dict[str, Any]], max_duration_minutes: int = 60) -> List[Dict[str, Any]]`
Фильтрует список заданий, оставляя только активные.

**Параметры**:
- `jobs` (List[Dict[str, Any]]): Список заданий
- `max_duration_minutes` (int): Максимальная длительность в минутах

**Возвращаемое значение**: Список активных заданий

### Модуль utils.helpers.py

#### `universal_filter(data: List[dict], fields: Union[List[str], Dict[str, str]]) -> List[dict]`
Универсальный фильтр для списков словарей.

**Параметры**:
- `data` (List[dict]): Исходный список словарей
- `fields` (Union[List[str], Dict[str, str]]): Поля для фильтрации или переименования

**Возвращаемое значение**: Отфильтрованный список словарей

#### `parse_rac_output(raw_text: str) -> List[Dict[str, str]]`
Парсит вывод утилиты rac.

**Параметры**:
- `raw_text` (str): Сырой текстовый вывод rac

**Возвращаемое значение**: Список словарей с информацией из вывода

#### `decode_output(raw_data: bytes) -> str`
Декодирует бинарные данные от rac.

**Параметры**:
- `raw_data` (bytes): Бинарные данные

**Возвращаемое значение**: Декодированная строка