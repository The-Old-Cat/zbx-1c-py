import os
import tempfile
from pathlib import Path
from typing import Optional


def find_rac_executable() -> Optional[Path]:
    """
    Поиск исполняемого файла rac в системе
    с учетом кроссплатформенности
    """
    import shutil

    # Сначала пробуем найти в PATH
    which_rac = shutil.which("rac")
    if which_rac:
        return Path(which_rac)

    # Общие пути для разных ОС
    common_paths = []

    if os.name == "nt":  # Windows
        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")

        # Ищем в стандартных директориях 1С
        for base in [program_files, program_files_x86]:
            base_path = Path(base) / "1cv8"
            if base_path.exists():
                for version_dir in base_path.iterdir():
                    if version_dir.is_dir():
                        rac_path = version_dir / "bin" / "rac.exe"
                        if rac_path.exists():
                            return rac_path

    else:  # Linux/macOS
        # Linux пути
        linux_paths = [
            "/opt/1C/v8.3/x86_64/rac",
            "/opt/1cv8/x86_64/rac",
            "/usr/bin/rac",
        ]

        # macOS пути
        macos_paths = [
            "/Applications/1C/Enterprise Platform/rac",
            "/Applications/1cv8/rac",
        ]

        common_paths.extend(linux_paths)
        common_paths.extend(macos_paths)

        for path_str in common_paths:
            path = Path(path_str)
            if path.exists():
                return path

    return None


def get_temp_file(suffix: str = ".tmp") -> Path:
    """Создание временного файла с учетом ОС"""
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return Path(path)


def ensure_dir(path: Path) -> Path:
    """Создание директории если её нет"""
    path.mkdir(parents=True, exist_ok=True)
    return path
