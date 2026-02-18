"""
Клиент для работы с RAC (Remote Administration Client)
Работает точно так же как в run_direct.py
"""

import subprocess
from typing import List, Dict, Any, Optional
from loguru import logger


class RACClient:
    """Клиент для выполнения команд RAC"""

    def __init__(self, settings=None):
        """
        Инициализация клиента

        Args:
            settings: Настройки приложения (опционально)
        """
        self.settings = settings
        # Порядок кодировок важен: 1С на Windows использует CP866 (OEM),
        # затем пробуем CP1251 (Windows) и UTF-8 для новых версий
        self.encodings = ["cp866", "cp1251", "utf-8"]
        self.timeout = getattr(settings, "command_timeout", 30) if settings else 30

    def execute(self, cmd_parts: List[str], mask_password: bool = True) -> Optional[Dict[str, Any]]:
        """
        Выполнение команды RAC - точная копия execute_rac_command из run_direct.py

        Args:
            cmd_parts: Части команды в виде списка
            mask_password: Скрывать пароль в логах

        Returns:
            Результат выполнения или None в случае ошибки
        """
        try:
            # Маскируем пароль в логах
            log_cmd = " ".join(cmd_parts)
            if mask_password:
                log_cmd = (
                    log_cmd.replace(f"--cluster-pwd={self.settings.user_pass}", "--cluster-pwd=***")
                    if self.settings and self.settings.user_pass
                    else log_cmd
                )

            logger.debug(f"Executing: {log_cmd}")

            result = subprocess.run(cmd_parts, capture_output=True, timeout=self.timeout)

            # Пробуем декодировать вывод
            # Для первой кодировки используем strict, чтобы проверить корректность
            for i, enc in enumerate(self.encodings):
                try:
                    error_mode = "strict" if i == 0 else "replace"
                    stdout = result.stdout.decode(enc, errors=error_mode)
                    stderr = result.stderr.decode(enc, errors=error_mode)
                    return {"returncode": result.returncode, "stdout": stdout, "stderr": stderr}
                except Exception:
                    continue

            # Если ничего не сработало, используем UTF-8 по умолчанию
            return {
                "returncode": result.returncode,
                "stdout": result.stdout.decode("utf-8", errors="replace"),
                "stderr": result.stderr.decode("utf-8", errors="replace"),
            }

        except Exception as e:
            logger.error(f"Ошибка выполнения: {e}")
            return None

    def execute_with_auth(
        self, command: str, subcommand: str, cluster_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Выполнение команды с авторизацией

        Args:
            command: Основная команда (infobase, session, job)
            subcommand: Подкоманда (summary list, list)
            cluster_id: ID кластера (опционально)

        Returns:
            Результат выполнения или None в случае ошибки
        """
        if not self.settings:
            logger.error("Settings not provided")
            return None

        cmd_parts = [
            str(self.settings.rac_path),
            command,
            subcommand,
        ]

        if cluster_id:
            cmd_parts.append(f"--cluster={cluster_id}")

        # Добавляем аутентификацию если есть
        if self.settings.user_name:
            cmd_parts.append(f"--cluster-user={self.settings.user_name}")
        if self.settings.user_pass:
            cmd_parts.append(f"--cluster-pwd={self.settings.user_pass}")

        cmd_parts.append(f"{self.settings.rac_host}:{self.settings.rac_port}")

        return self.execute(cmd_parts)
