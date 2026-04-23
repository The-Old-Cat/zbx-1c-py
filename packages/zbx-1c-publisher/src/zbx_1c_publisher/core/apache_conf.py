"""Модуль для управления конфигурацией Apache (алиасы 1С)."""

from __future__ import annotations

import logging
import platform
import re
import subprocess
from pathlib import Path
from typing import Optional

from .config import PublisherConfig

logger = logging.getLogger(__name__)


def get_onec_conf_path(config: PublisherConfig) -> Path:
    """Возвращает путь к файлу конфигурации публикаций 1С."""
    if config.apache_conf_path:
        # Путь относительно основного конфига
        return config.apache_conf_path.parent / "extra" / "httpd-1c.conf"

    # Путь по умолчанию
    if platform.system().lower() == "windows":
        return Path(config.APACHE_INSTALL_PATH_WIN) / "conf" / "extra" / "httpd-1c.conf"
    else:
        return Path("/etc/apache2/conf-available/httpd-1c.conf")


def ensure_1c_conf_included(config: PublisherConfig) -> bool:
    """Гарантирует, что httpd-1c.conf подключён в httpd.conf."""
    httpd_conf = config.apache_conf_path
    if not httpd_conf:
        if platform.system().lower() == "windows":
            httpd_conf = Path(config.APACHE_INSTALL_PATH_WIN) / "conf" / "httpd.conf"
        else:
            httpd_conf = Path("/etc/apache2/apache2.conf")

    onec_conf = get_onec_conf_path(config)
    include_line = f'Include "{str(onec_conf).replace(chr(92), "/")}"'

    # Создаём директорию если её нет
    onec_conf.parent.mkdir(parents=True, exist_ok=True)

    # Создаём файл если его нет
    if not onec_conf.exists():
        initial_content = """# ============================================
# Конфигурация публикаций 1С:Предприятие
# Автоматически сгенерировано zbx-1c-publisher
# ============================================

# Разрешаем выполнение CGI/1C веб-расширений
<IfModule mod_1cws.c>
    AddHandler 1cws-module .1cws
</IfModule>

# Настройки для директорий публикаций
<Directory "C:/Apache24/htdocs/prod">
    Options Indexes FollowSymLinks
    AllowOverride All
    Require all granted
    <IfModule mod_1cws.c>
        SetHandler 1cws-module
    </IfModule>
</Directory>

<Directory "C:/Apache24/htdocs/tech">
    Options Indexes FollowSymLinks
    AllowOverride All
    Require all granted
    <IfModule mod_1cws.c>
        SetHandler 1cws-module
    </IfModule>
</Directory>

# ============================================================
# Алиасы для конкретных баз (генерируются автоматически)
# Не редактируйте этот блок вручную
# ============================================================
"""
        onec_conf.write_text(initial_content, encoding="utf-8")
        logger.info("Создан файл конфигурации: %s", onec_conf)

    try:
        with open(httpd_conf, "r", encoding="utf-8") as f:
            content = f.read()
            if include_line in content:
                logger.debug("Include уже присутствует в %s", httpd_conf)
                return True
    except Exception as e:
        logger.warning("Не удалось прочитать %s: %s", httpd_conf, e)

    to_append = f"\n# 1C Auto-Publisher Configuration\n{include_line}\n"

    try:
        with open(httpd_conf, "a", encoding="utf-8") as f:
            f.write(to_append)
        logger.info("✓ Include добавлен в %s", httpd_conf)
        return True
    except PermissionError:
        logger.error("Нет прав на запись в %s", httpd_conf)
        return False
    except Exception as e:
        logger.error("Ошибка: %s", e)
        return False


def add_1c_alias_to_conf(
    base_name: str,
    publish_dir: Path,
    config: PublisherConfig,
    vrd_filename: str = "default.vrd",
) -> bool:
    """
    Добавляет алиас для опубликованной базы в httpd-1c.conf.

    Args:
        base_name: Имя базы (для URL)
        publish_dir: Директория публикации
        config: Конфигурация
        vrd_filename: Имя VRD файла (default.vrd)

    Returns:
        True если успешно
    """
    onec_conf = get_onec_conf_path(config)
    onec_conf.parent.mkdir(parents=True, exist_ok=True)

    # Нормализуем путь для Apache
    publish_path = str(publish_dir).replace("\\", "/")

    # Формируем блок конфигурации
    config_block = f"""
# 1c publication: {base_name}
Alias "/{base_name}" "{publish_path}/"
<Directory "{publish_path}">
    AllowOverride All
    Options None
    Require all granted
    SetHandler 1c-application
    ManagedApplicationDescriptor "{publish_path}/{vrd_filename}"
</Directory>
"""

    try:
        # Читаем существующий файл
        if onec_conf.exists():
            content = onec_conf.read_text(encoding="utf-8")
            # Проверяем, существует ли уже такой алиас
            if f'Alias "/{base_name}"' in content:
                logger.info("Алиас для /%s уже существует", base_name)
                return True

        # Добавляем новый алиас
        with open(onec_conf, "a", encoding="utf-8") as f:
            f.write(config_block)

        logger.info("✓ Добавлен алиас: /%s → %s", base_name, publish_dir)
        return True

    except Exception as e:
        logger.error("Ошибка при добавлении алиаса: %s", e)
        return False


def remove_1c_alias_from_conf(base_name: str, config: PublisherConfig) -> bool:
    """
    Удаляет алиас для базы из httpd-1c.conf.

    Args:
        base_name: Имя базы
        config: Конфигурация

    Returns:
        True если успешно
    """
    onec_conf = get_onec_conf_path(config)

    if not onec_conf.exists():
        logger.debug("Файл конфигурации не существует: %s", onec_conf)
        return True

    try:
        with open(onec_conf, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        skip_until_close = False
        removed = False

        for line in lines:
            # Проверяем начало блока
            if f'Alias "/{base_name}"' in line or f"# 1c publication: {base_name}" in line:
                skip_until_close = True
                removed = True
                continue

            # Если внутри блока, ждём закрывающий тег
            if skip_until_close:
                if "</Directory>" in line:
                    skip_until_close = False
                continue

            # Сохраняем строки вне удаляемого блока
            new_lines.append(line)

        if removed:
            with open(onec_conf, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            logger.info("✓ Удалён алиас для /%s", base_name)
        else:
            logger.debug("Алиас для /%s не найден", base_name)

        return True

    except Exception as e:
        logger.error("Ошибка при удалении алиаса: %s", e)
        return False


def list_1c_aliases(config: PublisherConfig) -> list[str]:
    """
    Возвращает список всех алиасов 1С из httpd-1c.conf.

    Args:
        config: Конфигурация

    Returns:
        Список имён баз
    """
    onec_conf = get_onec_conf_path(config)

    if not onec_conf.exists():
        return []

    aliases = []
    try:
        content = onec_conf.read_text(encoding="utf-8")
        for line in content.split("\n"):
            match = re.search(r'Alias "/([^"]+)"', line)
            if match:
                aliases.append(match.group(1))
        return aliases
    except Exception as e:
        logger.error("Ошибка при чтении алиасов: %s", e)
        return []


def validate_apache_config(config: PublisherConfig) -> tuple[bool, str]:
    """
    Проверяет синтаксис конфигурации Apache.

    Args:
        config: Конфигурация публикатора

    Returns:
        (успех, сообщение)
    """
    if not config.apache_conf_path:
        return False, "Путь к конфигурации Apache не указан"

    # Определяем путь к httpd.exe в зависимости от ОС
    system = platform.system().lower()

    if system == "windows":
        apache_bin = Path(config.APACHE_INSTALL_PATH_WIN) / "bin" / "httpd.exe"
    else:
        apache_bin = Path("/usr/sbin/apache2ctl")

    if not apache_bin.exists():
        return False, f"Apache binary not found: {apache_bin}"

    try:
        cmd = [str(apache_bin), "-t"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            logger.info("✓ Конфигурация Apache корректна")
            return True, "Syntax OK"
        else:
            error = result.stderr.strip() or result.stdout.strip()
            logger.error("Ошибка конфигурации Apache: %s", error)
            return False, error

    except subprocess.TimeoutExpired:
        return False, "Timeout при проверке конфигурации"
    except Exception as e:
        return False, str(e)
