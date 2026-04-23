"""CLI интерфейс для автопубликации 1С."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import click
from loguru import logger

from ..core import (
    PublisherConfig,
    generate_vrd_inplace,
    get_bases_from_server,
    publish_base,
    publish_multiple_bases,
    delete_publish,
    delete_multiple_bases,
    delete_all_published_bases,
    get_published_bases,
    validate_vrd,
    deploy_apache,
    check_apache_status,
    generate_default_vrd,
    disable_web_client_in_vrd,
    get_template_path,
    find_webinst,
    restart_apache_service,
    stop_apache_service,
    start_apache_service,
    get_apache_version,
    create_1c_conf_template,
    ensure_1c_conf_included,
)
from ..core.discovery import InfoBaseInfo


def setup_logging(log_level: str = "INFO", log_path: Optional[str] = None) -> None:
    """Настраивает логирование."""
    # Удаляем стандартные обработчики
    logger.remove()

    # Вывод в консоль
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    )

    # Файл логов (если указан путь)
    if log_path:
        log_dir = Path(log_path)
        log_dir.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_dir / "publisher.log",
            level=log_level,
            rotation="10 MB",
            retention="7 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        )

    # Перенаправляем стандартный logging в loguru
    class InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            logger_opt = logger.opt(depth=6, exception=record.exc_info)
            logger_opt.log(record.levelno, record.getMessage())

    logging.basicConfig(handlers=[InterceptHandler()], level=0)
    logging.getLogger().setLevel(logging.DEBUG)


@click.group()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=False),
    default=".env",
    help="Путь к файлу конфигурации",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default=None,
    help="Уровень логирования",
)
@click.pass_context
def cli(ctx: click.Context, config: str, log_level: Optional[str]) -> None:
    """Автопубликация информационных баз 1С:Предприятия.

    Инструмент для массовой публикации баз 1С с генерацией VRD-файлов
    на основе шаблонов FULL (все сервисы) или THIN (только OData/Аналитика).
    """
    ctx.ensure_object(dict)
    ctx.obj["config_file"] = config

    # Загружаем конфигурацию
    config_obj = PublisherConfig()

    # Переопределяем уровень логирования из CLI (если указан)
    final_log_level = log_level or config_obj.LOG_LEVEL
    setup_logging(final_log_level, config_obj.LOG_PATH)

    ctx.obj["config"] = config_obj


@cli.command()
@click.option("--mode", type=click.Choice(["FULL", "THIN"]), default=None, help="Режим публикации")
@click.option("--server", default=None, help="Адрес сервера 1С")
@click.pass_context
def list_bases(ctx: click.Context, mode: Optional[str], server: Optional[str]) -> None:
    """Вывести список информационных баз с сервера 1С."""
    config: PublisherConfig = ctx.obj["config"]

    if server:
        config.SERVER_1C_HOST = server

    if mode:
        config.PUBLISH_MODE = mode

    logger.info("Получение списка баз с сервера 1С: {}", config.SERVER_1C_HOST)

    try:
        bases = get_bases_from_server(config)

        click.echo("\n" + "=" * 70)
        click.echo(f"{'Имя базы':<30} | {'Описание':<35}")
        click.echo("=" * 70)

        for base in bases:
            should_publish = config.should_publish_base(base.name)
            status = "✓" if should_publish else "✗"
            click.echo(f"{status} {base.name:<28} | {base.description[:33]:<35}")

        click.echo("=" * 70)
        click.echo(f"Всего баз: {len(bases)}")
        click.echo(
            f"Будет опубликовано: {sum(1 for b in bases if config.should_publish_base(b.name))}"
        )
        click.echo()

    except Exception as e:
        logger.error("Ошибка при получении списка баз: {}", e)
        ctx.exit(1)


@cli.command()
@click.argument("base_name")
@click.option("--mode", type=click.Choice(["FULL", "THIN"]), default=None, help="Режим публикации")
@click.option("--tech-name", default=None, help="Техническое имя для публикации")
@click.option("--server", default=None, help="Адрес сервера 1С")
@click.option("--dry-run", is_flag=True, help="Тестовый режим (без реальной публикации)")
@click.pass_context
def publish(
    ctx: click.Context,
    base_name: str,
    mode: Optional[str],
    tech_name: Optional[str],
    server: Optional[str],
    dry_run: bool,
) -> None:
    """Опубликовать одну информационную базу."""
    config: PublisherConfig = ctx.obj["config"]

    if server:
        config.SERVER_1C_HOST = server

    if mode:
        config.PUBLISH_MODE = mode

    if tech_name is None:
        tech_name = f"{base_name}{config.TECH_SUFFIX}"

    logger.info("Публикация базы: {} (режим: {})", base_name, config.PUBLISH_MODE)

    if dry_run:
        logger.info("[DRY RUN] База {} → /{}", base_name, tech_name)
        logger.info("[DRY RUN] VRD будет сгенерирован из шаблона: {}", config.PUBLISH_MODE)
        return

    # Генерируем VRD в директории публикации
    publish_dir = config.get_publish_dir(base_name)
    vrd_filename = config.get_vrd_filename()
    publish_dir.mkdir(parents=True, exist_ok=True)

    # Создаём default.vrd
    generate_default_vrd(publish_dir, config, base_name)

    vrd_path = generate_vrd_inplace(
        base_name=base_name,
        tech_name=publish_dir.name,
        publish_dir=publish_dir,
        mode=config.PUBLISH_MODE,
        server=config.SERVER_1C_HOST,
        vrd_filename=vrd_filename,
    )

    if vrd_path is None:
        logger.error("Не удалось сгенерировать VRD-файл")
        ctx.exit(1)

    # Валидируем VRD
    if not validate_vrd(vrd_path):
        logger.error("VRD-файл не прошёл валидацию")
        ctx.exit(1)

    # Публикуем через webinst
    success, msg = publish_base(base_name, config, tech_name)

    if success:
        logger.info("База {} успешно опубликована как /{}", base_name, tech_name)
    else:
        logger.error("Ошибка публикации базы {}: {}", base_name, msg)
        ctx.exit(1)


@cli.command()
@click.option("--mode", type=click.Choice(["FULL", "THIN"]), default=None, help="Режим публикации")
@click.option("--prefix", default=None, help="Префикс баз для публикации")
@click.option("--exclude", default=None, help="Исключения (через запятую)")
@click.option("--server", default=None, help="Адрес сервера 1С")
@click.option("--dry-run", is_flag=True, help="Тестовый режим (без реальной публикации)")
@click.option("--skip-existing", is_flag=True, help="Пропускать уже опубликованные базы")
@click.pass_context
def publish_all(
    ctx: click.Context,
    mode: Optional[str],
    prefix: Optional[str],
    exclude: Optional[str],
    server: Optional[str],
    dry_run: bool,
    skip_existing: bool,
) -> None:
    """Опубликовать все информационные базы."""
    config: PublisherConfig = ctx.obj["config"]

    if server:
        config.SERVER_1C_HOST = server

    if mode:
        config.PUBLISH_MODE = mode

    if prefix:
        config.BASE_PREFIX = prefix

    if exclude:
        config.BASE_EXCLUDE = exclude

    logger.info("Публикация всех баз (режим: {})", config.PUBLISH_MODE)

    # Получаем список баз
    try:
        bases = get_bases_from_server(config)
    except Exception as e:
        logger.error("Ошибка при получении списка баз: {}", e)
        ctx.exit(1)

    # Фильтруем базы
    bases_to_publish = [b.name for b in bases if config.should_publish_base(b.name)]

    if not bases_to_publish:
        logger.warning("Нет баз для публикации")
        return

    logger.info("Будет опубликовано {} баз:", len(bases_to_publish))
    for base_name in bases_to_publish:
        logger.info("  - {}", base_name)

    if dry_run:
        logger.info("[DRY RUN] Реальная публикация не выполняется")
        return

    # Публикуем базы
    results = publish_multiple_bases(bases_to_publish, config, skip_existing=skip_existing)

    # Выводим отчёт
    success_count = sum(1 for success, _ in results.values() if success)
    fail_count = len(results) - success_count

    click.echo("\n" + "=" * 70)
    click.echo("ОТЧЁТ О ПУБЛИКАЦИИ")
    click.echo("=" * 70)

    for base_name, (success, msg) in results.items():
        status = "✓ OK" if success else f"✗ FAIL: {msg}"
        click.echo(f"  {base_name:<30} {status}")

    click.echo("=" * 70)
    click.echo(f"Успешно: {success_count}, Ошибок: {fail_count}")
    click.echo()

    if fail_count > 0:
        ctx.exit(1)


@cli.command()
@click.argument("base_name")
@click.option("--server", default=None, help="Адрес сервера 1С")
@click.pass_context
def unpublish(ctx: click.Context, base_name: str, server: Optional[str]) -> None:
    """Удалить публикацию информационной базы."""
    config: PublisherConfig = ctx.obj["config"]

    if server:
        config.SERVER_1C_HOST = server

    logger.info("Удаление публикации: {}", base_name)

    success, msg = delete_publish(base_name, config)

    if success:
        logger.info("Публикация {} успешно удалена", base_name)
    else:
        logger.error("Ошибка при удалении публикации {}: {}", base_name, msg)
        ctx.exit(1)


@cli.command()
@click.argument("vrd_file", type=click.Path(exists=True))
def validate(vrd_file: str) -> None:
    """Проверить валидность VRD-файла."""
    vrd_path = Path(vrd_file)
    logger.info("Проверка VRD-файла: {}", vrd_path)

    if validate_vrd(vrd_path):
        logger.info("VRD-файл валиден")
    else:
        logger.error("VRD-файл невалиден")
        sys.exit(1)


@cli.command("apache-deploy")
@click.option("--version", default=None, help="Версия Apache")
@click.option("--install-path", default=None, help="Путь установки")
@click.pass_context
def apache_deploy(ctx: click.Context, version: Optional[str], install_path: Optional[str]) -> None:
    """Установить и настроить Apache."""
    config: PublisherConfig = ctx.obj["config"]

    if version:
        config.APACHE_VERSION = version

    if install_path:
        config.APACHE_INSTALL_PATH_WIN = install_path

    logger.info("Развёртывание Apache {} ...", config.APACHE_VERSION)

    publish_root = Path(config.PUBLISH_ROOT)
    success, msg = deploy_apache(publish_root)

    if success:
        logger.info("Apache успешно развёрнут: {}", msg)
    else:
        logger.error("Ошибка развёртывания Apache: {}", msg)
        ctx.exit(1)


@cli.command("apache-status")
@click.pass_context
def apache_status(ctx: click.Context) -> None:
    """Проверить статус службы Apache."""
    logger.info("Проверка статуса Apache...")

    success, msg = check_apache_status()

    if success:
        logger.info("Статус Apache: {}", msg)
    else:
        logger.warning("Статус Apache: {}", msg)
        ctx.exit(1)


@cli.command("apache-restart")
@click.pass_context
def apache_restart(ctx: click.Context) -> None:
    """Перезапустить службу Apache."""
    logger.info("Перезапуск Apache...")

    success, msg = restart_apache_service()

    if success:
        logger.info("Apache успешно перезапущен: {}", msg)
    else:
        logger.error("Ошибка перезапуска Apache: {}", msg)
        ctx.exit(1)


@cli.command("apache-stop")
@click.pass_context
def apache_stop(ctx: click.Context) -> None:
    """Остановить службу Apache."""
    logger.info("Остановка Apache...")

    success, msg = stop_apache_service()

    if success:
        logger.info("Apache успешно остановлен: {}", msg)
    else:
        logger.error("Ошибка остановки Apache: {}", msg)
        ctx.exit(1)


@cli.command("apache-start")
@click.pass_context
def apache_start(ctx: click.Context) -> None:
    """Запустить службу Apache."""
    logger.info("Запуск Apache...")

    success, msg = start_apache_service()

    if success:
        logger.info("Apache успешно запущен: {}", msg)
    else:
        logger.error("Ошибка запуска Apache: {}", msg)
        ctx.exit(1)


@cli.command("apache-version")
@click.pass_context
def apache_version(ctx: click.Context) -> None:
    """Показать версию Apache."""
    version = get_apache_version()
    logger.info("Версия Apache: {}", version)
    click.echo(f"Apache version: {version}")


@cli.command("apache-config")
@click.pass_context
def apache_config(ctx: click.Context) -> None:
    """Создать конфигурацию для 1С в Apache."""
    config: PublisherConfig = ctx.obj["config"]

    publish_root = Path(config.PUBLISH_ROOT)
    conf_path = create_1c_conf_template(publish_root)
    logger.info("Создан файл конфигурации: {}", conf_path)

    # Подключаем в основной конфиг
    apache_conf = config.apache_conf_path
    if apache_conf and apache_conf.exists():
        ensure_1c_conf_included(apache_conf)
        logger.info("Конфиг подключён к {}", apache_conf)


def main() -> None:
    """Точка входа для CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
