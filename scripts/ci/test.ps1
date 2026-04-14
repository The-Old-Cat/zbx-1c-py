# CI/CD скрипт для тестирования и сборки пакета zbx-1c-techlog (PowerShell)

Write-Host "============================================================"
Write-Host "CI/CD для zbx-1c-py"
Write-Host "============================================================"

# Переход в директорию проекта
$projectRoot = Split-Path -Parent $PSScriptRoot | Split-Path -Parent
Set-Location $projectRoot

function Print-Header {
    param([string]$text)
    Write-Host ""
    Write-Host "============================================================"
    Write-Host $text -ForegroundColor Yellow
    Write-Host "============================================================"
}

function Print-Success {
    param([string]$text)
    Write-Host "✓ $text" -ForegroundColor Green
}

function Print-Error {
    param([string]$text)
    Write-Host "✗ $text" -ForegroundColor Red
}

# Проверка наличия Python
Print-Header "Проверка окружения"
try {
    $pythonVersion = python --version 2>&1
    Print-Success "Python: $pythonVersion"
}
catch {
    Print-Error "Python не найден"
    exit 1
}

try {
    $pipVersion = pip --version 2>&1
    Print-Success "pip: $pipVersion"
}
catch {
    Print-Error "pip не найден"
    exit 1
}

# Установка зависимостей для разработки
Print-Header "Установка dev-зависимостей"
pip install pytest pytest-cov black mypy pylint

# Функция для тестирования пакета
function Test-Package {
    param(
        [string]$packageName,
        [string]$packagePath
    )

    Print-Header "Тестирование $packageName"
    Set-Location $packagePath

    Write-Host "Установка пакета..."
    pip install -e .

    Write-Host "Запуск тестов..."
    pytest tests/ -v --tb=short
    if ($LASTEXITCODE -ne 0) {
        Print-Error "$packageName: тесты не пройдены"
        Set-Location $projectRoot
        exit 1
    }

    Write-Host "Проверка типов (mypy)..."
    mypy src/ --ignore-missing-imports

    Write-Host "Проверка стиля (pylint)..."
    pylint src/ --disable=C0114, C0115, C0116, R0903, W0612

    Print-Success "$packageName: тесты пройдены"
    Set-Location $projectRoot
}

# Тестирование zbx-1c-techlog
Test-Package -packageName "zbx-1c-techlog" -packagePath "packages/zbx-1c-techlog"

# Итоги
Print-Header "Итоги"
Print-Success "Все тесты пройдены!"
Write-Host ""
Write-Host "Пакет готов к публикации:"
Write-Host "  - packages/zbx-1c-techlog"
