# Скрипт сборки пакетов для публикации (PowerShell)

Write-Host "============================================================"
Write-Host "Сборка пакетов zbx-1c-rac и zbx-1c-techlog"
Write-Host "============================================================"

# Переход в директорию проекта
$projectRoot = Split-Path -Parent $PSScriptRoot | Split-Path -Parent
Set-Location $projectRoot

# Проверка наличия build
if (-not (pip show build)) {
    Write-Host "Установка build..."
    pip install build
}

# Функция для сборки пакета
function Build-Package {
    param(
        [string]$packageName,
        [string]$packagePath
    )

    Write-Host ""
    Write-Host "============================================================"
    Write-Host "Сборка $packageName"
    Write-Host "============================================================"
    Set-Location $packagePath

    # Очистка старых сборок
    Remove-Item -Recurse -Force dist, build, *.egg-info -ErrorAction SilentlyContinue

    # Сборка
    python -m build

    Write-Host "✓ $packageName собран"
    Get-ChildItem dist | Select-Object Name, Length

    Set-Location $projectRoot
}

# Сборка zbx-1c-rac
Build-Package -packageName "zbx-1c-rac" -packagePath "packages/zbx-1c-rac"

# Сборка zbx-1c-techlog
Build-Package -packageName "zbx-1c-techlog" -packagePath "packages/zbx-1c-techlog"

Write-Host ""
Write-Host "============================================================"
Write-Host "Сборка завершена"
Write-Host "============================================================"
Write-Host "Пакеты для публикации:"
Write-Host "  - packages/zbx-1c-rac/dist/*.whl"
Write-Host "  - packages/zbx-1c-rac/dist/*.tar.gz"
Write-Host "  - packages/zbx-1c-techlog/dist/*.whl"
Write-Host "  - packages/zbx-1c-techlog/dist/*.tar.gz"
