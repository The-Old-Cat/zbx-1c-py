#!/usr/bin/env bash
# Скрипт сборки пакетов для публикации

set -e

echo "============================================================"
echo "Сборка пакетов zbx-1c-rac и zbx-1c-techlog"
echo "============================================================"

# Переход в директорию проекта
cd "$(dirname "$0")/../.."

# Проверка наличия build
if ! python -m pip show build &> /dev/null; then
    echo "Установка build..."
    pip install build
fi

# Сборка zbx-1c-rac
echo ""
echo "============================================================"
echo "Сборка zbx-1c-rac"
echo "============================================================"
cd packages/zbx-1c-rac

# Очистка старых сборок
rm -rf dist/ build/ *.egg-info

# Сборка
python -m build

echo "✓ zbx-1c-rac собран"
ls -la dist/

cd ../..

# Сборка zbx-1c-techlog
echo ""
echo "============================================================"
echo "Сборка zbx-1c-techlog"
echo "============================================================"
cd packages/zbx-1c-techlog

# Очистка старых сборок
rm -rf dist/ build/ *.egg-info

# Сборка
python -m build

echo "✓ zbx-1c-techlog собран"
ls -la dist/

cd ../..

echo ""
echo "============================================================"
echo "Сборка завершена"
echo "============================================================"
echo "Пакеты для публикации:"
echo "  - packages/zbx-1c-rac/dist/*.whl"
echo "  - packages/zbx-1c-rac/dist/*.tar.gz"
echo "  - packages/zbx-1c-techlog/dist/*.whl"
echo "  - packages/zbx-1c-techlog/dist/*.tar.gz"
