#!/usr/bin/env python3
"""
Точка входа для запуска как модуля
python -m zbx_1c [command]
"""

from .cli.commands import cli


def main():
    """Основная функция"""
    cli()


if __name__ == "__main__":
    main()
