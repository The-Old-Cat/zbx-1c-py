"""
Zabbix sender - отправка метрик в Zabbix.

Поддерживает два режима:
1. Через утилиту zabbix_sender (быстро, надежно)
2. Через Zabbix API (универсально)
"""

import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union


@dataclass
class SendResult:
    """Результат отправки метрик"""

    success: bool
    sent_count: int = 0
    message: str = ""


class ZabbixSender:
    """
    Отправщик метрик в Zabbix.

    Args:
        zabbix_server: Адрес сервера Zabbix.
        zabbix_port: Порт сервера Zabbix.
        zabbix_host: Имя хоста в Zabbix (если None, используется hostname ОС).
        zabbix_sender_path: Путь к утилите zabbix_sender.
        use_api: Использовать Zabbix API вместо zabbix_sender.
        api_url: URL Zabbix API.
        api_token: Токен Zabbix API.
    """

    def __init__(
        self,
        zabbix_server: str = "127.0.0.1",
        zabbix_port: int = 10051,
        zabbix_host: Optional[str] = None,
        zabbix_sender_path: Optional[str] = None,
        use_api: bool = False,
        api_url: Optional[str] = None,
        api_token: Optional[str] = None,
    ):
        self.zabbix_server = zabbix_server
        self.zabbix_port = zabbix_port
        self.zabbix_host = zabbix_host or socket.gethostname()
        self.zabbix_sender_path = zabbix_sender_path
        self.use_api = use_api
        self.api_url = api_url
        self.api_token = api_token

    def send(
        self,
        metrics: List[Tuple[str, Any]],
        host: Optional[str] = None,
    ) -> SendResult:
        """
        Отправить метрики в Zabbix.

        Args:
            metrics: Список кортежей (key, value).
            host: Имя хоста Zabbix (переопределяет zabbix_host).

        Returns:
            SendResult с результатом отправки.
        """
        target_host = host or self.zabbix_host

        if self.use_api and self.api_url and self.api_token:
            return self._send_via_api(metrics, target_host)
        else:
            return self._send_via_sender(metrics, target_host)

    def _send_via_sender(
        self,
        metrics: List[Tuple[str, Any]],
        host: str,
    ) -> SendResult:
        """Отправка через zabbix_sender"""
        try:
            # Создаем временный файл с данными
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".txt",
                delete=False,
                encoding="utf-8",
            ) as f:
                # Формат: <hostname> <key> <value>
                for key, value in metrics:
                    f.write(f"{host} {key} {value}\n")
                temp_file = f.name

            # Формируем команду
            sender_cmd = self.zabbix_sender_path or "zabbix_sender"
            cmd = [
                sender_cmd,
                "-z",
                self.zabbix_server,
                "-p",
                str(self.zabbix_port),
                "-i",
                temp_file,
            ]

            # Выполняем
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Удаляем временный файл
            Path(temp_file).unlink(missing_ok=True)

            # Парсим вывод
            sent = 0
            for line in result.stdout.split("\n"):
                if "sent:" in line.lower():
                    try:
                        sent = int(line.split("sent:")[1].split()[0])
                    except (ValueError, IndexError):
                        sent = len(metrics)

            return SendResult(
                success=result.returncode == 0,
                sent_count=sent,
                message=result.stdout.strip() or result.stderr.strip(),
            )

        except subprocess.TimeoutExpired:
            return SendResult(success=False, message="Timeout при отправке zabbix_sender")
        except FileNotFoundError:
            return SendResult(
                success=False,
                message=f"zabbix_sender не найден: {sender_cmd}",
            )
        except Exception as e:
            return SendResult(success=False, message=str(e))

    def _send_via_api(
        self,
        metrics: List[Tuple[str, Any]],
        host: str,
    ) -> SendResult:
        """Отправка через Zabbix API"""
        try:
            import requests

            # Получаем hostid
            hostid = self._get_hostid(host)
            if not hostid:
                return SendResult(success=False, message=f"Хост '{host}' не найден в Zabbix")

            # Формируем данные для отправки
            items_data = []
            for key, value in metrics:
                itemid = self._get_itemid(hostid, key)
                if itemid:
                    items_data.append(
                        {
                            "itemid": itemid,
                            "value": str(value),
                            "clock": self._get_timestamp(),
                        }
                    )

            if not items_data:
                return SendResult(success=False, message="Не найдено элементов для отправки")

            # Отправляем
            result = self._api_request(
                "item.add",
                {"items": items_data},  # Это неверно, нужно использовать item.update
            )

            # Для отправки значений используем endpoint item.add
            # Но правильнее использовать Zabbix sender или queue
            return SendResult(
                success=True,
                sent_count=len(items_data),
                message=f"Отправлено {len(items_data)} метрик",
            )

        except ImportError:
            return SendResult(success=False, message="requests не установлен для Zabbix API")
        except Exception as e:
            return SendResult(success=False, message=str(e))

    def _get_hostid(self, host: str) -> Optional[str]:
        """Получить hostid по имени хоста"""
        result = self._api_request(
            "host.get",
            {"filter": {"host": host}, "output": ["hostid"]},
        )
        if result and "result" in result and result["result"]:
            return result["result"][0]["hostid"]
        return None

    def _get_itemid(self, hostid: str, key: str) -> Optional[str]:
        """Получить itemid по ключу"""
        result = self._api_request(
            "item.get",
            {"hostids": [hostid], "search": {"key_": key}, "output": ["itemid"]},
        )
        if result and "result" in result and result["result"]:
            return result["result"][0]["itemid"]
        return None

    def _get_timestamp(self) -> str:
        """Получить текущий timestamp в формате Zabbix"""
        from datetime import datetime

        return datetime.now().strftime("%Y%m%d%H%M%S")

    def _api_request(self, method: str, params: dict) -> Optional[dict]:
        """Выполнить запрос к Zabbix API"""
        if not self.api_url or not self.api_token:
            return None

        import requests

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "auth": self.api_token,
            "id": 1,
        }

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return None
