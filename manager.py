"""
Менеджер мониторинга 1С:Предприятия для Zabbix

Критически важные моменты:
- Лимит сессий задается в .env через SESSION_LIMIT (количество лицензий)
- Память: мониторить на уровне ОС для каждого рабочего сервера
- Центральный сервер: svp-pinavto01 — при падении кластер недоступен
- Диапазон портов: 1560-1591 для рабочих процессов (важно для firewall)
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


WARNINGS = {
    "session_limit": """
        Лимит сессий берется из настроек (.env):
        SESSION_LIMIT = количество лицензий (устанавливается вручную).
    """,
    "memory_monitoring": """
        Память нужно мониторить на уровне ОС для каждого рабочего сервера,
        так как в параметрах кластера указаны только лимиты для процессов.
    """,
    "central_server": """
        svp-pinavto01 является центральным сервером кластера.
        При его падении кластер становится недоступен полностью.
    """,
    "port_range": """
        Диапазон портов 1560-1591 используется для динамического выделения
        портов рабочим процессам. Это важно для firewall.
    """
}


class ClusterMetricsCollector:
    """
    Сборщик метрик кластера 1С
    
    Архитектура:
    - Рабочий сервер (Working Server) — узел с агентом ragent
    - Рабочий процесс (rphost.exe) — выполняет код 1С, обслуживает сессии
    - Лимит сессий = connections-limit × количество процессов
    - Память считается по процессам rphost (фактическое использование)
    """
    
    def __init__(self, rac_host: str, rac_port: int, rac_path: str,
                 cluster_user: Optional[str] = None, cluster_pwd: Optional[str] = None):
        self.rac_host = rac_host
        self.rac_port = rac_port
        self.rac_path = rac_path
        self.cluster_user = cluster_user
        self.cluster_pwd = cluster_pwd

        # Критически важные сервера
        self.central_servers = ["svp-pinavto01", "srv-pinavto01"]

        # Диапазон портов рабочих процессов
        self.process_port_range = (1560, 1591)

        # Лимит сессий из .env (SESSION_LIMIT)
        self.session_limit = int(os.getenv("SESSION_LIMIT", 100))
    
    def get_session_limit(self, working_servers: List[Dict]) -> int:
        """
        Возвращает лимит сессий из настроек (.env)

        Лимит устанавливается вручную в SESSION_LIMIT
        в соответствии с количеством лицензий 1С
        """
        logger.info(f"Session limit from .env: {self.session_limit}")
        return self.session_limit
    
    def get_memory_usage(self, processes: List[Dict]) -> Dict[str, Any]:
        """
        Расчет использования памяти
        
        Архитектура:
        - Память выделяется каждому процессу rphost отдельно
        - Лимит памяти задается в настройках рабочего процесса
        - Фактическое использование берется из process list (memory-size)
        
        Важно: memory-limit из server list может быть 0 (не задан),
        поэтому мониторим фактическое использование в КБ/МБ
        """
        total_memory_kb = 0
        processes_memory = []
        
        for proc in processes:
            memory_kb = proc.get("memory_size_kb", 0)
            total_memory_kb += memory_kb
            
            processes_memory.append({
                "host": proc.get("host", ""),
                "pid": proc.get("pid", 0),
                "memory_kb": memory_kb,
                "memory_mb": round(memory_kb / 1024, 2),
            })
        
        # Группировка по хостам (рабочим серверам)
        memory_by_host = {}
        for proc in processes_memory:
            host = proc["host"]
            if host not in memory_by_host:
                memory_by_host[host] = 0
            memory_by_host[host] += proc["memory_kb"]
        
        return {
            "total_memory_kb": total_memory_kb,
            "total_memory_mb": round(total_memory_kb / 1024, 2),
            "total_memory_gb": round(total_memory_kb / 1024 / 1024, 2),
            "by_host": memory_by_host,
            "processes": processes_memory,
            "warning": WARNINGS["memory_monitoring"]
        }
    
    def check_central_server_status(self, working_servers: List[Dict]) -> Dict[str, Any]:
        """
        Проверка статуса центрального сервера
        
        Критически важно: если центральный сервер недоступен,
        весь кластер становится неработоспособным
        """
        central_server_status = {}
        
        for server in working_servers:
            host = server.get("host", "")
            if host in self.central_servers:
                central_server_status[host] = {
                    "is_central": True,
                    "status": server.get("status", "unknown"),
                    "warning": WARNINGS["central_server"]
                }
            else:
                central_server_status[host] = {
                    "is_central": False,
                    "status": server.get("status", "unknown")
                }
        
        # Проверка: все ли центральные сервера работают
        all_central_ok = all(
            info["status"] == "working" 
            for info in central_server_status.values() 
            if info.get("is_central")
        )
        
        return {
            "status": central_server_status,
            "all_central_available": all_central_ok,
            "central_servers": self.central_servers
        }
    
    def get_port_range_info(self) -> Dict[str, Any]:
        """
        Информация о диапазоне портов для рабочих процессов
        
        Важно для настройки firewall
        """
        return {
            "range_start": self.process_port_range[0],
            "range_end": self.process_port_range[1],
            "total_ports": self.process_port_range[1] - self.process_port_range[0] + 1,
            "warning": WARNINGS["port_range"]
        }
    
    def collect_metrics(self, working_servers: List[Dict], processes: List[Dict],
                       sessions: List[Dict]) -> Dict[str, Any]:
        """
        Сбор всех метрик кластера

        Возвращает:
        - session_limit: лимит сессий из .env
        - session_usage: процент использования
        - memory: информация по памяти
        - central_server: статус центральных серверов
        - port_range: информация по портам
        """
        # Лимит сессий из .env
        session_limit = self.get_session_limit(working_servers)
        current_sessions = len(sessions)
        session_percent = round((current_sessions / session_limit * 100), 2) if session_limit > 0 else 0

        # Использование памяти
        memory_info = self.get_memory_usage(processes)

        # Статус центральных серверов
        central_status = self.check_central_server_status(working_servers)

        # Информация по портам
        port_info = self.get_port_range_info()

        return {
            "timestamp": datetime.now().isoformat(),
            "sessions": {
                "current": current_sessions,
                "limit": session_limit,
                "percent": session_percent,
                "warning": WARNINGS["session_limit"]
            },
            "memory": memory_info,
            "central_server": central_status,
            "port_range": port_info,
            "working_servers_count": len(working_servers),
            "processes_count": len(processes)
        }


def main():
    """Пример использования"""
    # Пример данных (в реальности получаем из rac)
    working_servers = [
        {
            "name": "Центральный сервер",
            "host": "srv-pinavto01",
            "status": "working"
        }
    ]

    processes = [
        {
            "host": "srv-pinavto01",
            "pid": 19980,
            "memory_size_kb": 154122
        },
        {
            "host": "srv-pinavto01",
            "pid": 34168,
            "memory_size_kb": 785
        }
    ]

    sessions = [{"session-id": i} for i in range(8)]

    collector = ClusterMetricsCollector(
        rac_host="127.0.0.1",
        rac_port=1545,
        rac_path=r"C:\Program Files\1cv8\8.3.27.1786\bin\rac.exe",
        cluster_user="new_1cPin_KA",
        cluster_pwd="!Admin1c!159753"
    )

    metrics = collector.collect_metrics(working_servers, processes, sessions)

    print("\n" + "="*60)
    print("МЕТРИКИ КЛАСТЕРА 1С")
    print("="*60)
    print(f"Сессии: {metrics['sessions']['current']}/{metrics['sessions']['limit']} "
          f"({metrics['sessions']['percent']}%)")
    print(f"Память: {metrics['memory']['total_memory_mb']} МБ")
    print(f"Рабочих серверов: {metrics['working_servers_count']}")
    print(f"Процессов: {metrics['processes_count']}")
    print(f"Центральные сервера доступны: {metrics['central_server'].get('all_central_available', 'N/A')}")
    print(f"Диапазон портов: {metrics['port_range']['range_start']}-{metrics['port_range']['range_end']}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
