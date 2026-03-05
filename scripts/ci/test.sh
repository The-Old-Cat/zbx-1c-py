#!/usr/bin/env bash
# CI/CD скрипт для тестирования и сборки пакетов zbx-1c-rac и zbx-1c-techlog

set -e

echo "============================================================"
echo "CI/CD для zbx-1c-py"
echo "============================================================"

# Переход в директорию проекта
cd "$(dirname "$0")/../.."

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo "============================================================"
    echo -e "${YELLOW}$1${NC}"
    echo "============================================================"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Проверка наличия Python
print_header "Проверка окружения"
if ! command -v python3 &> /dev/null; then
    print_error "Python3 не найден"
    exit 1
fi
print_success "Python3: $(python3 --version)"

if ! command -v pip &> /dev/null; then
    print_error "pip не найден"
    exit 1
fi
print_success "pip: $(pip --version)"

# Установка зависимостей для разработки
print_header "Установка dev-зависимостей"
pip install pytest pytest-cov black mypy pylint

# Тестирование zbx-1c-rac
print_header "Тестирование zbx-1c-rac"
cd packages/zbx-1c-rac

echo "Установка пакета..."
pip install -e .

echo "Запуск тестов..."
pytest tests/ -v --tb=short

echo "Проверка типов (mypy)..."
mypy src/ --ignore-missing-imports || true

echo "Проверка стиля (pylint)..."
pylint src/ --disable=C0114,C0115,C0116,R0903,W0612 || true

print_success "zbx-1c-rac: тесты пройдены"
cd ../..

# Тестирование zbx-1c-techlog
print_header "Тестирование zbx-1c-techlog"
cd packages/zbx-1c-techlog

echo "Установка пакета..."
pip install -e .

echo "Запуск тестов..."
pytest tests/ -v --tb=short

echo "Проверка типов (mypy)..."
mypy src/ --ignore-missing-imports || true

echo "Проверка стиля (pylint)..."
pylint src/ --disable=C0114,C0115,C0116,R0903,W0612 || true

print_success "zbx-1c-techlog: тесты пройдены"
cd ../..

# Итоги
print_header "Итоги"
print_success "Все тесты пройдены!"
echo ""
echo "Пакеты готовы к публикации:"
echo "  - packages/zbx-1c-rac"
echo "  - packages/zbx-1c-techlog"
