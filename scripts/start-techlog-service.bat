@echo off
REM Запуск FastAPI сервиса техжурнала как фонового процесса
REM Использование: start-techlog-service.bat [port]

set PORT=%1
if "%PORT%"=="" set PORT=8001

echo Starting Zabbix 1C TechJournal Monitoring API service on port %PORT%...

cd /d "%~dp0.."
call uv run zbx-1c-techlog-api --port %PORT%

echo Service started in background.
echo API available at http://localhost:%PORT%
echo Swagger UI: http://localhost:%PORT%/docs
