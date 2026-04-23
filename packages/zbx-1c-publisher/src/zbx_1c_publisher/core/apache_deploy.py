"""Модуль для развёртывания и настройки Apache для 1С (кроссплатформенный)."""

from __future__ import annotations

import ctypes
import logging
import os
import platform
import re
import socket
import subprocess
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ============================================================
# Константы по умолчанию
# ============================================================
APACHE_VERSION = os.environ.get("APACHE_VERSION", "2.4.66")
APACHE_VS = os.environ.get("APACHE_VS", "VS18")
APACHE_ZIP_NAME = f"httpd-{APACHE_VERSION}-260223-Win64-{APACHE_VS}.zip"
APACHE_DOWNLOAD_URL = os.environ.get(
    "APACHE_DOWNLOAD_URL",
    f"https://www.apachelounge.com/download/{APACHE_VS}/binaries/{APACHE_ZIP_NAME}",
)
APACHE_FALLBACK_URL = os.environ.get("APACHE_FALLBACK_URL", "")
APACHE_ZIP_TEMP = Path(os.environ.get("APACHE_ZIP_TEMP", "apache_temp.zip"))
DOWNLOAD_TIMEOUT = int(os.environ.get("DOWNLOAD_TIMEOUT", "300"))

# Список портов для проверки в порядке приоритета
DEFAULT_PORTS = [80, 8080, 8443, 8888, 9090, 10080, 10081, 10082]


# ============================================================
# Пути для разных ОС
# ============================================================


def get_install_path() -> Path:
    """Возвращает путь установки Apache в зависимости от ОС."""
    sys_platform = platform.system().lower()
    if sys_platform == "windows":
        return Path(os.environ.get("APACHE_INSTALL_PATH_WIN", r"C:\Apache24"))
    elif sys_platform == "linux":
        return Path(os.environ.get("APACHE_INSTALL_PATH_LINUX", "/etc/apache2"))
    return Path("/etc/apache2")


def get_httpd_exe() -> Path:
    """Возвращает путь к исполняемому файлу Apache."""
    install_path = get_install_path()
    if platform.system().lower() == "windows":
        return install_path / "bin" / "httpd.exe"
    return install_path / "bin" / "httpd"


def get_apache_conf_dir() -> Path:
    """Возвращает путь к директории конфигурации Apache."""
    install_path = get_install_path()
    if platform.system().lower() == "windows":
        return install_path / "conf"
    return Path("/etc/apache2")


def get_onec_conf_path() -> Path:
    """Возвращает путь к файлу конфигурации публикаций 1С."""
    conf_dir = get_apache_conf_dir()
    if platform.system().lower() == "windows":
        return conf_dir / "extra" / "httpd-1c.conf"
    return conf_dir / "conf-available" / "httpd-1c.conf"


def get_service_name() -> str:
    """Возвращает имя службы Apache в зависимости от ОС."""
    if platform.system().lower() == "windows":
        return os.environ.get("APACHE_SERVICE_NAME", "Apache2.4")
    return "apache2"


# ============================================================
# Проверка прав администратора
# ============================================================


def is_admin() -> tuple[bool, str]:
    """Проверяет наличие прав администратора."""
    sys_platform = platform.system().lower()

    if sys_platform == "windows":
        try:
            return (
                ctypes.windll.shell32.IsUserAnAdmin() != 0,
                "Нужны права администратора.",
            )
        except AttributeError:
            return False, "Ошибка проверки прав Windows."

    if sys_platform == "linux":
        if hasattr(os, "getuid"):
            return os.getuid() == 0, "Нужны права root (sudo)."
        return False, "os.getuid недоступен."

    return True, ""


# ============================================================
# Работа с портами (кросс-платформенно)
# ============================================================


def is_port_free(port: int) -> bool:
    """Проверяет, свободен ли порт (IPv4 и IPv6)."""
    try:
        # Проверяем IPv4
        sock4 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock4.settimeout(1)
        result4 = sock4.connect_ex(("127.0.0.1", port))
        sock4.close()

        # Проверяем IPv6
        sock6 = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock6.settimeout(1)
        result6 = sock6.connect_ex(("::1", port))
        sock6.close()

        return result4 != 0 and result6 != 0
    except Exception:
        return False


def find_free_port(start_ports: Optional[list[int]] = None) -> int:
    """
    Ищет свободный порт.

    Args:
        start_ports: Список портов для проверки в первую очередь

    Returns:
        Свободный порт
    """
    to_check = start_ports if start_ports else DEFAULT_PORTS.copy()

    for port in to_check:
        if is_port_free(port):
            logger.info("Порт %d свободен.", port)
            return port

    # Расширенный поиск
    for port in range(10000, 10100):
        if is_port_free(port):
            logger.info("Порт %d свободен.", port)
            return port

    # Если ничего не нашли, возвращаем 8080 как запасной вариант
    logger.warning("Не удалось найти свободный порт, использую 8080")
    return 8080


def change_listen_port(conf_file: Path, new_port: int) -> bool:
    """
    Меняет порт Listen в конфигурационном файле Apache.

    Args:
        conf_file: Путь к конфигурационному файлу
        new_port: Новый порт

    Returns:
        True если успешно, False в противном случае
    """
    if not conf_file.exists():
        logger.error("Файл конфигурации не найден: %s", conf_file)
        return False

    try:
        content = conf_file.read_text(encoding="utf-8")
        original_content = content

        # Замена Listen 80 -> Listen new_port
        content = re.sub(r"^Listen\s+\d+", f"Listen {new_port}", content, flags=re.MULTILINE)

        # Замена Listen 0.0.0.0:80 -> Listen new_port
        content = re.sub(
            r"^Listen\s+[\d.:]+:\d+", f"Listen {new_port}", content, flags=re.MULTILINE
        )

        # Замена Listen [::]:80 -> Listen new_port
        content = re.sub(r"^Listen\s+\[::\]:\d+", f"Listen {new_port}", content, flags=re.MULTILINE)

        if content != original_content:
            conf_file.write_text(content, encoding="utf-8")
            logger.info("Порт изменён на %d в %s", new_port, conf_file)
            return True

        logger.debug("Listen директива уже настроена на порт %d", new_port)
        return True

    except Exception as e:
        logger.error("Ошибка при изменении порта: %s", e)
        return False


def ensure_free_port(
    conf_dir: Path,
    conf_files: Optional[list[str]] = None,
    start_ports: Optional[list[int]] = None,
) -> int:
    """
    Гарантирует свободный порт, меняя конфиг при необходимости.

    Args:
        conf_dir: Директория с конфигурационными файлами
        conf_files: Список файлов для проверки
        start_ports: Список портов для проверки

    Returns:
        Установленный порт
    """
    free_port = find_free_port(start_ports)

    if conf_files is None:
        if platform.system().lower() == "windows":
            conf_files = ["httpd.conf"]
        else:
            conf_files = ["ports.conf", "apache2.conf"]

    for name in conf_files:
        conf_file = conf_dir / name
        if conf_file.exists():
            change_listen_port(conf_file, free_port)
            break

    return free_port


# ============================================================
# Утилиты: выполнение команд
# ============================================================


def run_cmd(cmd: list[str], check: bool = False) -> tuple[bool, str]:
    """
    Выполняет команду.

    Args:
        cmd: Команда и аргументы
        check: Проверять ли код возврата

    Returns:
        Кортеж (успех, вывод stderr)
    """
    logger.debug("Выполняется: %s", " ".join(cmd))
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, check=check, encoding="utf-8", errors="replace"
        )
        if proc.stdout.strip():
            logger.debug("stdout: %s", proc.stdout.strip())
        if proc.stderr.strip():
            logger.debug("stderr: %s", proc.stderr.strip())
        return proc.returncode == 0, proc.stderr.strip()
    except FileNotFoundError:
        logger.error("Команда не найдена: %s", cmd[0])
        return False, "Команда не найдена"
    except subprocess.CalledProcessError as e:
        logger.error("Ошибка выполнения: %s", e)
        return False, str(e)


# ============================================================
# Загрузка файлов
# ============================================================


def is_valid_zip(path: Path) -> bool:
    """Проверяет, что файл является корректным ZIP-архивом."""
    if not path.exists():
        return False
    try:
        with open(path, "rb") as f:
            header = f.read(4)
            return header[:2] == b"PK"
    except OSError:
        return False


def download_file(url: str, dest: Path) -> bool:
    """Скачивает файл с проверкой."""
    logger.info("Скачивание: %s", url)
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
            data = resp.read()
            with open(dest, "wb") as f:
                f.write(data)
            logger.info("Скачано %d байт в %s", len(data), dest)
            return True
    except urllib.error.HTTPError as e:
        logger.error("HTTP ошибка %d: %s", e.code, e.reason)
        return False
    except urllib.error.URLError as e:
        logger.error("Ошибка сети: %s", e.reason)
        return False
    except Exception as e:
        logger.error("Ошибка скачивания: %s", e)
        return False


def cleanup_zip() -> None:
    """Удаляет временный zip-файл."""
    if APACHE_ZIP_TEMP.exists():
        try:
            APACHE_ZIP_TEMP.unlink()
        except OSError:
            pass


# ============================================================
# Конфигурация для 1С
# ============================================================


def create_1c_conf_template(publish_root: Path, output_path: Optional[Path] = None) -> Path:
    """Создаёт шаблон конфигурации для 1С."""
    if output_path is None:
        output_path = get_onec_conf_path()

    htdocs_path = str(publish_root).replace("\\", "/")

    conf_template = f"""# ============================================
# Конфигурация публикаций 1С:Предприятие
# Автоматически сгенерировано zbx-1c-publisher
# ============================================

# Разрешаем выполнение CGI/1C веб-расширений
<IfModule mod_1cws.c>
    AddHandler 1cws-module .1cws
</IfModule>

# Настройки для директорий публикаций
<Directory "{htdocs_path}/prod">
    Options Indexes FollowSymLinks
    AllowOverride All
    Require all granted
    <IfModule mod_1cws.c>
        SetHandler 1cws-module
    </IfModule>
</Directory>

<Directory "{htdocs_path}/tech">
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

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(conf_template, encoding="utf-8")
        logger.info("Создан шаблон конфигурации: %s", output_path)
        return output_path
    except Exception as e:
        logger.error("Ошибка при создании шаблона: %s", e)
        raise


def ensure_1c_conf_included(apache_conf: Path) -> bool:
    """Гарантирует, что httpd-1c.conf подключён в основной конфиг."""
    onec_conf = get_onec_conf_path()
    include_line = f'Include "{str(onec_conf).replace(chr(92), "/")}"'

    try:
        with open(apache_conf, "r", encoding="utf-8") as f:
            content = f.read()
            if include_line in content:
                return True
    except Exception:
        pass

    to_append = f"\n# 1C Auto-Publisher Configuration\n{include_line}\n"

    try:
        with open(apache_conf, "a", encoding="utf-8") as f:
            f.write(to_append)
        logger.info("✓ Include добавлен в %s", apache_conf)
        return True
    except PermissionError:
        logger.error("Нет прав на запись в %s", apache_conf)
        return False
    except Exception as e:
        logger.error("Ошибка: %s", e)
        return False


# ============================================================
# Установка Apache на Windows
# ============================================================


def setup_windows(publish_root: Optional[Path] = None) -> tuple[bool, str]:
    """Установка и настройка Apache на Windows с автоматическим поиском порта."""
    logger.info("--- Настройка Apache для Windows ---")

    install_path = get_install_path()
    httpd_exe = get_httpd_exe()
    service_name = get_service_name()

    # Проверка существующей установки
    if install_path.exists():
        logger.info("Путь %s уже существует.", install_path)
        apache_conf = install_path / "conf" / "httpd.conf"
        if apache_conf.exists():
            free_port = find_free_port()
            if free_port != 80:
                change_listen_port(apache_conf, free_port)
                logger.info("Порт изменён на %d в существующей установке", free_port)
        return True, f"already_installed:{install_path}"

    # Скачивание Apache
    logger.info("Скачивание Apache %s ...", APACHE_VERSION)
    if not download_file(APACHE_DOWNLOAD_URL, APACHE_ZIP_TEMP):
        if APACHE_FALLBACK_URL:
            logger.info("Пробуем альтернативный URL...")
            if not download_file(APACHE_FALLBACK_URL, APACHE_ZIP_TEMP):
                cleanup_zip()
                return False, "Не удалось скачать Apache"
        else:
            cleanup_zip()
            return False, "Не удалось скачать Apache"

    if not is_valid_zip(APACHE_ZIP_TEMP):
        cleanup_zip()
        return False, "Скачанный файл не является ZIP-архивом"

    # Распаковка
    logger.info("Распаковка архива...")
    try:
        with zipfile.ZipFile(APACHE_ZIP_TEMP, "r") as zip_ref:
            zip_ref.extractall(install_path.parent)
    except Exception as e:
        logger.error("Ошибка распаковки: %s", e)
        cleanup_zip()
        return False, f"Ошибка распаковки: {e}"
    finally:
        cleanup_zip()

    if not install_path.is_dir():
        return False, f"Папка {install_path} не найдена"

    if not httpd_exe.is_file():
        return False, f"Файл {httpd_exe} не найден"

    # Настройка порта
    apache_conf = install_path / "conf" / "httpd.conf"
    free_port = find_free_port()
    change_listen_port(apache_conf, free_port)
    logger.info("Apache будет использовать порт: %d", free_port)

    # Настройка конфигурации для 1С
    if publish_root:
        create_1c_conf_template(publish_root)
        ensure_1c_conf_included(apache_conf)

    # Регистрация службы
    run_cmd([str(httpd_exe), "-k", "uninstall", "-n", service_name])
    ok, stderr = run_cmd([str(httpd_exe), "-k", "install", "-n", service_name])

    if not ok:
        return False, f"Не удалось зарегистрировать службу: {stderr}"

    logger.info("Служба '%s' зарегистрирована.", service_name)

    # Запуск службы
    ok, stderr = run_cmd([str(httpd_exe), "-k", "start", "-n", service_name])

    if not ok:
        logger.warning("Первый запуск не удался, пробуем переустановить...")
        run_cmd([str(httpd_exe), "-k", "uninstall", "-n", service_name])
        run_cmd([str(httpd_exe), "-k", "install", "-n", service_name])
        ok, stderr = run_cmd([str(httpd_exe), "-k", "start", "-n", service_name])

        if not ok:
            return False, f"Не удалось запустить Apache: {stderr}"

    msg = f"Apache установлен в {install_path} и запущен на порту {free_port}"
    if free_port != 80:
        msg += f" (http://localhost:{free_port})"
    logger.info(msg)
    return True, msg


# ============================================================
# Установка Apache на Linux
# ============================================================


def setup_linux(publish_root: Optional[Path] = None) -> tuple[bool, str]:
    """Установка и настройка Apache на Linux с автоматическим поиском порта."""
    logger.info("--- Настройка Apache для Linux ---")

    # Проверка ОС
    os_release = Path("/etc/os-release")
    is_debian_like = False
    if os_release.exists():
        content = os_release.read_text(encoding="utf-8").lower()
        is_debian_like = any(kw in content for kw in ("debian", "ubuntu", "linuxmint"))

    if not is_debian_like:
        logger.warning("Поддерживаются только Debian/Ubuntu-совместимые дистрибутивы")
        # Пробуем продолжить

    commands = [
        ["apt", "update"],
        ["apt", "install", "-y", "apache2"],
        ["systemctl", "enable", "apache2"],
    ]

    for cmd in commands:
        ok, stderr = run_cmd(cmd)
        if not ok:
            return False, f"Настройка Apache прервана на: {' '.join(cmd)}"

    # Настройка порта
    conf_dir = Path("/etc/apache2")
    free_port = find_free_port()
    ensure_free_port(conf_dir, conf_files=["ports.conf"], start_ports=[free_port])

    # Настройка конфигурации для 1С
    if publish_root:
        create_1c_conf_template(publish_root)
        apache_conf = conf_dir / "apache2.conf"
        ensure_1c_conf_included(apache_conf)

    # Запуск службы
    ok, stderr = run_cmd(["systemctl", "start", "apache2"])

    if not ok:
        return False, f"Не удалось запустить Apache: {stderr}"

    msg = f"Apache установлен и запущен на порту {free_port}"
    if free_port != 80:
        msg += f" (http://localhost:{free_port})"
    logger.info(msg)
    return True, msg


# ============================================================
# Главная функция развёртывания
# ============================================================


def deploy_apache(publish_root: Optional[Path] = None) -> tuple[bool, str]:
    """Развёртывает Apache в зависимости от ОС."""
    current_os = platform.system()

    if current_os == "Linux":
        return setup_linux(publish_root)
    elif current_os == "Windows":
        return setup_windows(publish_root)
    else:
        msg = f"ОС {current_os} не поддерживается"
        logger.warning(msg)
        return False, msg


# ============================================================
# Управление службой Apache
# ============================================================


def check_apache_status() -> tuple[bool, str]:
    """Проверяет статус службы Apache."""
    current_os = platform.system()
    service_name = get_service_name()

    if current_os == "Windows":
        httpd_exe = get_httpd_exe()
        if not httpd_exe.exists():
            return False, "Apache не найден"

        try:
            check_svc = subprocess.run(
                ["sc", "query", service_name],
                capture_output=True,
                text=True,
                check=False,
            )
            if check_svc.returncode == 0:
                return True, f"Служба {service_name} работает"
            return False, f"Служба {service_name} не найдена или остановлена"
        except OSError as exc:
            return False, f"Ошибка проверки: {exc}"

    elif current_os == "Linux":
        try:
            proc = subprocess.run(
                ["systemctl", "is-active", "apache2"],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.stdout.strip() == "active":
                return True, "Служба apache2 активна"
            return False, "Служба apache2 неактивна"
        except OSError as exc:
            return False, f"Ошибка проверки: {exc}"

    return False, f"ОС {current_os} не поддерживается"


def restart_apache_service() -> tuple[bool, str]:
    """Перезапускает службу Apache."""
    current_os = platform.system()
    service_name = get_service_name()

    if current_os == "Windows":
        httpd_exe = get_httpd_exe()
        if not httpd_exe.exists():
            return False, "Apache не найден"
        return run_cmd([str(httpd_exe), "-k", "restart", "-n", service_name])
    elif current_os == "Linux":
        return run_cmd(["systemctl", "restart", "apache2"])
    return False, f"ОС {current_os} не поддерживается"


def stop_apache_service() -> tuple[bool, str]:
    """Останавливает службу Apache."""
    current_os = platform.system()
    service_name = get_service_name()

    if current_os == "Windows":
        httpd_exe = get_httpd_exe()
        if not httpd_exe.exists():
            return False, "Apache не найден"
        return run_cmd([str(httpd_exe), "-k", "stop", "-n", service_name])
    elif current_os == "Linux":
        return run_cmd(["systemctl", "stop", "apache2"])
    return False, f"ОС {current_os} не поддерживается"


def start_apache_service() -> tuple[bool, str]:
    """Запускает службу Apache."""
    current_os = platform.system()
    service_name = get_service_name()

    if current_os == "Windows":
        httpd_exe = get_httpd_exe()
        if not httpd_exe.exists():
            return False, "Apache не найден"
        return run_cmd([str(httpd_exe), "-k", "start", "-n", service_name])
    elif current_os == "Linux":
        return run_cmd(["systemctl", "start", "apache2"])
    return False, f"ОС {current_os} не поддерживается"


def get_apache_version() -> str:
    """Возвращает версию Apache."""
    httpd_exe = get_httpd_exe()
    if not httpd_exe.exists():
        return "Не установлен"

    try:
        proc = subprocess.run(
            [str(httpd_exe), "-v"],
            capture_output=True,
            text=True,
            check=False,
        )
        output = proc.stdout or proc.stderr
        match = re.search(r"Apache/(\d+\.\d+\.\d+)", output)
        if match:
            return match.group(1)
        return "Версия не определена"
    except Exception:
        return "Ошибка"


# ============================================================
# Запуск при прямом вызове
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Управление Apache для 1С")
    parser.add_argument(
        "action",
        choices=["deploy", "status", "restart", "stop", "start", "version", "config"],
        help="Действие",
    )
    parser.add_argument("--publish-root", default="C:/Apache24/htdocs", help="Корень публикации")
    parser.add_argument("--port", type=int, default=80, help="Желаемый порт")

    args = parser.parse_args()

    if args.action == "deploy":
        success, msg = deploy_apache(Path(args.publish_root))
        print(f"{'OK' if success else 'ERROR'}: {msg}")

    elif args.action == "status":
        success, msg = check_apache_status()
        print(f"{'RUNNING' if success else 'STOPPED'}: {msg}")

    elif args.action == "restart":
        success, msg = restart_apache_service()
        print(f"{'OK' if success else 'ERROR'}: {msg}")

    elif args.action == "stop":
        success, msg = stop_apache_service()
        print(f"{'OK' if success else 'ERROR'}: {msg}")

    elif args.action == "start":
        success, msg = start_apache_service()
        print(f"{'OK' if success else 'ERROR'}: {msg}")

    elif args.action == "version":
        version = get_apache_version()
        print(f"Apache version: {version}")

    elif args.action == "config":
        conf_path = create_1c_conf_template(Path(args.publish_root))
        print(f"Config created: {conf_path}")
