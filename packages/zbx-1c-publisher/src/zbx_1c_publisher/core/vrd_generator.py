"""Модуль для генерации VRD-файлов из шаблонов."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Optional

try:
    from lxml import etree

    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False
    logging.getLogger(__name__).warning("lxml не установлен, используется fallback режим")


logger = logging.getLogger(__name__)

VRD_NS = {"vrd": "http://v8.1c.ru/8.2/virtual-resource-system"}


def get_template_path(mode: str = "FULL") -> Optional[Path]:
    """Возвращает путь к шаблону VRD."""
    template_name = "full.vrd" if mode.upper() == "FULL" else "thin.vrd"
    template_path = Path(__file__).parent.parent / "templates" / template_name

    if not template_path.exists():
        logger.error("Файл шаблона %s не найден!", template_name)
        return None

    return template_path


def generate_vrd_from_template(
    base_name: str,
    tech_name: str,
    mode: str = "FULL",
    server: str = "localhost",
    template_path: Optional[Path] = None,
) -> Optional[Path]:
    """Создаёт индивидуальный VRD-файл на основе шаблона."""
    if template_path is None:
        template_path = get_template_path(mode)

    if template_path is None or not template_path.exists():
        logger.error("Файл шаблона не найден!")
        return None

    try:
        tree = etree.parse(str(template_path))
        root = tree.getroot()
    except etree.XMLSyntaxError as e:
        logger.error("Ошибка парсинга шаблона: %s", e)
        return None

    root.set("base", f"/{tech_name}")
    ib_conn_str = f'Srvr="{server}";Ref="{base_name}";'
    root.set("ib", ib_conn_str)

    try:
        temp_vrd = Path(tempfile.gettempdir()) / f"temp_{tech_name}.vrd"
        tree.write(
            str(temp_vrd),
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=True,
        )
        logger.debug("VRD-файл сохранён: %s", temp_vrd)
        return temp_vrd
    except OSError as e:
        logger.error("Ошибка сохранения VRD-файла: %s", e)
        return None


def generate_vrd_inplace(
    base_name: str,
    tech_name: str,
    publish_dir: Path,
    mode: str = "FULL",
    server: str = "localhost",
    template_path: Optional[Path] = None,
    vrd_filename: str = "1cv8.vrd",
) -> Optional[Path]:
    """Создаёт VRD-файл непосредственно в директории публикации."""
    if template_path is None:
        template_path = get_template_path(mode)

    if template_path is None or not template_path.exists():
        logger.error("Файл шаблона не найден!")
        return None

    try:
        tree = etree.parse(str(template_path))
        root = tree.getroot()
    except etree.XMLSyntaxError as e:
        logger.error("Ошибка парсинга шаблона: %s", e)
        return None

    root.set("base", f"/{tech_name}")
    root.set("ib", f'Srvr="{server}";Ref="{base_name}";')

    vrd_file = publish_dir / vrd_filename
    try:
        tree.write(
            str(vrd_file),
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=True,
        )
        logger.info("VRD-файл сохранён: %s", vrd_file)
        return vrd_file
    except OSError as e:
        logger.error("Ошибка сохранения VRD-файла: %s", e)
        return None


def generate_default_vrd(publish_dir: Path, config, base_name: str) -> Optional[Path]:
    """
    Генерирует default.vrd в корневой директории публикации.

    Args:
        publish_dir: Директория публикации
        config: Конфигурация
        base_name: Имя базы

    Returns:
        Путь к созданному файлу или None
    """
    default_vrd_path = publish_dir.parent / "default.vrd"

    if default_vrd_path.exists():
        logger.debug("default.vrd уже существует: %s", default_vrd_path)
        return default_vrd_path

    try:
        content = f"""<?xml version="1.0" encoding="UTF-8"?>
<vrd xmlns="http://v8.1c.ru/v8/tech-data">
  <publish mode="http">
    <connection connectionString="Srvr={config.SERVER_1C_HOST};Ref={base_name};"/>
  </publish>
</vrd>"""

        with open(default_vrd_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("Default VRD-файл создан: %s", default_vrd_path)
        return default_vrd_path
    except Exception as e:
        logger.error("Ошибка при создании default.vrd: %s", e)
        return None


def disable_web_client_in_vrd(vrd_path: Path) -> bool:
    """
    Отключает веб-клиент в указанном VRD-файле.
    Добавляет <application enable="false"/> в корневой элемент.
    Для tech публикаций также отключает ненужные сервисы.

    Args:
        vrd_path: Путь к VRD-файлу

    Returns:
        True если успешно, False при ошибке
    """
    if not vrd_path.exists():
        logger.warning("VRD-файл не найден: %s", vrd_path)
        return False

    try:
        if LXML_AVAILABLE:
            tree = etree.parse(str(vrd_path))
            root = tree.getroot()

            # Отключаем веб-клиент
            app_elem = root.find(".//application")
            if app_elem is None:
                app_elem = etree.SubElement(root, "application")
            app_elem.set("enable", "false")

            # Отключаем веб-сервисы (для безопасности)
            ws_elem = root.find(".//ws")
            if ws_elem is not None:
                ws_elem.set("pointEnableCommon", "false")
                ws_elem.set("publishExtensionsByDefault", "false")

            # Отключаем HTTP-сервисы
            http_services = root.find(".//httpServices")
            if http_services is not None:
                http_services.set("publishExtensionsByDefault", "false")
                # Отключаем все сервисы внутри
                for service in http_services.findall(".//service"):
                    service.set("enable", "false")

            # Оставляем только OData и аналитику для мониторинга
            standard_odata = root.find(".//standardOdata")
            if standard_odata is not None:
                standard_odata.set("enable", "true")

            analytics = root.find(".//analytics")
            if analytics is not None:
                analytics.set("enable", "true")

            tree.write(str(vrd_path), encoding="utf-8", xml_declaration=True, pretty_print=True)
            logger.info("✅ Веб-клиент отключён в %s", vrd_path)
            logger.info("   Доступен только OData и аналитика для мониторинга")
        else:
            # Fallback без lxml
            with open(vrd_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Отключаем веб-клиент
            if "<application" not in content:
                content = content.replace("</point>", '  <application enable="false"/>\n</point>')
            else:
                content = content.replace(
                    '<application enable="true"', '<application enable="false"'
                )
                content = content.replace("<application>", '<application enable="false">')

            # Отключаем веб-сервисы
            content = content.replace('pointEnableCommon="true"', 'pointEnableCommon="false"')
            content = content.replace(
                'publishExtensionsByDefault="true"', 'publishExtensionsByDefault="false"'
            )

            # Отключаем HTTP сервисы
            content = content.replace('<service enable="true"', '<service enable="false"')

            # Включаем OData и аналитику
            content = content.replace('standardOdata enable="false"', 'standardOdata enable="true"')
            content = content.replace('analytics enable="false"', 'analytics enable="true"')

            with open(vrd_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info("✅ Веб-клиент отключён в %s (fallback)", vrd_path)

        return True

    except etree.XMLSyntaxError as e:
        logger.error("❌ Ошибка парсинга VRD-файла: %s", e)
        return False
    except Exception as e:
        logger.error("❌ Ошибка при отключении веб-клиента: %s", e)
        return False


def enable_web_client_in_vrd(vrd_path: Path) -> bool:
    """
    Включает веб-клиент в указанном VRD-файле.

    Args:
        vrd_path: Путь к VRD-файлу

    Returns:
        True если успешно, False при ошибке
    """
    if not vrd_path.exists():
        logger.warning("VRD-файл не найден: %s", vrd_path)
        return False

    try:
        if LXML_AVAILABLE:
            tree = etree.parse(str(vrd_path))
            root = tree.getroot()

            # Включаем веб-клиент
            app_elem = root.find(".//application")
            if app_elem is None:
                app_elem = etree.SubElement(root, "application")
            app_elem.set("enable", "true")

            tree.write(str(vrd_path), encoding="utf-8", xml_declaration=True, pretty_print=True)
            logger.info("✅ Веб-клиент включён в %s", vrd_path)
        else:
            with open(vrd_path, "r", encoding="utf-8") as f:
                content = f.read()

            content = content.replace('<application enable="false"', '<application enable="true"')
            content = content.replace("<application>", '<application enable="true">')

            with open(vrd_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info("✅ Веб-клиент включён в %s (fallback)", vrd_path)

        return True

    except Exception as e:
        logger.error("❌ Ошибка при включении веб-клиента: %s", e)
        return False


def validate_vrd(vrd_path: Path) -> bool:
    """Проверяет корректность VRD-файла."""
    if not vrd_path.exists():
        logger.error("VRD-файл не найден: %s", vrd_path)
        return False

    try:
        tree = etree.parse(str(vrd_path))
        root = tree.getroot()

        if "base" not in root.attrib:
            logger.error("Отсутствует атрибут 'base' в VRD-файле")
            return False

        if "ib" not in root.attrib:
            logger.error("Отсутствует атрибут 'ib' в VRD-файле")
            return False

        ib_str = root.get("ib", "")
        if "Srvr=" not in ib_str or "Ref=" not in ib_str:
            logger.error("Некорректная строка подключения: %s", ib_str)
            return False

        logger.info("✅ VRD-файл валиден: %s", vrd_path)
        return True

    except etree.XMLSyntaxError as e:
        logger.error("Невалидный XML в VRD-файле: %s", e)
        return False
    except Exception as e:
        logger.error("Ошибка при проверке VRD-файла: %s", e)
        return False


def get_vrd_info(vrd_path: Path) -> dict:
    """
    Получает информацию о VRD-файле.

    Args:
        vrd_path: Путь к VRD-файлу

    Returns:
        Словарь с информацией о VRD
    """
    info = {
        "path": str(vrd_path),
        "exists": vrd_path.exists(),
        "valid": False,
        "base": None,
        "ib": None,
        "web_client_enabled": None,
        "odata_enabled": None,
        "analytics_enabled": None,
    }

    if not vrd_path.exists():
        return info

    try:
        tree = etree.parse(str(vrd_path))
        root = tree.getroot()

        info["valid"] = True
        info["base"] = root.get("base")
        info["ib"] = root.get("ib")

        # Проверяем веб-клиент
        app_elem = root.find(".//application")
        if app_elem is not None:
            info["web_client_enabled"] = app_elem.get("enable") == "true"

        # Проверяем OData
        odata_elem = root.find(".//standardOdata")
        if odata_elem is not None:
            info["odata_enabled"] = odata_elem.get("enable") == "true"

        # Проверяем аналитику
        analytics_elem = root.find(".//analytics")
        if analytics_elem is not None:
            info["analytics_enabled"] = analytics_elem.get("enable") == "true"

    except Exception as e:
        logger.error("Ошибка при чтении VRD-файла: %s", e)

    return info
