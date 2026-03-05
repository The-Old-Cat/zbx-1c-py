"""
Общие утилиты для пакетов zbx-1c-rac и zbx-1c-techlog.

Этот модуль можно использовать в обоих пакетах для избежания дублирования кода.
"""

from .logging import setup_logging, get_logger
from .config import BaseConfig

__all__ = [
    "setup_logging",
    "get_logger",
    "BaseConfig",
]
