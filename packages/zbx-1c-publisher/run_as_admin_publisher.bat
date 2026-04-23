@echo off
:: Проверка прав администратора
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ============================================================
    echo ВНИМАНИЕ: Скрипт не запущен от имени администратора!
    echo ============================================================
    echo Для корректной работы необходимы права администратора.
    echo.
    echo Пожалуйста, запустите этот файл от имени администратора:
    echo   1. Щёлкните правой кнопкой мыши по файлу
    echo   2. Выберите "Запуск от имени администратора"
    echo.
    pause
    exit /b 1
)

cd /d G:\Automation\zbx-1c-py
call .venv\Scripts\activate.bat
python packages\zbx-1c-publisher\run_publisher.py
pause