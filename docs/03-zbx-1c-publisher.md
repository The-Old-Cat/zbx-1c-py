# Автопубликация 1С (zbx-1c-publisher)

Инструмент для массовой публикации информационных баз 1С:Предприятия с автоматической генерацией VRD-файлов.

## 🎯 Назначение

При большом количестве информационных баз ручное создание и редактирование `.vrd` файлов для каждой из них становится неэффективным. Пакет `zbx-1c-publisher` решает эту проблему:

- **Автоматическое получение списка баз** с сервера 1С через COM
- **Программная генерация VRD** на лету из шаблонов
- **Массовая публикаство всех баз** одной командой
- **Гибкое управление режимами** — FULL (все сервисы) или THIN (только OData)

## 🚀 Быстрый старт

### Установка

```bash
cd packages/zbx-1c-publisher
pip install -e .
```

### Настройка

1. Создайте `.env` файл:

```bash
# Сервер 1С
SERVER_1C_HOST=localhost
SERVER_1C_PORT=1545

# Режим публикации: FULL или THIN
PUBLISH_MODE=FULL

# Директория для публикации
PUBLISH_ROOT=C:/inetpub/wwwroot

# Суффикс для технических имён
TECH_SUFFIX=_pub
```

2. Проверьте подключение к серверу 1С:

```bash
zbx-1c-publisher list
```

### Публикация

```bash
# Опубликовать одну базу
zbx-1c-publisher publish MyDatabase

# Опубликовать все базы
zbx-1c-publisher publish-all

# Опубликовать в режиме THIN (экономия ресурсов)
zbx-1c-publisher publish-all --mode THIN
```

## 📋 Команды

### `list` — Просмотр списка баз

```bash
# Показать все базы
zbx-1c-publisher list

# Указать сервер
zbx-1c-publisher list --server 1c-server.example.com
```

### `publish` — Публикация одной базы

```bash
# Опубликовать базу
zbx-1c-publisher publish MyDatabase

# С техническим именем
zbx-1c-publisher publish MyDatabase --tech-name mydb_web

# В режиме THIN
zbx-1c-publisher publish MyDatabase --mode THIN

# Тестовый режим (без публикации)
zbx-1c-publisher publish MyDatabase --dry-run
```

### `publish-all` — Массовая публикация

```bash
# Все базы
zbx-1c-publisher publish-all

# Только с префиксом "prod_"
zbx-1c-publisher publish-all --prefix prod_

# Исключить некоторые базы
zbx-1c-publisher publish-all --exclude TestBase,ArchivedBase

# Пропустить уже опубликованные
zbx-1c-publisher publish-all --skip-existing
```

### `unpublish` — Удаление публикации

```bash
zbx-1c-publisher unpublish MyDatabase_pub
```

### `validate` — Проверка VRD-файла

```bash
zbx-1c-publisher validate path/to/file.vrd
```

## ⚙️ Конфигурация

### Основные параметры

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `SERVER_1C_HOST` | Адрес сервера 1С | `localhost` |
| `SERVER_1C_PORT` | Порт сервера 1С | `1545` |
| `PUBLISH_MODE` | Режим публикации (FULL/THIN) | `FULL` |
| `PUBLISH_ROOT` | Корневая директория публикации | `C:/inetpub/wwwroot` |
| `TECH_SUFFIX` | Суффикс для технических имён | `_pub` |
| `BASE_PREFIX` | Префиксы баз для публикации | — |
| `BASE_EXCLUDE` | Исключения баз | — |

## 📁 VRD-шаблоны

### full.vrd — Полная публикация

Все HTTP-сервисы, Web-сервисы и OData включены.

### thin.vrd — Минимальная публикация

HTTP-сервисы отключены, доступен только OData и Аналитика.

## 📖 Полная документация

См. [packages/zbx-1c-publisher/docs/README.md](../packages/zbx-1c-publisher/docs/README.md)
