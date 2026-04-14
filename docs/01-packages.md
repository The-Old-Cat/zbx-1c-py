# zbx-1c: Система мониторинга 1С через техжурнал

Пакет для мониторинга 1С:Предприятия через техжурнал в системе Zabbix.

## 📦 Пакет

| Пакет | Назначение | Зависимости | Установка |
|-------|------------|-------------|-----------|
| **[zbx-1c-techlog](zbx-1c-techlog/)** | Мониторинг через техжурнал 1С (ошибки, блокировки, SQL) | ~4 пакета | `pip install -e zbx-1c-techlog` |

## 🚀 Быстрый старт

### Мониторинг через техжурнал

```bash
cd zbx-1c-techlog
pip install -e .
cp ../../.env.techlog.example ../../.env.techlog
zbx-1c-techlog check
```

## 📚 Документация

- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Полное руководство по развертыванию
- **[zbx-1c-techlog/README.md](zbx-1c-techlog/README.md)** — Документация по техжурналу

## 🎯 Преимущества

✅ **Минимум зависимостей** — только необходимые пакеты
✅ **Простая конфигурация** — `.env.techlog` для всех настроек
✅ **Гибкость** — мониторинг ошибок, блокировок, медленного SQL

## 🔧 Для разработчиков

### Структура

```
packages/
└── zbx-1c-techlog/
    ├── pyproject.toml
    ├── src/zbx_1c_techlog/
    └── README.md
```

## 📞 Поддержка

- Email: ar-kovale@yandex.ru
- GitHub Issues: https://github.com/your-repo/zbx-1c/issues
