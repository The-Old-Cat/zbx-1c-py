"""
Менеджер для работы с лицензиями 1С
"""

from typing import Optional, Dict, Any
from loguru import logger

from ...core.config import Settings
from ...core.models import LicenseStats, LicenseInfo
from ...utils.rac_client import RACClient
from ...utils.license_detector import LicenseDetector
from ...utils.license_parser import parse_license_stats, parse_license_type


class LicenseManager:
    """Менеджер для получения и управления лицензиями 1С"""

    def __init__(self, settings: Settings):
        """
        Инициализация менеджера

        Args:
            settings: Настройки приложения
        """
        self.settings = settings
        self.rac = RACClient(settings)
        self.detector = LicenseDetector(timeout=getattr(settings, "command_timeout", 30) // 3)
        self._license_cache: Optional[LicenseStats] = None

    def get_license_stats(self, host: Optional[str] = None, use_cache: bool = False) -> LicenseStats:
        """
        Получение статистики по лицензиям

        Args:
            host: Хост для проверки (по умолчанию settings.rac_host)
            use_cache: Использовать кэш

        Returns:
            LicenseStats со статистикой лицензий
        """
        if use_cache and self._license_cache is not None:
            return self._license_cache

        host = host or self.settings.rac_host

        # 1. Определяем тип лицензирования
        detection_result = self.detector.detect(
            host=host,
            rac_path=str(self.settings.rac_path),
            check_local=True,
        )

        logger.debug(
            f"License detection: type={detection_result['type']}, "
            f"host={detection_result['host']}, available={detection_result['available']}"
        )

        if not detection_result["available"]:
            logger.warning(f"License source not available: {detection_result.get('error', 'Unknown error')}")
            return LicenseStats(
                license_type="unknown",
                host=host,
                licenses=[],
                total_licenses=0,
                used_licenses=0,
                free_licenses=0,
            )

        license_type = detection_result["type"]
        license_host = detection_result["host"]

        # 2. Для HASP используем данные из детектора
        if license_type == "hasp" and detection_result.get("licenses_data"):
            hasp_data = detection_result["licenses_data"]
            licenses = []
            
            for lic in hasp_data.get("licenses", []):
                licenses.append(LicenseInfo.from_dict(lic))
            
            stats = LicenseStats(
                license_type="hasp",
                host=license_host,
                licenses=licenses,
                total_licenses=hasp_data.get("total", 0),
                used_licenses=hasp_data.get("used", 0),
                free_licenses=hasp_data.get("free", 0),
            )
            
            logger.info(
                f"HASP license stats: total={stats.total_licenses}, "
                f"used={stats.used_licenses}, free={stats.free_licenses}, "
                f"usage={stats.usage_percent}%"
            )
            
            self._license_cache = stats
            return stats

        # 3. Для server/local используем rac license list
        cmd = [str(self.settings.rac_path), "license", "list", license_host]

        result = self.rac.execute(cmd, mask_password=False)

        if not result or result["returncode"] != 0 or not result["stdout"]:
            logger.error(f"Failed to get licenses from {license_host}: {result.get('stderr', 'Unknown error') if result else 'No result'}")
            return LicenseStats(
                license_type=license_type,
                host=license_host,
                licenses=[],
                total_licenses=0,
                used_licenses=0,
                free_licenses=0,
            )

        # 4. Парсим вывод
        output = result["stdout"]
        stats = parse_license_stats(output, license_type, license_host)

        logger.info(
            f"License stats: type={stats.license_type}, "
            f"total={stats.total_licenses}, used={stats.used_licenses}, "
            f"free={stats.free_licenses}, usage={stats.usage_percent}%"
        )

        self._license_cache = stats
        return stats

    def get_license_stats_raw(self, host: Optional[str] = None) -> Dict[str, Any]:
        """
        Получение сырых данных по лицензиям (для отладки)

        Args:
            host: Хост для проверки

        Returns:
            Словарь с данными о лицензиях
        """
        host = host or self.settings.rac_host

        stats = self.get_license_stats(host=host, use_cache=False)

        return {
            "license_type": stats.license_type,
            "host": stats.host,
            "total": stats.total_licenses,
            "used": stats.used_licenses,
            "free": stats.free_licenses,
            "usage_percent": stats.usage_percent,
            "licenses": [
                {
                    "type": lic.license_type,
                    "total": lic.total,
                    "used": lic.used,
                    "free": lic.free,
                    "series": lic.series,
                    "description": lic.description,
                }
                for lic in stats.licenses
            ],
        }

    def clear_cache(self) -> None:
        """Очистка кэша лицензий"""
        self._license_cache = None
