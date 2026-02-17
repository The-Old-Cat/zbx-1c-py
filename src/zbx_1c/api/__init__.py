"""
API для интеграции с Zabbix
"""

from zbx_1c.api.main import app
from zbx_1c.api.routes import router

__all__ = ["app", "router"]
