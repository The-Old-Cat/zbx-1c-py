from typing import Optional


class Zabbix1CError(Exception):
    """Базовое исключение приложения"""

    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class RACNotFoundError(Zabbix1CError):
    """Утилита rac не найдена"""

    pass


class RACConnectionError(Zabbix1CError):
    """Ошибка подключения к RAS"""

    pass


class RACExecutionError(Zabbix1CError):
    """Ошибка выполнения команды rac"""

    pass


class ClusterNotFoundError(Zabbix1CError):
    """Кластер не найден"""

    pass


class AuthenticationError(Zabbix1CError):
    """Ошибка аутентификации"""

    pass


class ParseError(Zabbix1CError):
    """Ошибка парсинга вывода rac"""

    pass
