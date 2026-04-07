@echo off
REM Запуск FastAPI сервиса для мониторинга техжурнала 1С
REM Использование: start-techlog-api.bat [port]

set PORT=%1
if "%PORT%"=="" set PORT=8001

echo Starting Zabbix 1C TechJournal Monitoring API on port %PORT%...

cd /d "%~dp0.."
call .venv\Scripts\zbx-1c-techlog-api.exe --port %PORT%
