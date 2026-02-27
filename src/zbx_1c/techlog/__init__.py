"""
Модуль для работы с техническим журналом 1С.

Чтение и парсинг логов событий 1С:Предприятия.
"""

from .reader import TechLogReader, LogEvent

__all__ = ["TechLogReader", "LogEvent"]
