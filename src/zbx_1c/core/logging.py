from loguru import logger

from .config import get_settings


def setup_logging() -> None:
    """Настройка логирования - только ошибки в файл"""
    settings = get_settings()

    # Удаляем все стандартные обработчики
    logger.remove()

    # Формат для файла (только дата, уровень и сообщение)
    file_format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"

    # Добавляем файловый вывод только для ошибок
    log_file = settings.log_path / "zbx-1c-error-{time:YYYY-MM-DD}.log"
    logger.add(
        log_file,
        format=file_format,
        level="ERROR",  # Только ошибки и выше
        rotation="1 day",
        retention="30 days",
        compression="gz",
        encoding="utf-8",
        backtrace=False,
        diagnose=False,
    )

    # В режиме debug все равно ничего не выводим в консоль
    # Только ошибки в файл


def get_logger(name: str):
    """Получение логгера для модуля"""
    return logger.bind(module=name)
