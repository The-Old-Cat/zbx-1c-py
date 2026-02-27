"""Отправка метрик в Zabbix"""

import json
import logging
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SenderResult:
    """Результат отправки метрик"""

    success: bool
    sent_count: int
    failed_count: int
    message: str = ""


class ZabbixSender:
    """
    Отправщик метрик в Zabbix.

    Поддерживает два способа отправки:
    1. Через утилиту zabbix_sender (предпочтительно)
    2. Через Zabbix API (если zabbix_sender недоступен)
    """

    def __init__(
        self,
        zabbix_server: str = "127.0.0.1",
        zabbix_port: int = 10051,
        zabbix_host: str | None = None,
        zabbix_sender_path: str | Path | None = None,
        use_api: bool = False,
        api_url: str | None = None,
        api_token: str | None = None,
    ):
        """
        Инициализация отправщика.

        Args:
            zabbix_server: Адрес сервера Zabbix
            zabbix_port: Порт Zabbix trapper (по умолчанию 10051)
            zabbix_host: Имя хоста в Zabbix (если None, используется hostname ОС)
            zabbix_sender_path: Путь к утилите zabbix_sender
            use_api: Использовать Zabbix API вместо zabbix_sender
            api_url: URL Zabbix API
            api_token: Токен Zabbix API
        """
        self.zabbix_server = zabbix_server
        self.zabbix_port = zabbix_port
        self.zabbix_host = zabbix_host or socket.gethostname()
        self.zabbix_sender_path = zabbix_sender_path
        self.use_api = use_api
        self.api_url = api_url
        self.api_token = api_token

    def send(
        self,
        metrics: list[tuple[str, Any]],
        host: str | None = None,
    ) -> SenderResult:
        """
        Отправка метрик в Zabbix.

        Args:
            metrics: Список кортежей (key, value)
            host: Имя хоста Zabbix (переопределяет значение из конструктора)

        Returns:
            SenderResult с результатом отправки
        """
        target_host = host or self.zabbix_host

        if self.use_api and self.api_url and self.api_token:
            return self._send_via_api(metrics, target_host)
        else:
            return self._send_via_sender(metrics, target_host)

    def _send_via_sender(
        self,
        metrics: list[tuple[str, Any]],
        host: str,
    ) -> SenderResult:
        """
        Отправка через утилиту zabbix_sender.

        Args:
            metrics: Список кортежей (key, value)
            host: Имя хоста Zabbix

        Returns:
            SenderResult с результатом отправки
        """
        # Формируем данные для отправки
        # Формат: - host key value
        lines = []
        for key, value in metrics:
            lines.append(f"- {host} {key} {value}")

        if not lines:
            return SenderResult(
                success=True,
                sent_count=0,
                failed_count=0,
                message="Нет метрик для отправки",
            )

        # Определяем путь к zabbix_sender
        sender_cmd = self._find_zabbix_sender()

        if sender_cmd is None:
            # zabbix_sender не найден, пробуем отправить через API
            logger.warning("zabbix_sender не найден, пробуем API")
            return self._send_via_api(metrics, host)

        # Формируем команду
        # Используем stdin для передачи данных
        try:
            input_data = "\n".join(lines)

            cmd = [
                sender_cmd,
                "-z",
                self.zabbix_server,
                "-p",
                str(self.zabbix_port),
                "-s",
                host,
                "-i",
                "-",  # Чтение из stdin
            ]

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            stdout, stderr = process.communicate(input=input_data, timeout=30)

            if process.returncode == 0:
                # Парсим вывод zabbix_sender
                # Пример: "sent: 10; skipped: 0; total: 10; failed: 0; skipped: 0"
                sent_count = len(lines)
                failed_count = 0

                for line in stdout.splitlines():
                    if "failed:" in line:
                        try:
                            failed_count = int(
                                line.split("failed:")[1].split(";")[0].strip()
                            )
                            sent_count = int(
                                line.split("sent:")[1].split(";")[0].strip()
                            )
                        except (ValueError, IndexError):
                            pass

                return SenderResult(
                    success=failed_count == 0,
                    sent_count=sent_count,
                    failed_count=failed_count,
                    message=stdout.strip() if stdout else "OK",
                )
            else:
                return SenderResult(
                    success=False,
                    sent_count=0,
                    failed_count=len(lines),
                    message=f"zabbix_sender вернул код {process.returncode}: {stderr}",
                )

        except subprocess.TimeoutExpired:
            return SenderResult(
                success=False,
                sent_count=0,
                failed_count=len(lines),
                message="Таймаут отправки zabbix_sender",
            )
        except Exception as e:
            return SenderResult(
                success=False,
                sent_count=0,
                failed_count=len(lines),
                message=f"Ошибка отправки zabbix_sender: {e}",
            )

    def _send_via_api(
        self,
        metrics: list[tuple[str, Any]],
        host: str,
    ) -> SenderResult:
        """
        Отправка через Zabbix API.

        Args:
            metrics: Список кортежей (key, value)
            host: Имя хоста Zabbix

        Returns:
            SenderResult с результатом отправки
        """
        if not self.api_url or not self.api_token:
            return SenderResult(
                success=False,
                sent_count=0,
                failed_count=len(metrics),
                message="Zabbix API URL или токен не указаны",
            )

        try:
            import urllib.request
            import urllib.error

            # Формируем запрос к API
            # Метод: item.get для получения ID элементов данных
            # Затем: trapper data

            # Получаем ID хоста
            host_id = self._get_host_id(host)

            if not host_id:
                return SenderResult(
                    success=False,
                    sent_count=0,
                    failed_count=len(metrics),
                    message=f"Хост '{host}' не найден в Zabbix",
                )

            # Получаем ID элементов данных
            item_ids = self._get_item_ids(host_id, metrics)

            # Формируем данные для отправки
            # Для trapper используем формат: host, key, value, timestamp
            timestamp = int(socket.time.time())

            data = []
            for key, value in metrics:
                item_id = item_ids.get(key)
                if item_id:
                    data.append(
                        {
                            "itemid": item_id,
                            "value": str(value),
                            "clock": timestamp,
                        }
                    )

            if not data:
                return SenderResult(
                    success=False,
                    sent_count=0,
                    failed_count=len(metrics),
                    message="Элементы данных не найдены",
                )

            # Отправляем через API
            response = self._api_call("item.add", data)

            if response and "result" in response:
                return SenderResult(
                    success=True,
                    sent_count=len(data),
                    failed_count=0,
                    message="Метрики успешно отправлены через API",
                )
            else:
                return SenderResult(
                    success=False,
                    sent_count=0,
                    failed_count=len(data),
                    message=f"Ошибка API: {response}",
                )

        except Exception as e:
            return SenderResult(
                success=False,
                sent_count=0,
                failed_count=len(metrics),
                message=f"Ошибка отправки через API: {e}",
            )

    def _find_zabbix_sender(self) -> str | None:
        """
        Поиск утилиты zabbix_sender в системе.

        Returns:
            Путь к утилите или None
        """
        # Проверяем указанный путь
        if self.zabbix_sender_path:
            path = Path(self.zabbix_sender_path)
            if path.exists() and path.is_executable():
                return str(path)

        # Проверяем PATH
        sender_names = ["zabbix_sender", "zabbix-sender", "zabbix_sender.exe"]

        for name in sender_names:
            path = shutil.which(name)
            if path:
                return path

        # Проверяем стандартные пути
        standard_paths = [
            "/usr/bin/zabbix_sender",
            "/usr/local/bin/zabbix_sender",
            "/opt/zabbix/bin/zabbix_sender",
            "C:\\Program Files\\Zabbix Agent\\zabbix_sender.exe",
            "C:\\Zabbix\\bin\\zabbix_sender.exe",
        ]

        for path in standard_paths:
            p = Path(path)
            if p.exists() and p.is_file():
                return str(p)

        return None

    def _get_host_id(self, host: str) -> str | None:
        """Получение ID хоста в Zabbix"""
        response = self._api_call(
            "host.get",
            {"filter": {"host": host}, "output": ["hostid"]},
        )

        if response and "result" in response and response["result"]:
            return response["result"][0]["hostid"]

        return None

    def _get_item_ids(
        self,
        host_id: str,
        metrics: list[tuple[str, Any]],
    ) -> dict[str, str]:
        """Получение ID элементов данных"""
        keys = [key for key, _ in metrics]

        response = self._api_call(
            "item.get",
            {
                "hostids": [host_id],
                "filter": {"key_": keys},
                "output": ["itemid", "key_"],
            },
        )

        item_ids = {}
        if response and "result" in response:
            for item in response["result"]:
                item_ids[item["key_"]] = item["itemid"]

        return item_ids

    def _api_call(self, method: str, params: Any) -> dict | None:
        """Вызов Zabbix API"""
        import urllib.request
        import urllib.error
        import json

        if not self.api_url or not self.api_token:
            return None

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "auth": self.api_token,
            "id": 1,
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.api_url,
                data=data,
                headers={"Content-Type": "application/json"},
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))

        except Exception as e:
            logger.error(f"Ошибка Zabbix API: {e}")
            return None


# Импорт для поиска в PATH
try:
    import shutil
except ImportError:
    shutil = None  # type: ignore
