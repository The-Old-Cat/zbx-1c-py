@echo off
REM Запуск FastAPI сервиса техжурнала
REM Использование: start-techlog-api.bat [port]

set PORT=%1
if "%PORT%"=="" set PORT=8001

echo Starting Zabbix 1C TechJournal Monitoring API service on port %PORT%...

cd /d "%~dp0..\packages\zbx-1c-techlog"
uv run --package zbx-1c-techlog zbx-1c-techlog-api --port %PORT%

echo.
echo Service started.
echo API available at http://localhost:%PORT%
echo Swagger UI: http://localhost:%PORT%/docs
