"""Модуль для публикации информационных баз через webinst."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import platform
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime

from .config import PublisherConfig
from .vrd_generator import generate_vrd_inplace, generate_default_vrd, disable_web_client_in_vrd
from .apache_conf import add_1c_alias_to_conf, remove_1c_alias_from_conf

logger = logging.getLogger(__name__)


def mask_sensitive_data(text: str) -> str:
    """Маскирует чувствительные данные в строке."""
    if not text:
        return text
    # Маскируем пароли
    text = re.sub(r"--cluster-pwd=\S+", "--cluster-pwd=***", text)
    text = re.sub(r"--cluster-user=\S+", "--cluster-user=***", text)
    text = re.sub(r"--pwd=\S+", "--pwd=***", text)
    text = re.sub(r"password=\S+", "password=***", text, flags=re.IGNORECASE)
    # Маскируем строки подключения
    text = re.sub(r"Srvr=\S+;Ref=\S+;", "Srvr=***;Ref=***;", text)
    # Маскируем имена пользователей в командах
    text = re.sub(r"--user=\S+", "--user=***", text)
    return text


def restart_apache(config: PublisherConfig) -> tuple[bool, str]:
    """Перезапускает Apache."""
    system = platform.system().lower()

    try:
        if system == "windows":
            apache_bin = Path(config.APACHE_INSTALL_PATH_WIN) / "bin" / "httpd.exe"
            service_name = config.APACHE_SERVICE_NAME

            if apache_bin.exists():
                # Пробуем перезапустить через службу
                result = subprocess.run(
                    ["net", "stop", service_name],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    shell=True,
                )
                result = subprocess.run(
                    ["net", "start", service_name],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    shell=True,
                )
                if result.returncode == 0:
                    logger.info("✅ Apache перезапущен через службу")
                    return True, "Apache restarted"

                # Если не получилось через службу, пробуем через httpd -k restart
                result = subprocess.run(
                    [str(apache_bin), "-k", "restart"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    shell=True,
                )
                if result.returncode == 0:
                    logger.info("✅ Apache перезапущен через httpd -k restart")
                    return True, "Apache restarted"
                else:
                    error = result.stderr.strip() or result.stdout.strip()
                    return False, f"Ошибка перезапуска: {error}"
            else:
                return False, f"Apache не найден: {apache_bin}"

        elif system == "linux":
            result = subprocess.run(
                ["systemctl", "restart", "apache2"], capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                logger.info("✅ Apache перезапущен")
                return True, "Apache restarted"
            else:
                return False, f"Ошибка перезапуска: {result.stderr}"
        else:
            return False, f"ОС {system} не поддерживается"

    except subprocess.TimeoutExpired:
        return False, "Таймаут при перезапуске Apache"
    except Exception as e:
        return False, f"Ошибка перезапуска Apache: {e}"


def find_webinst(config: PublisherConfig) -> Optional[Path]:
    """Ищет webinst с учётом версии из конфига."""
    system = platform.system().lower()
    exe_name = "webinst.exe" if system == "windows" else "webinst"

    # Если путь указан в конфиге
    if config.WEBINST_PATH:
        path = Path(config.WEBINST_PATH)
        if path.exists():
            logger.debug("webinst найден по пути из конфига: %s", path)
            return path

    paths = []
    if config.ONEC_VERSION:
        if system == "windows":
            paths = [
                Path(rf"C:\Program Files\1cv8\{config.ONEC_VERSION}\bin\{exe_name}"),
                Path(rf"C:\Program Files (x86)\1cv8\{config.ONEC_VERSION}\bin\{exe_name}"),
            ]
        else:
            paths = [Path(f"/opt/1cv8/x86_64/{config.ONEC_VERSION}/bin/{exe_name}")]

    # Стандартные пути
    if system == "windows":
        paths.append(Path(r"C:\Program Files\1cv8\bin\webinst.exe"))
        paths.append(Path(r"C:\Program Files (x86)\1cv8\bin\webinst.exe"))
    else:
        paths.append(Path("/opt/1cv8/bin/webinst"))

    for path in paths:
        if path.exists():
            logger.debug("webinst найден: %s", path)
            return path

    # Поиск в PATH
    webinst_in_path = shutil.which(exe_name)
    if webinst_in_path:
        return Path(webinst_in_path)

    logger.warning("webinst не найден")
    return None


def get_apache_conf_path(config: PublisherConfig) -> Optional[Path]:
    """Возвращает путь к конфигурационному файлу Apache."""
    if config.apache_conf_path and Path(config.apache_conf_path).exists():
        return Path(config.apache_conf_path)

    system = platform.system().lower()
    if system == "windows":
        return Path(config.APACHE_INSTALL_PATH_WIN) / "conf" / "httpd.conf"
    else:
        return Path("/etc/apache2/apache2.conf")


def create_temp_apache_conf(config: PublisherConfig) -> Path:
    """Создаёт временный конфиг Apache для webinst."""
    temp_conf = (
        Path(tempfile.gettempdir())
        / f"webinst_temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.conf"
    )

    publish_root = str(config.PUBLISH_ROOT).replace("\\", "/")
    apache_root = str(config.APACHE_INSTALL_PATH_WIN).replace("\\", "/")

    content = f"""# Temporary config for webinst
Listen 8080
ServerRoot "{apache_root}"
DocumentRoot "{publish_root}"
<Directory "{publish_root}">
    Options Indexes FollowSymLinks
    AllowOverride All
    Require all granted
</Directory>
"""
    temp_conf.write_text(content, encoding="utf-8")
    logger.debug("Создан временный конфиг: %s", temp_conf)
    return temp_conf


def publish_base(
    base_name: str,
    config: PublisherConfig,
    tech_name: Optional[str] = None,
    force: bool = False,
    auto_restart: bool = True,
) -> tuple[bool, str]:
    """Публикует базу с автоматической генерацией VRD."""
    logger.info("Публикация: %s", base_name)
    temp_conf = None
    result = False
    result_msg = ""

    try:
        publish_dir = config.get_publish_dir(base_name)
        vrd_filename = config.get_vrd_filename()
        publish_dir.mkdir(parents=True, exist_ok=True)

        # Создаём default.vrd
        generate_default_vrd(publish_dir, config, base_name)

        # Генерируем основной VRD
        vrd_path = generate_vrd_inplace(
            base_name=base_name,
            tech_name=tech_name or publish_dir.name,
            publish_dir=publish_dir,
            mode=config.PUBLISH_MODE,
            server=config.SERVER_1C_HOST,
            vrd_filename=vrd_filename,
        )
        if not vrd_path:
            return False, f"Не создан VRD: {vrd_filename}"

        webinst_exe = find_webinst(config)
        if not webinst_exe or not webinst_exe.exists():
            return False, "webinst.exe не найден"

        # Получаем путь к конфигу Apache
        apache_conf = get_apache_conf_path(config)

        # Если конфиг не найден, создаём временный
        if not apache_conf or not apache_conf.exists():
            temp_conf = create_temp_apache_conf(config)
            apache_conf = temp_conf

        # Формируем имя wsdir
        wsdir_name = tech_name if tech_name else publish_dir.name
        if config.PUBLISH_TYPE.upper() == "TECH":
            wsdir_name = base_name

        # Формируем команду
        cmd = [
            str(webinst_exe),
            "-publish",
            "-apache24",
            "-wsdir",
            wsdir_name,
            "-dir",
            str(publish_dir),
            "-connstr",
            f"Srvr={config.SERVER_1C_HOST};Ref={base_name};",
            "-descriptor",
            str(vrd_path),
            "-confPath",
            str(apache_conf),
        ]

        logger.debug("Команда: %s", mask_sensitive_data(" ".join(cmd)))

        # Выполняем команду
        encoding = "cp866" if platform.system().lower() == "windows" else "utf-8"
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            shell=platform.system().lower() == "windows",
            encoding=encoding,
            errors="replace",
        )

        # Проверяем результат
        output = proc.stdout.strip() if proc.stdout else ""
        error = proc.stderr.strip() if proc.stderr else ""

        if proc.returncode == 0:
            logger.info("✅ База %s опубликована", base_name)

            # Отключаем веб-клиент в VRD
            vrd_file = publish_dir / vrd_filename
            if vrd_file.exists():
                disable_web_client_in_vrd(vrd_file)

            # Добавляем алиас в конфиг Apache
            alias_name = wsdir_name
            add_1c_alias_to_conf(alias_name, publish_dir, config, vrd_filename)

            result = True
            result_msg = str(publish_dir)
        else:
            # Анализируем ошибку
            err_msg = error or output
            if "already exists" in err_msg.lower() or "существует" in err_msg.lower():
                logger.warning("Публикация уже существует: %s", base_name)
                result = True
                result_msg = "already exists"
            elif "access denied" in err_msg.lower() or "отказано в доступе" in err_msg.lower():
                result_msg = "Нет прав доступа. Запустите скрипт от имени администратора"
            else:
                result_msg = f"webinst error: {mask_sensitive_data(err_msg[:500])}"

        # Перезапускаем Apache после успешной публикации
        if result and auto_restart:
            logger.info("Перезапуск Apache...")
            restart_ok, restart_msg = restart_apache(config)
            if not restart_ok:
                logger.warning("Не удалось перезапустить Apache: %s", restart_msg)
                result_msg += f" (Apache не перезапущен: {restart_msg})"
            else:
                logger.info("✅ Apache перезапущен")
                result_msg += " (Apache перезапущен)"

        return result, result_msg

    except subprocess.TimeoutExpired:
        return False, "Таймаут 120 секунд"
    except Exception as e:
        logger.error(f"Ошибка публикации {base_name}: {e}", exc_info=True)
        return False, str(e)
    finally:
        # Удаляем временный конфиг
        if temp_conf and temp_conf.exists():
            try:
                temp_conf.unlink()
            except:
                pass


def delete_publish(
    base_name: str, config: PublisherConfig, delete_files: bool = True, auto_restart: bool = True
) -> tuple[bool, str]:
    """Полностью удаляет публикацию базы."""
    logger.info("Удаление публикации: %s", base_name)
    temp_conf = None
    result = False
    result_msg = ""

    try:
        publish_root = Path(config.PUBLISH_ROOT)

        # Нормализуем пути для Windows
        if platform.system().lower() == "windows":
            publish_root = Path(str(publish_root).replace("/", "\\"))

        # Пути для prod и tech
        prod_dir = publish_root / "prod" / base_name
        tech_name = f"{base_name}{config.TECH_SUFFIX}"
        tech_dir = publish_root / "tech" / tech_name

        deleted_dirs = []
        webinst_exe = find_webinst(config)

        # Функция для удаления через webinst
        def unpublish_with_webinst(wsdir: str, dir_path: Path) -> bool:
            if not webinst_exe or not webinst_exe.exists():
                return False

            # Получаем конфиг Apache
            apache_conf = get_apache_conf_path(config)

            if not apache_conf or not apache_conf.exists():
                temp_conf_local = create_temp_apache_conf(config)
                apache_conf = temp_conf_local
                nonlocal temp_conf
                temp_conf = temp_conf_local

            cmd = [
                str(webinst_exe),
                "-unpublish",
                "-apache24",
                "-wsdir",
                wsdir,
                "-confPath",
                str(apache_conf),
            ]

            try:
                encoding = "cp866" if platform.system().lower() == "windows" else "utf-8"
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    shell=platform.system().lower() == "windows",
                    encoding=encoding,
                )
                if proc.returncode == 0:
                    logger.info("Удалена публикация webinst: %s", wsdir)
                    return True
                else:
                    err = proc.stderr.strip() or proc.stdout.strip()
                    if "not found" not in err.lower() and "не найдена" not in err.lower():
                        logger.warning("Ошибка webinst: %s", err[:200])
            except Exception as e:
                logger.warning("Ошибка при вызове webinst: %s", e)
            return False

        # 1. Удаляем prod публикацию
        if prod_dir.exists():
            unpublish_with_webinst(base_name, prod_dir)

            if delete_files:
                shutil.rmtree(prod_dir, ignore_errors=True)
                logger.info("Директория prod удалена: %s", prod_dir)
                deleted_dirs.append(str(prod_dir))

        # 2. Удаляем tech публикацию
        if tech_dir.exists():
            unpublish_with_webinst(tech_name, tech_dir)

            if delete_files:
                shutil.rmtree(tech_dir, ignore_errors=True)
                logger.info("Директория tech удалена: %s", tech_dir)
                deleted_dirs.append(str(tech_dir))

        # 3. Удаляем алиас из httpd-1c.conf
        remove_1c_alias_from_conf(base_name, config)

        if not deleted_dirs:
            logger.info("Публикация %s не найдена", base_name)
            result = True
            result_msg = "not found"
        else:
            result = True
            result_msg = f"Deleted: {', '.join(deleted_dirs)}"

        # Перезапускаем Apache после успешного удаления
        if result and auto_restart and deleted_dirs:
            logger.info("Перезапуск Apache...")
            restart_ok, restart_msg = restart_apache(config)
            if not restart_ok:
                logger.warning("Не удалось перезапустить Apache: %s", restart_msg)
                result_msg += f" (Apache не перезапущен: {restart_msg})"
            else:
                logger.info("✅ Apache перезапущен")
                result_msg += " (Apache перезапущен)"

        return result, result_msg

    except PermissionError as e:
        logger.error("Ошибка прав доступа при удалении: %s", e)
        return False, f"Нет прав доступа. Запустите скрипт от имени администратора: {e}"
    except Exception as e:
        logger.error("Ошибка при удалении: %s", e)
        return False, f"Ошибка при удалении: {e}"
    finally:
        if temp_conf and temp_conf.exists():
            try:
                temp_conf.unlink()
            except:
                pass


def publish_multiple_bases(
    bases: list[str],
    config: PublisherConfig,
    skip_existing: bool = False,
    auto_restart: bool = True,
) -> dict[str, tuple[bool, str]]:
    """Публикует список баз."""
    results = {}
    need_restart = False

    for base in bases:
        if not config.should_publish_base(base):
            logger.info("Пропуск (фильтр): %s", base)
            results[base] = (True, "skipped by filter")
            continue
        publish_dir = config.get_publish_dir(base)
        if skip_existing and publish_dir.exists():
            results[base] = (True, "exists")
            continue

        # Публикуем без автоматического перезапуска каждой базы
        result, msg = publish_base(base, config, auto_restart=False)
        results[base] = (result, msg)
        if result:
            need_restart = True

    # Один раз перезапускаем Apache после публикации всех баз
    if need_restart and auto_restart:
        logger.info("Перезапуск Apache после публикации всех баз...")
        restart_ok, restart_msg = restart_apache(config)
        if not restart_ok:
            logger.warning("Не удалось перезапустить Apache: %s", restart_msg)
            # Добавляем предупреждение к результатам
            for base in results:
                if results[base][0]:
                    results[base] = (
                        results[base][0],
                        f"{results[base][1]} (Apache NOT restarted: {restart_msg})",
                    )
        else:
            logger.info("✅ Apache успешно перезапущен")
            for base in results:
                if results[base][0]:
                    results[base] = (results[base][0], f"{results[base][1]} (Apache restarted)")

    return results


def delete_multiple_bases(
    bases: list[str],
    config: PublisherConfig,
    delete_files: bool = True,
    auto_restart: bool = True,
) -> dict[str, tuple[bool, str]]:
    """Удаляет публикации нескольких баз."""
    logger.info("Массовое удаление %d баз", len(bases))

    results = {}
    need_restart = False

    for base in bases:
        if not config.should_publish_base(base):
            logger.info("Пропуск (фильтр): %s", base)
            results[base] = (True, "skipped by filter")
            continue

        # Удаляем без автоматического перезапуска каждой базы
        success, msg = delete_publish(base, config, delete_files=delete_files, auto_restart=False)
        results[base] = (success, msg)
        if success and "not found" not in msg:
            need_restart = True
        logger.info("  %s: %s", base, "OK" if success else "ERR")

    # Один раз перезапускаем Apache после удаления всех баз
    if need_restart and auto_restart:
        logger.info("Перезапуск Apache после удаления всех баз...")
        restart_ok, restart_msg = restart_apache(config)
        if not restart_ok:
            logger.warning("Не удалось перезапустить Apache: %s", restart_msg)
            for base in results:
                if results[base][0] and "not found" not in results[base][1]:
                    results[base] = (
                        results[base][0],
                        f"{results[base][1]} (Apache NOT restarted: {restart_msg})",
                    )
        else:
            logger.info("✅ Apache успешно перезапущен")
            for base in results:
                if results[base][0] and "not found" not in results[base][1]:
                    results[base] = (results[base][0], f"{results[base][1]} (Apache restarted)")

    success_count = sum(1 for v in results.values() if v[0])
    logger.info("Массовое удаление завершено. Успешно: %d/%d", success_count, len(bases))
    return results


def delete_all_published_bases(
    config: PublisherConfig, delete_files: bool = True, auto_restart: bool = True
) -> dict[str, tuple[bool, str]]:
    """Удаляет ВСЕ опубликованные базы."""
    logger.info("Удаление ВСЕХ опубликованных баз")

    publish_root = Path(config.PUBLISH_ROOT)
    prod_dir = publish_root / "prod"
    tech_dir = publish_root / "tech"

    all_bases = []

    if prod_dir.exists():
        for item in prod_dir.iterdir():
            if item.is_dir():
                all_bases.append(item.name)

    if tech_dir.exists():
        for item in tech_dir.iterdir():
            if item.is_dir():
                name = item.name
                if name.endswith(config.TECH_SUFFIX):
                    name = name[: -len(config.TECH_SUFFIX)]
                all_bases.append(name)

    all_bases = list(set(all_bases))

    if not all_bases:
        logger.info("Нет опубликованных баз для удаления")
        return {}

    logger.info("Найдено опубликованных баз: %d", len(all_bases))
    return delete_multiple_bases(all_bases, config, delete_files, auto_restart)


def get_published_bases(config: PublisherConfig) -> list[str]:
    """Возвращает список опубликованных баз."""
    publish_root = Path(config.PUBLISH_ROOT)
    prod_dir = publish_root / "prod"
    tech_dir = publish_root / "tech"

    published = []

    if prod_dir.exists():
        for item in prod_dir.iterdir():
            if item.is_dir():
                vrd_files = list(item.glob("*.vrd"))
                if vrd_files:
                    published.append(item.name)
                    logger.debug(f"Найдена публикация в prod: {item.name}")

    if tech_dir.exists():
        for item in tech_dir.iterdir():
            if item.is_dir():
                vrd_files = list(item.glob("*.vrd"))
                if vrd_files:
                    name = item.name
                    if name.endswith(config.TECH_SUFFIX):
                        name = name[: -len(config.TECH_SUFFIX)]
                    published.append(name)
                    logger.debug(f"Найдена публикация в tech: {item.name} -> {name}")

    published = list(set(published))
    logger.info("Найдено опубликованных баз: %d", len(published))
    return published
