"""
Детектор типа лицензирования 1С

Определяет:
- Локальное лицензирование
- Сервер лицензирования (удалённый)
- HASP (Sentinel) через порт 1947
"""

import socket
import subprocess
import urllib.request
import json as json_lib
from typing import Optional, Dict, Any, Tuple
from loguru import logger


class LicenseDetector:
    """Детектор типа лицензирования 1С"""

    HASP_PORT = 1947
    DEFAULT_TIMEOUT = 3

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        """
        Инициализация детектора

        Args:
            timeout: Таймаут для сетевых проверок (сек)
        """
        self.timeout = timeout

    def check_hasp(self, host: str = "localhost", port: int = HASP_PORT) -> bool:
        """
        Проверка наличия HASP (Sentinel) по порту 1947

        Args:
            host: Хост для проверки
            port: Порт HASP

        Returns:
            True если HASP доступен
        """
        try:
            with socket.create_connection((host, port), timeout=self.timeout):
                logger.debug(f"HASP detected on {host}:{port}")
                return True
        except (socket.timeout, socket.error, OSError) as e:
            logger.debug(f"HASP not detected on {host}:{port}: {e}")
            return False
        except Exception as e:
            logger.warning(f"Error checking HASP on {host}:{port}: {e}")
            return False

    def get_hasp_licenses(self, host: str = "localhost", port: int = HASP_PORT) -> Optional[Dict[str, Any]]:
        """
        Получение информации о лицензиях HASP через Sentinel API

        Sentinel LDK Web API: http://host:1947/get_key_info
        
        Варианты endpoint'ов:
        - /get_key_info - основная информация о ключах
        - /get_key_info?fmt=json - явно запросить JSON
        - /api/v2/keys - API v2 (новые версии)

        Args:
            host: Хост HASP
            port: Порт HASP

        Returns:
            Данные о лицензиях или None
        """
        endpoints = [
            f"http://{host}:{port}/get_key_info?fmt=json",
            f"http://{host}:{port}/get_key_info",
            f"http://{host}:{port}/api/v2/keys",
        ]
        
        for url in endpoints:
            try:
                req = urllib.request.Request(url, method='GET')
                
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    if response.status != 200:
                        continue
                        
                    data = json_lib.loads(response.read().decode('utf-8'))
                    logger.debug(f"HASP API success: {url}")
                    
                    # Парсим информацию о ключах
                    licenses_info = []
                    total_licenses = 0
                    used_licenses = 0
                    
                    # Формат ответа Sentinel может отличаться
                    # Пробуем разные варианты парсинга
                    if isinstance(data, dict):
                        # Вариант 1: ключи в корне
                        keys = data.get('keys', [])
                        if not keys:
                            # Вариант 2: ключ в 'key_info'
                            keys = data.get('key_info', [])
                            if keys and not isinstance(keys, list):
                                keys = [keys]
                        
                        for key in keys:
                            if isinstance(key, dict):
                                # Получаем информацию о лицензии
                                serial = key.get('serial', 'unknown')
                                
                                # Лицензии могут быть в 'features' или 'licenses'
                                features = key.get('features', [])
                                if not features:
                                    features = key.get('licenses', [])
                                
                                for feature in features:
                                    if isinstance(feature, dict):
                                        license_count = feature.get('license_count', 0)
                                        license_used = feature.get('license_used', 0)
                                        feature_name = feature.get('name', f"Feature {feature.get('feature_id', 0)}")
                                        
                                        if license_count > 0:
                                            licenses_info.append({
                                                'license_type': 'hasp',
                                                'total': license_count,
                                                'in_use': license_used,
                                                'free': license_count - license_used,
                                                'series': serial,
                                                'description': feature_name,
                                            })
                                            total_licenses += license_count
                                            used_licenses += license_used
                    
                    if licenses_info:
                        return {
                            'type': 'hasp',
                            'host': host,
                            'licenses': licenses_info,
                            'total': total_licenses,
                            'used': used_licenses,
                            'free': total_licenses - used_licenses,
                        }
                    
            except Exception as e:
                logger.debug(f"HASP API failed ({url}): {e}")
                continue
        
        # Если ни один endpoint не сработал
        logger.warning(f"HASP detected but no API endpoints available")
        return None

    def check_license_server(
        self, host: str, rac_path: str, cluster_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Проверка сервера лицензирования через rac license list

        Args:
            host: Хост сервера лицензирования
            rac_path: Путь к rac
            cluster_id: ID кластера (опционально)

        Returns:
            (success, error_message)
        """
        cmd = [rac_path, "license", "list", host]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=10,
            )

            if result.returncode == 0 and result.stdout:
                logger.debug(f"License server detected on {host}")
                return True, None
            else:
                error = result.stderr.decode("cp866", errors="replace") or result.stderr.decode(
                    "utf-8", errors="replace"
                )
                logger.debug(f"License server check failed for {host}: {error}")
                return False, error

        except subprocess.TimeoutExpired:
            logger.debug(f"License server check timeout for {host}")
            return False, "Timeout"
        except Exception as e:
            logger.warning(f"Error checking license server {host}: {e}")
            return False, str(e)

    def detect(
        self,
        host: str,
        rac_path: str,
        check_local: bool = True,
    ) -> Dict[str, Any]:
        """
        Определение типа лицензирования

        Алгоритм:
        1. Проверяем указанный хост как сервер лицензирования
        2. Если не удалось — проверяем localhost
        3. Если не удалось — проверяем HASP на localhost

        Args:
            host: Основной хост для проверки
            rac_path: Путь к rac
            check_local: Проверять ли localhost если основной хост не ответил

        Returns:
            Словарь с информацией о типе лицензирования:
            {
                "type": "server" | "local" | "hasp" | "unknown",
                "host": str,
                "available": bool,
                "error": Optional[str],
                "licenses_data": Optional[dict]  # Данные о лицензиях для HASP
            }
        """
        result: Dict[str, Any] = {
            "type": "unknown",
            "host": host,
            "available": False,
            "error": None,
            "licenses_data": None,
        }

        # 1. Проверяем указанный хост как сервер лицензирования
        success, error = self.check_license_server(host, rac_path)
        if success:
            result["type"] = "server"
            result["available"] = True
            logger.info(f"License type: server ({host})")
            return result

        # 2. Если не успех и check_local=True, проверяем localhost
        if check_local and host != "localhost":
            success, error = self.check_license_server("localhost", rac_path)
            if success:
                result["type"] = "local"
                result["host"] = "localhost"
                result["available"] = True
                logger.info(f"License type: local (localhost)")
                return result

        # 3. Проверяем HASP
        if self.check_hasp(host):
            result["type"] = "hasp"
            result["host"] = host
            result["available"] = True
            
            # Пытаемся получить данные о лицензиях HASP
            hasp_data = self.get_hasp_licenses(host)
            if hasp_data:
                result["licenses_data"] = hasp_data
                logger.info(f"HASP licenses: total={hasp_data['total']}, used={hasp_data['used']}")
            else:
                # HASP обнаружен, но не удалось получить лицензии
                # Это нормально для некоторых конфигураций
                logger.warning(f"HASP detected but licenses not available")
            
            logger.info(f"License type: HASP ({host})")
            return result

        # 4. Ничего не найдено
        result["error"] = error or "License source not detected"
        logger.warning(f"License type: unknown (error: {result['error']})")
        return result
