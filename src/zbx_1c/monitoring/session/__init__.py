"""
Модуль для работы с сессиями 1С
"""

from zbx_1c.monitoring.session.collector import SessionCollector, check_ras_availability

__all__ = ["SessionCollector", "check_ras_availability"]
