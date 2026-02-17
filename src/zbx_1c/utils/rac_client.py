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
        # Порядок кодировок важен: сначала пробуем UTF-8 (современные версии 1С),
        # затем CP866 (классическая кодировка 1С на Windows), потом CP1251
        self.encodings = ["utf-8", "cp866", "cp1251"]
        self.timeout = getattr(settings, 'command_timeout', 30) if settings else 30

    def execute(self, cmd_parts: List[str]) -> Optional[Dict[str, Any]]:
        """
        Выполнение команды RAC - точная копия execute_rac_command из run_direct.py

        Args:
            cmd_parts: Части команды в виде списка

        Returns:
            Результат выполнения или None в случае ошибки
        """
        try:
            logger.debug(f"Executing: {' '.join(cmd_parts)}")

            result = subprocess.run(cmd_parts, capture_output=True, timeout=self.timeout)

            # Пробуем декодировать вывод
            for enc in self.encodings:
                try:
                    stdout = result.stdout.decode(enc, errors="replace")
                    stderr = result.stderr.decode(enc, errors="replace")
                    return {
                        "returncode": result.returncode,
                        "stdout": stdout,
                        "stderr": stderr
                    }
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

    def execute_with_auth(self, command: str, subcommand: str, cluster_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
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
