# zbx-1c: Модульная система мониторинга 1С

Два независимых пакета для мониторинга 1С:Предприятия в системе Zabbix.

## 📦 Пакеты

| Пакет | Назначение | Зависимости | Установка |
|-------|------------|-------------|-----------|
| **[zbx-1c-rac](zbx-1c-rac/)** | Мониторинг через RAC (сессии, задания, кластеры) | ~5 пакетов | `pip install -e zbx-1c-rac` |
| **[zbx-1c-techlog](zbx-1c-techlog/)** | Мониторинг через техжурнал 1С (ошибки, блокировки, SQL) | ~4 пакета | `pip install -e zbx-1c-techlog` |

## 🚀 Быстрый старт

### Только мониторинг RAC

```bash
cd zbx-1c-rac
pip install -e .
cp ../../.env.rac.example ../../.env.rac
zbx-1c-rac check-config
```

### Только мониторинг техжурнала

```bash
cd zbx-1c-techlog
pip install -e .
cp ../../.env.techlog.example ../../.env.techlog
zbx-1c-techlog check
```

### Оба пакета вместе

```bash
pip install -e zbx-1c-rac -e zbx-1c-techlog
```

## 📚 Документация

- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Полное руководство по развертыванию
- **[zbx-1c-rac/README.md](zbx-1c-rac/README.md)** — Документация по RAC-мониторингу
- **[zbx-1c-techlog/README.md](zbx-1c-techlog/README.md)** — Документация по техжурналу

## 🎯 Преимущества разделения

✅ **Независимое развертывание** — устанавливайте только нужный пакет  
✅ **Минимум зависимостей** — никаких лишних пакетов  
✅ **Разные конфигурации** — `.env.rac` и `.env.techlog` не конфликтуют  
✅ **Гибкость** — можно использовать оба пакета вместе или по отдельности

## 📋 Сравнение с монолитной версией

| Характеристика | Монолит (старая) | Модульная (новая) |
|----------------|------------------|-------------------|
| Зависимостей | ~10 пакетов | ~4-5 пакетов на пакет |
| Конфигурация | Единый `.env` | Раздельные `.env.rac`, `.env.techlog` |
| Установка | Все или ничего | Только нужное |
| Обновление | Полное | Покомпонентное |

## 🔧 Для разработчиков

### Структура

```
packages/
├── zbx-1c-rac/
│   ├── pyproject.toml
│   ├── src/zbx_1c_rac/
│   └── README.md
│
├── zbx-1c-techlog/
│   ├── pyproject.toml
│   ├── src/zbx_1c_techlog/
│   └── README.md
│
└── DEPLOYMENT.md
```

### Общие утилиты (shared/)

```
shared/
├── core/
│   ├── logging.py
│   └── config.py
└── zabbix/
    └── sender.py
```

Используйте `shared/` для общего кода между пакетами.

## 📞 Поддержка

- Email: ar-kovale@yandex.ru
- GitHub Issues: https://github.com/your-repo/zbx-1c/issues
