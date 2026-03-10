# Документация zbx-1c-py

Кроссплатформенный инструмент для интеграции 1С:Предприятия с системой мониторинга Zabbix.

---

## 📚 Навигация по документации

### 01. Быстрый старт

| Документ | Описание |
|----------|----------|
| **[01-quickstart.md](01-quickstart.md)** | Быстрый старт и установка |
| **[01-packages.md](01-packages.md)** | О модульных пакетах |

### 02. Пакеты

| Пакет | Документация |
|-------|--------------|
| **zbx-1c-rac** | [02-zbx-1c-rac.md](02-zbx-1c-rac.md) — мониторинг через RAC |
| **zbx-1c-techlog** | [02-zbx-1c-techlog.md](02-zbx-1c-techlog.md) — мониторинг через техжурнал |

### 03. Миграция

| Документ | Описание |
|----------|----------|
| **[03-migration.md](03-migration.md)** | Переход с монолитной на модульную архитектуру |

### 04. Настройка и интеграция

| Документ | Описание |
|----------|----------|
| **[04-zabbix-integration.md](04-zabbix-integration.md)** | Интеграция с Zabbix (UserParameter, шаблоны) |
| **[04-cluster-status.md](04-cluster-status.md)** | Мониторинг статуса кластера |
| **[04-logcfg-setup.md](04-logcfg-setup.md)** | Настройка техжурнала 1С (logcfg.xml) |

### 05. Кроссплатформенность

| Документ | Описание |
|----------|----------|
| **[05-crossplatform.md](05-crossplatform.md)** | Общая кроссплатформенность проекта |
| **[05-zbx-1c-rac-crossplatform.md](05-zbx-1c-rac-crossplatform.md)** | Кроссплатформенность zbx-1c-rac |

### 06. Архитектура и API

| Документ | Описание |
|----------|----------|
| **[06-architecture.md](06-architecture.md)** | Архитектура проекта |
| **[06-api.md](06-api.md)** | REST API для интеграции |

---

## 📋 Структура документации

```
docs/
├── README.md                          # Этот файл (навигация)
│
├── 01-quickstart.md                   # Быстрый старт
├── 01-packages.md                     # О пакетах
│
├── 02-deployment.md                   # Развёртывание
├── 02-zbx-1c-rac.md                   # Пакет RAC
├── 02-zbx-1c-techlog.md               # Пакет техжурнала
│
├── 03-migration.md                    # Миграция с монолита
│
├── 04-zabbix-integration.md           # Интеграция с Zabbix
├── 04-cluster-status.md               # Мониторинг кластеров
├── 04-logcfg-setup.md                 # Настройка logcfg.xml
│
├── 05-crossplatform.md                # Общая кроссплатформенность
├── 05-zbx-1c-rac-crossplatform.md     # Кроссплатформенность RAC
│
└── 06-architecture.md                 # Архитектура
└── 06-api.md                          # REST API
```

---

## 🎯 Модульная архитектура

Проект разделён на **два независимых пакета**:

| Пакет | Назначение | Установка |
|-------|------------|-----------|
| **[zbx-1c-rac](02-zbx-1c-rac.md)** | Мониторинг через RAC (сессии, задания, кластеры) | `pip install -e packages/zbx-1c-rac` |
| **[zbx-1c-techlog](02-zbx-1c-techlog.md)** | Мониторинг через техжурнал 1С (ошибки, блокировки, SQL) | `pip install -e packages/zbx-1c-techlog` |

**Преимущества:**
- ✅ Независимое развёртывание
- ✅ Минимум зависимостей
- ✅ Раздельные конфигурации (`.env.rac`, `.env.techlog`)

---

## 🚀 Быстрый старт

### 1. Установка zbx-1c-rac

```bash
cd packages/zbx-1c-rac
pip install -e .
cp ../../.env.rac.example ../../.env.rac
zbx-1c-rac check-config
```

### 2. Установка zbx-1c-techlog

```bash
cd packages/zbx-1c-techlog
pip install -e .
cp ../../.env.techlog.example ../../.env.techlog
zbx-1c-techlog check
```

### 3. Оба пакета вместе

```bash
pip install -e ./packages/zbx-1c-rac -e ./packages/zbx-1c-techlog
```

---

## 📞 Поддержка

- **Email:** ar-kovale@yandex.ru
- **GitHub Issues:** https://github.com/your-repo/zbx-1c/issues

---

## 📅 Дата обновления документации

Последнее обновление: **2026-03-10**
