---
created: 2026-02-11T09:27
description: "Технологический журнал (ТЖ) — инструмент диагностики платформы 1С:Предприятие для записи технических событий: SQL-запросы, блокировки, ошибки, вызовы, действия администратора."
tags:
  - 1С
  - мониторинг
  - производительность
  - гайд
updated: 2026-04-09T18:00
---

# Технологический журнал 1С: полное руководство

## 📌 Что Это

Технологический журнал (ТЖ) — инструмент диагностики платформы 1С:Предприятие для записи технических событий: SQL-запросы, блокировки, ошибки, вызовы, действия администратора.

**Отличие от журнала регистрации:** ЖР фиксирует бизнес-события (проведение документов), ТЖ — технические (запросы, блокировки, исключения).

---

## ⚙️ Настройка

### Расположение Файла `logcfg.xml`

| ОС | Путь |
|---|---|
| Windows | `C:\Program Files\1cv8\conf\logcfg.xml` |
| Windows (конкретная версия) | `C:\Program Files\1cv8\8.3.25.1394\bin\conf\logcfg.xml` |
| Linux | `/opt/1cv8/x86_64/current/conf/logcfg.xml` |

**Важно:**
- Перезапуск сервера не требуется — платформа перечитывает файл каждую минуту
- Каталог для логов должен существовать и иметь права на запись
- В каталоге логов не должно быть посторонних файлов

---

## 🔖 События (Name)

| Событие | Описание |
|---------|----------|
| `ADMIN` | Действия администратора кластера |
| `ATTN` | Мониторинг состояния кластера |
| `CALL` | Входящий удаленный вызов |
| `CLSTR` | Операции, изменяющие работу кластера |
| `CONN` | Установка/разрыв соединения с сервером |
| `DBMSSQL` | Выполнение SQL (MS SQL Server) |
| `DBPOSTGRS` | Выполнение SQL (PostgreSQL) |
| `DB2` | Выполнение SQL (Db2) |
| `DBORACLE` | Выполнение SQL (Oracle) |
| `DBV8DBEng` | Выполнение SQL (файловая БД) |
| `EXCP` | Исключительные ситуации (ошибки) |
| `EXCPCNTX` | События, не завершившиеся при ошибке |
| `HASP` | Обращение к аппаратному ключу защиты |
| `LEAKS` | Утечки памяти |
| `MEM` | Увеличение памяти процессами |
| `PROC` | Старт/завершение/авария процесса |
| `QERR` | Ошибки компиляции запросов |
| `SCALL` | Исходящий удаленный вызов |
| `SCOM` | Создание/удаление серверного контекста |
| `SDBL` | Исполнение запросов к модели данных 1С |
| `SESN` | Начало/окончание сеанса |
| `SRVC` | Запуск/остановка сервисов кластера |
| `SYSTEM` | Системные события (только по указанию 1С) |
| `TDEADLOCK` | Взаимная блокировка (дедлок) |
| `TLOCK` | Управляемая блокировка |
| `TTIMEOUT` | Таймаут ожидания блокировки |
| `VRSREQUEST` | Запрос к серверу за ресурсом |
| `VRSRESPONSE` | Ответ сервера |

---

## 🔖 Свойства Событий

| Свойство            | Описание                           | Пример                                           |
| ------------------- | ---------------------------------- | ------------------------------------------------ |
| `Usr`               | Имя пользователя ИБ                | `Usr=Иванов`                                     |
| `computerName`      | Имя компьютера                     | `computerName=srv-rds`                           |
| `p:processName`     | Имя информационной базы            | `p:processName=korp`                             |
| `T:clientID`        | ID соединения с клиентом по TCP    | `T:clientID=12345`                               |
| `T:applicationName` | Идентификатор клиентской программы | `T:applicationName=1CV8`                         |
| `T:connectID`       | Номер соединения с ИБ              | `T:connectID=156`                                |
| `SessionID`         | Номер сеанса (GUID)                | `SessionID=60405002-45dc-4d34-9767-8104cbc4a25a` |
| `duration`          | Длительность (микросекунды)        | `duration=1500000` (1.5 сек)                     |
| `context`           | Стек вызова 1С                     | `context='ОбщийМодуль.Модуль : 234'`             |
| `descr`             | Описание ошибки                    | `descr='Сеанс завершен администратором'`         |
| `sql`               | Текст SQL-запроса                  | `sql='SELECT * FROM Documents'`                  |
| `rows`              | Количество строк результата        | `rows=15000`                                     |
| `rowsaffected`      | Количество измененных строк        | `rowsaffected=0`                                 |
| `module`            | Имя модуля                         | `module='ОбщегоНазначения'`                      |
| `method`            | Имя метода                         | `method='ВыполнитьМетодКонфигурации'`            |
| `regions`           | Области блокировок                 | `regions='AccumRg789'`                           |
| `locks`             | Описание заблокированного ресурса  | `locks='Fld123=42:Exclusive'`                    |

---

## 🔧 Синтаксис Фильтров

### Где задаются

Фильтры задаются в файле `logcfg.xml` внутри элемента `<log>`.

### Общий вид

```xml
<event>
    <eq property="Name" value="EXCP"/>
</event>
```

### Операторы фильтрации

| Тег | Значение | Пример |
|-----|----------|--------|
| `eq` | равно | `<eq property="Name" value="EXCP"/>` |
| `ne` | не равно | `<ne property="Usr" value="admin"/>` |
| `gt` | больше | `<gt property="duration" value="1000000"/>` |
| `ge` | больше или равно | `<ge property="duration" value="1000000"/>` |
| `lt` | меньше | `<lt property="duration" value="500000"/>` |
| `le` | меньше или равно | `<le property="duration" value="500000"/>` |
| `like` | соответствие маске (`%` — любой набор символов) | `<like property="descr" value="%deadlock%"/>` |
| `in` | список значений | см. ниже |

### Логические операторы

#### `and` — все условия должны выполняться

```xml
<event>
    <and>
        <eq property="Name" value="EXCP"/>
        <like property="descr" value="%access%"/>
    </and>
</event>
```

#### `or` — хотя бы одно условие

```xml
<event>
    <or>
        <eq property="Name" value="EXCP"/>
        <eq property="Name" value="ELOG"/>
        <eq property="Name" value="DBMSSQL"/>
    </or>
</event>
```

#### `not` — отрицание

```xml
<event>
    <not>
        <eq property="Name" value="DBMSSQL"/>
    </not>
</event>
```

#### `in` — список значений

```xml
<event>
    <in property="Name">
        <value>EXCP</value>
        <value>DBMSSQL</value>
    </in>
</event>
```

### Полезные поля для фильтров

| Поле | Значение |
|------|----------|
| `Name` | Тип события (`EXCP`, `DBMSSQL`, `CALL`…) |
| `Usr` | Пользователь |
| `T:applicationName` | Имя приложения (тонкий клиент, сервер) |
| `p:processName` | Имя процесса (rphost, rmngr) |
| `SessionID` | UUID сессии |
| `descr` | Текст ошибки/описание |
| `context` | Контекст выполнения |
| `duration` | Длительность в микросекундах |

---

## 📄 Пример logcfg.xml (с комментариями)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!--
  Конфигурация журнала регистрации технологического журнала 1С:Предприятия 8.3
  Файл: logcfg.xml
  Документация: https://its.1c.ru/db/v8319doc#browse:17:-1:1701

  Префиксы свойств:
  - (без префикса) : глобальные свойства события
  - p:             : свойства процесса уровня ОС (родительский процесс)
  - t:             : свойства потока/сессии 1С (текущий контекст выполнения)
  - T:             : свойства клиентского соединения (тонкий/толстый клиент, веб-клиент)
  - query:         : свойства, специфичные для логов запросов к СУБД
  - er_excp:       : свойства для логов исключений и ошибок
-->
<config xmlns="http://v8.1c.ru/v8/tech-log">

    <!-- ========================================================= -->
    <!--                 ОСНОВНОЙ ЛОГ СЕРВЕРА                      -->
    <!-- ========================================================= -->
    <!--
      Журнал ключевых событий сервера 1С: запуск/остановка процессов,
      административные действия, события кластера, предупреждения.

      Параметры:
      - location : путь к папке для файлов лога (убедитесь в правах на запись)
      - history  : глубина ротации: количество дней хранения архивных файлов
    -->
    <log location="E:\1c_log\srv" history="12">
        <!-- Фильтрация по типу события (атрибут Name) -->
        <event><eq property="Name" value="ATTN"/></event>   <!-- Предупреждения и важные системные сообщения -->
        <event><eq property="Name" value="PROC"/></event>   <!-- Старт/остановка рабочих процессов (rphost, rmngr) -->
        <event><eq property="Name" value="ADMIN"/></event>  <!-- Действия администратора через консоль кластера -->
        <event><eq property="Name" value="CLSTR"/></event>  <!-- События управления кластером: регистрация, балансировка -->

        <!-- Свойства, записываемые в каждую строку лога -->
        <property name="t:processName"/>    <!-- Имя процесса 1С: rphost (рабочий), rmngr (менеджер) -->
        <property name="computerName"/>     <!-- Сетевое имя сервера/компьютера -->
        <property name="Usr"/>              <!-- Имя пользователя 1С (из списка пользователей ИБ) -->
        <property name="T:clientID"/>       <!-- Уникальный ID клиентского приложения -->
        <property name="T:applicationName"/><!-- Тип клиента: 1C:Enterprise, ThinClient, WebClient и т.п. -->
        <property name="T:connectID"/>      <!-- Внутренний ID соединения с сервером -->
        <property name="SessionID"/>        <!-- ID сессии 1С внутри рабочего процесса -->
        <property name="context"/>          <!-- Контекст: модуль, процедура, строка кода (если доступен) -->
        <property name="descr"/>            <!-- Человекочитаемое описание события -->
    </log>


    <!-- ========================================================= -->
    <!--              ДЛИТЕЛЬНЫЕ ВЫЗОВЫ (> 1 СЕКУНДЫ)              -->
    <!-- ========================================================= -->
    <!--
      Фиксирует вызовы методов с длительностью ≥ 1 секунды.
      Помогает выявлять "узкие места" в коде конфигурации или платформенных операциях.

      Единица измерения duration: микросекунды (1 сек = 1 000 000 мкс)
    -->
    <log location="E:\1c_log\LONG_CALLS" history="12">
        <event>
            <eq property="Name" value="CALL"/>              <!-- Событие: завершение вызова метода -->
            <ge property="duration" value="1000000"/>       <!-- Фильтр: длительность >= 1 000 000 мкс (1 сек) -->
        </event>

        <!-- Свойства для анализа производительности -->
        <property name="p:processName"/>    <!-- Родительский процесс ОС -->
        <property name="t:processName"/>    <!-- Процесс 1С, выполнивший вызов -->
        <property name="Usr"/>              <!-- Пользователь, инициировавший операцию -->
        <property name="computerName"/>     <!-- Хост выполнения -->
        <property name="T:connectID"/>      <!-- ID соединения -->
        <property name="SessionID"/>        <!-- ID сессии -->
        <property name="module"/>           <!-- Имя модуля, где расположен вызов -->
        <property name="method"/>           <!-- Имя вызванного метода/процедуры -->
        <property name="context"/>          <!-- Детали контекста: стек, параметры -->
    </log>


    <!-- ========================================================= -->
    <!--                 МОНИТОРИНГ ПАМЯТИ (MEM/LEAKS)            -->
    <!-- ========================================================= -->
    <!--
      Специализированный журнал для диагностики потребления памяти:
      - MEM   : периодические снимки использования памяти процессом
      - LEAKS : сигналы о потенциальных утечках (неосвобождённые объекты)

      Рекомендуется для отладки при росте потребления памяти rphost.
      history=24 — хранение до 24 файлов ротации.
    -->
    <log location="E:\1c_log\MEMORY" history="2">
        <event><eq property="Name" value="MEM"/></event>
        <event><eq property="Name" value="LEAKS"/></event>
        <event><eq property="Name" value="EXCP"/></event>

        <property name="p:processName"/>
        <property name="t:processName"/>
        <property name="Memory"/>
        <property name="MemoryPeak"/>
        <property name="Context"/>
        <property name="Descr"/>
        <property name="Usr"/>
    </log>


    <!-- ========================================================= -->
    <!--                ПРОБЛЕМНЫЕ БЛОКИРОВКИ                      -->
    <!-- ========================================================= -->
    <!--
      Регистрация проблем с блокировками данных:
      - TTIMEOUT : превышение времени ожидания блокировки (риск "зависаний")
      - TDEADLOCK: взаимная блокировка (deadlock) — требует немедленного анализа

      Критично для многопользовательских ИБ с интенсивной записью.
    -->
    <log location="E:\1c_log\LOCKS" history="12">
        <event><eq property="Name" value="TTIMEOUT"/></event>
        <event><eq property="Name" value="TDEADLOCK"/></event>

        <property name="p:processName"/>
        <property name="t:processName"/>
        <property name="T:connectID"/>
        <property name="Usr"/>
        <property name="regions"/>
        <property name="locks"/>
        <property name="context"/>
    </log>


    <!-- ========================================================= -->
    <!--              МЕДЛЕННЫЕ ЗАПРОСЫ К СУБД (> 0.5 СЕК)         -->
    <!-- ========================================================= -->
    <!--
      Отдельный журнал (пространство имён query:) для анализа запросов:
      - SDBL    : запросы на языке 1С, преобразованные в SQL
      - DBMSSQL : нативные запросы к СУБД (для MS SQL; для PostgreSQL — DBPGSQL и т.п.)

      Порог: 500 000 мкс = 0.5 секунды.
      Важно: требует включения "Регистрация запросов к СУБД" в настройках ИБ.
    -->
    <query:log xmlns:query="http://v8.1c.ru/v8/tech-log"
               location="E:\1c_log\Query1c"
               history="12">

        <query:event>
            <query:eq property="Name" value="SDBL"/>
            <query:ge property="duration" value="500000"/>
        </query:event>

        <query:event>
            <query:eq property="Name" value="DBMSSQL"/>
            <query:ge property="duration" value="500000"/>
        </query:event>

        <query:property name="p:processName"/>
        <query:property name="t:processName"/>
        <query:property name="computerName"/>
        <query:property name="T:connectID"/>
        <query:property name="Usr"/>
        <query:property name="Context"/>
        <query:property name="Sql"/>
        <query:property name="duration"/>
        <query:property name="rows"/>
        <query:property name="rowsaffected"/>
    </query:log>

    <!-- Генерация планов выполнения для медленных запросов -->
    <query:plansql xmlns:query="http://v8.1c.ru/v8/tech-log"
                   location="E:\1c_log\Query1c"/>


    <!-- ========================================================= -->
    <!--                  ПОЛНЫЕ ИСКЛЮЧЕНИЯ (ОШИБКИ)               -->
    <!-- ========================================================= -->
    <!--
      Журнал исключений (пространство er_excp:):
      - EXCP    : факт возникновения исключения
      - EXCPCNTX: детальный контекст (стек вызовов) на момент ошибки
    -->
    <er_excp:log xmlns:er_excp="http://v8.1c.ru/v8/tech-log"
                 location="E:\1c_log\ERROR_EXCP"
                 history="12">

        <er_excp:event>
            <er_excp:eq property="Name" value="EXCP"/>
        </er_excp:event>
        <er_excp:event>
            <er_excp:eq property="Name" value="EXCPCNTX"/>
        </er_excp:event>

        <er_excp:property name="context"/>
        <er_excp:property name="descr"/>
        <er_excp:property name="p:processName"/>
        <er_excp:property name="t:processName"/>
        <er_excp:property name="Usr"/>
        <er_excp:property name="computerName"/>
        <er_excp:property name="SessionID"/>
        <er_excp:property name="T:connectID"/>
    </er_excp:log>


    <!-- ========================================================= -->
    <!--                 ДАМПЫ ПРИ КРАШАХ ПРОЦЕССОВ                -->
    <!-- ========================================================= -->
    <!--
      Настройка создания дампов памяти (crash dump) при аварийном
      завершении процессов 1С.
      create="false" — авто-создание отключено (экономит место).
    -->
    <dump create="false"/>

</config>
```

---

## 🎯 Примеры полезных фильтров

### Только ошибки

```xml
<event>
    <eq property="Name" value="EXCP"/>
</event>
```

### Только медленные запросы

```xml
<event>
    <eq property="Name" value="DBMSSQL"/>
    <ge property="duration" value="500000"/>
</event>
```

### Только конкретный пользователь

```xml
<event>
    <eq property="Usr" value="Иванов"/>
</event>
```

### Всё кроме фоновых заданий

```xml
<event>
    <ne property="T:applicationName" value="BackgroundJob"/>
</event>
```

### Конкретная сессия

```xml
<event>
    <eq property="SessionID" value="c7d3a1b2-..."/>
</event>
```

### Боевой шаблон: ошибки + журнал + SQL

```xml
<event>
    <or>
        <eq property="Name" value="EXCP"/>
        <eq property="Name" value="ELOG"/>
        <eq property="Name" value="DBMSSQL"/>
    </or>
</event>
```

---

## 🔍 Пример Строки Лога

```
11:02.516052-0,EXCP,2,p:processName=korp,Usr=Иванов,computerName=srv-rds,T:connectID=156,SessionID=60405002-45dc-4d34-9767-8104cbc4a25a,Descr='src\rserver\src\RMngrCalls.cpp(536): Сеанс работы завершен администратором.',Context='ОбщийМодуль.СтандартныеПодсистемыСервер.Модуль : 53'
```

**Расшифровка:**
- `11:02.516052-0` — время и длительность
- `EXCP` — тип события (ошибка)
- `2` — уровень
- `p:processName=korp` — ИБ
- `Usr=Иванов` — пользователь
- `computerName=srv-rds` — компьютер
- `T:connectID=156` — ID соединения
- `Descr=...` — описание ошибки
- `Context=...` — стек вызова

---

## 📊 Частые Сценарии Использования

### 1. Найти медленные запросы

```bash
grep -E "DBMSSQL|DBPOSTGRS" /path/to/logs/*.log | grep "duration" | awk -F'duration=' '{if($2+0 > 5000000) print}'
```

### 2. Найти ошибки конкретного пользователя

```bash
findstr "Usr=Иванов" E:\1c_log\srv\*.log | findstr "EXCP"
```

### 3. Найти блокировки по конкретной базе

```bash
findstr "p:processName=korp" E:\1c_log\LOCKS\*.log
```

### 4. Найти долгие вызовы по конкретному модулю

```bash
findstr "module=ОбщегоНазначения" E:\1c_log\LONG_CALLS\*.log
```

---

## ⚠️ Важные замечания

1. **Имена свойств чувствительны к регистру**
   - ✅ `Usr` (не `usr`, не `t:Usr`)
   - ✅ `computerName` (не `computername`)
   - ✅ `T:connectID` (с двоеточием)

2. **Длительность в микросекундах**
   - 1 секунда = 1 000 000 мкс
   - 100 мс = 100 000 мкс

3. **Для продакшена используйте фильтры**
   - Не собирайте все события (`All=true`)
   - Устанавливайте пороги по длительности
   - Ограничивайте историю (24–72 часа)

4. **Права доступа**
   - Пользователь от имени которого работает 1С должен иметь полный доступ к каталогу логов
   - В каталоге не должно быть посторонних файлов

5. **Объём логов**
   - При полном сборе — гигабайты в час
   - При точечной настройке — десятки мегабайт в сутки

6. **Производительность**
   - ТЖ может **убить производительность**, если включить всё подряд
   - ✅ Включаем точечно
   - ❌ Никогда не включаем без фильтров на проде

---

## 🔗 Полезные ссылки

- [Руководство администратора 1С (раздел 3.17)](https://users.v8.1c.ru/Adm1936.aspx)
- [Обработка "Настройка технологического журнала" на ИТС](https://its.1c.ru/db/metod8dev/content/3474/hdoc)
- [Gilev.ru — Технологический журнал](http://www.gilev.ru/techjournal/)

---

## 📝 Версии

| Дата | Изменение |
|------|-----------|
| 2026-02-11 | Создание заметки |
| 2026-04-08 | Основные события, свойства, пример конфигурации |
| 2026-04-09 | Объединение с документацией по синтаксису фильтров |

---

**Теги:** #1C #TechLog #технологический_журнал #logcfg #диагностика #performance
