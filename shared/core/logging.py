"""
Настройка логирования для проектов zbx-1c.

Использует loguru для удобного логирования с поддержкой цветов и ротации.
"""

import sys
from pathlib import Path
from typing import Optional, Union

from loguru import logger


def setup_logging(
    log_path: Optional[Union[str, Path]] = None,
    level: str = "INFO",
    debug: bool = False,
    rotation: str = "10 MB",
    retention: str = "7 days",
    format_str: Optional[str] = None,
) -> None:
    """
    Настройка логирования.

    Args:
        log_path: Путь к файлу лога. Если None, логи только в консоль.
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        debug: Если True, устанавливает уровень DEBUG.
        rotation: Когда ротировать лог (например, "10 MB", "1 day").
        retention: Сколько хранить логов (например, "7 days", "1 month").
        format_str: Формат сообщения лога.
    """
    # Удаляем стандартный обработчик
    logger.remove()

    # Формат по умолчанию
    if format_str is None:
        format_str = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    # Уровень логирования
    log_level = "DEBUG" if debug else level

    # Консольный вывод с цветами
    logger.add(
        sys.stderr,
        level=log_level,
        format=format_str,
        colorize=True,
    )

    # Файловый вывод (если указан путь)
    if log_path:
        log_file = Path(log_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_file / "app.log",
            level=log_level,
            format=format_str,
            rotation=rotation,
            retention=retention,
            compression="zip",
            enqueue=True,  # Асинхронная запись
        )


def get_logger(name: str = __name__):
    """
    Получить экземпляр логгера.

    Args:
        name: Имя логгера (обычно __name__).

    Returns:
        Экземпляр logger для использования в модуле.
    """
    return logger.bind(name=name)
