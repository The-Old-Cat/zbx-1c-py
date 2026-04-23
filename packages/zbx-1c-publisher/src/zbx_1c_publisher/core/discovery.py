"""Модуль для получения списка информационных баз с сервера 1С через RAC."""

from __future__ import annotations

import logging
import re
import subprocess
import shutil
import platform
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


def mask_sensitive_data(text: str) -> str:
    """Маскирует чувствительные данные в строке."""
    # Маскируем параметры аутентификации RAC
    text = re.sub(r"--cluster-pwd=\S+", "--cluster-pwd=***", text)
    text = re.sub(r"--cluster-user=\S+", "--cluster-user=***", text)
    text = re.sub(r"--pwd=\S+", "--pwd=***", text)
    text = re.sub(r"password=\S+", "password=***", text, flags=re.IGNORECASE)
    # Маскируем имена пользователей в командах
    text = re.sub(r"--user=\S+", "--user=***", text)
    return text


class InfoBaseInfo:
    """Информация об информационной базе."""

    def __init__(self, name: str, description: str = "", db_name: str = "", uuid: str = ""):
        self.name = name
        self.description = description
        self.db_name = db_name
        self.uuid = uuid

    def __repr__(self) -> str:
        return f"InfoBaseInfo(name={self.name!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, InfoBaseInfo) and self.name == other.name


def find_rac_executable(config) -> Optional[Path]:
    """Ищет исполняемый файл rac с учётом версии."""
    system = platform.system().lower()
    exe_name = "rac.exe" if system == "windows" else "rac"

    # Пути с учётом версии из конфига
    paths = []
    if hasattr(config, "ONEC_VERSION") and config.ONEC_VERSION:
        if system == "windows":
            paths = [
                Path(rf"C:\Program Files\1cv8\{config.ONEC_VERSION}\bin\{exe_name}"),
                Path(rf"C:\Program Files (x86)\1cv8\{config.ONEC_VERSION}\bin\{exe_name}"),
            ]
        else:
            paths = [Path(f"/opt/1cv8/x86_64/{config.ONEC_VERSION}/bin/{exe_name}")]

    # Стандартные пути
    paths += [
        (
            Path(r"C:\Program Files\1cv8\bin\rac.exe")
            if system == "windows"
            else Path("/opt/1cv8/bin/rac")
        ),
        Path(r"C:\Program Files (x86)\1cv8\bin\rac.exe"),
    ]

    for path in paths:
        if path.exists():
            logger.debug("RAC найден: %s", path)
            return path

    rac_in_path = shutil.which("rac" if system != "windows" else "rac.exe")
    if rac_in_path:
        return Path(rac_in_path)

    logger.warning("RAC не найден")
    return None


def run_rac_command(
    args: List[str],
    rac_path: Path,
    cluster_user: str = "",
    cluster_pwd: str = "",
    timeout: int = 30,
) -> str:
    """Выполняет команду RAC и возвращает вывод."""
    cmd = [str(rac_path)] + args
    if cluster_user and cluster_user.strip():
        cmd.extend([f"--cluster-user={cluster_user}"])
    if cluster_pwd and cluster_pwd.strip():
        cmd.extend([f"--cluster-pwd={cluster_pwd}"])

    # Логируем команду с маскировкой
    logger.debug("RAC: %s", mask_sensitive_data(" ".join(cmd)))

    try:
        encoding = "cp866" if platform.system().lower() == "windows" else "utf-8"
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            encoding=encoding,
            errors="replace",
        )
        if proc.returncode != 0 and proc.stderr:
            # Маскируем чувствительные данные в stderr
            masked_stderr = mask_sensitive_data(proc.stderr[:300])
            logger.debug("RAC stderr: %s", masked_stderr)
        return proc.stdout
    except subprocess.TimeoutExpired:
        logger.error("RAC timeout (%ds)", timeout)
        return ""
    except Exception as e:
        logger.error("RAC error: %s", e)
        return ""


def get_cluster_id(
    host: str, port: int, rac_path: Path, cluster_user: str = "", cluster_pwd: str = ""
) -> Optional[str]:
    """Получает UUID кластера 1С (без аутентификации)."""
    # Для cluster list НЕ нужны параметры аутентификации
    args = ["cluster", "list", f"{host}:{port}"]
    output = run_rac_command(args, rac_path, "", "")  # Без аутентификации
    match = re.search(r"cluster\s*:\s*([a-f0-9\-]{36})", output, re.IGNORECASE)
    if match:
        logger.info("Кластер: %s", match.group(1))
        return match.group(1)
    logger.error("UUID кластера не найден")
    return None


def get_infobases_from_cluster(
    cluster_id: str,
    host: str,
    port: int,
    rac_path: Path,
    cluster_user: str = "",
    cluster_pwd: str = "",
) -> List[InfoBaseInfo]:
    """Получает список информационных баз из кластера (с аутентификацией)."""
    # Для infobase summary list нужны параметры аутентификации
    args = ["infobase", "summary", "list", f"{host}:{port}", f"--cluster={cluster_id}"]
    output = run_rac_command(args, rac_path, cluster_user, cluster_pwd)
    bases: List[InfoBaseInfo] = []
    current = {}

    # Допустимые ключи для InfoBaseInfo
    valid_keys = {"name", "description", "descr", "db_name", "uuid"}

    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue
        match = re.match(r"([^:]+)\s*:\s*(.+)", line)
        if match:
            key = match.group(1).strip().lower()
            value = match.group(2).strip()

            # Пропускаем ключ 'infobase' - это маркер начала новой записи
            if key == "infobase":
                if current.get("name"):
                    # Фильтруем только допустимые ключи
                    filtered = {k: v for k, v in current.items() if k in valid_keys or k == "name"}
                    # Преобразуем 'descr' в 'description'
                    if "descr" in filtered:
                        filtered["description"] = filtered.pop("descr")
                    bases.append(InfoBaseInfo(**filtered))
                current = {"uuid": value}
            else:
                current[key] = value

    if current.get("name"):
        filtered = {k: v for k, v in current.items() if k in valid_keys or k == "name"}
        if "descr" in filtered:
            filtered["description"] = filtered.pop("descr")
        bases.append(InfoBaseInfo(**filtered))

    logger.info("Найдено баз: %d", len(bases))
    return bases


def get_bases_from_server(config) -> List[InfoBaseInfo]:
    """Получает список баз через RAC."""
    logger.info("Получение списка баз через RAC...")
    rac_path = find_rac_executable(config)
    if rac_path is None:
        raise RuntimeError("RAC не найден. Укажите ONEC_VERSION или путь к 1С.")

    cluster_id = get_cluster_id(
        host=config.SERVER_1C_HOST,
        port=config.SERVER_1C_PORT,
        rac_path=rac_path,
        # Для получения ID кластера аутентификация не нужна
    )
    if not cluster_id:
        raise RuntimeError(
            f"Не удалось получить UUID кластера. Проверьте RAS на {config.SERVER_1C_HOST}:{config.SERVER_1C_PORT}"
        )

    return get_infobases_from_cluster(
        cluster_id=cluster_id,
        host=config.SERVER_1C_HOST,
        port=config.SERVER_1C_PORT,
        rac_path=rac_path,
        cluster_user=config.SERVER_1C_USER,
        cluster_pwd=config.SERVER_1C_PASSWORD,
    )


def get_bases_local(config) -> List[InfoBaseInfo]:
    """Заглушка для локального получения баз."""
    logger.warning("Локальный метод не реализован")
    return []
