"""
Менеджер для работы с кластерами 1С
Работает точно так же как в run_direct.py
"""

import socket
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger

from ...core.config import Settings
from ...utils.rac_client import RACClient
from ...utils.converters import (
    parse_clusters,
    parse_infobases,
    parse_sessions,
    parse_jobs,
    parse_working_servers,
)
from ...core.models import WorkingServerInfo


def check_cluster_status(host: str, port: int, timeout: int = 5) -> str:
    """
    Проверка статуса кластера через подключение к рабочему серверу 1С

    Args:
        host: Хост рабочего сервера
        port: Порт рабочего сервера
        timeout: Таймаут подключения

    Returns:
        Статус кластера: "available", "unavailable" или "unknown"
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            return "available"
        else:
            return "unavailable"
    except Exception as e:
        logger.warning(f"Failed to check cluster status for {host}:{port}: {e}")
        return "unknown"


class ClusterManager:
    """Менеджер для работы с кластерами 1С"""

    def __init__(self, settings: Settings):
        """
        Инициализация менеджера

        Args:
            settings: Настройки приложения
        """
        self.settings = settings
        self.rac = RACClient(settings)
        self._clusters_cache: Optional[List[Dict]] = None

    def discover_clusters(self, use_cache: bool = True) -> List[Dict]:
        """
        Обнаружение кластеров - точная копия discover_clusters из run_direct.py

        Args:
            use_cache: Использовать кэш

        Returns:
            Список кластеров (в формате dict)
        """
        if use_cache and self._clusters_cache is not None:
            return self._clusters_cache

        # Формируем команду: rac.exe cluster list host:port
        cmd = [
            str(self.settings.rac_path),
            "cluster",
            "list",
            f"{self.settings.rac_host}:{self.settings.rac_port}",
        ]

        result = self.rac.execute(cmd)

        if not result or result["returncode"] != 0 or not result["stdout"]:
            logger.error("Не удалось получить список кластеров")
            return []

        # Парсим вывод
        clusters_data = parse_clusters(result["stdout"])
        clusters = []

        for data in clusters_data:
            try:
                cluster = {
                    "id": data.get("cluster") or data.get("id"),
                    "name": data.get("name", "unknown"),
                    "host": data.get("host", self.settings.rac_host),
                    "port": data.get("port", self.settings.rac_port),
                    "status": check_cluster_status(
                        data.get("host", self.settings.rac_host),
                        int(data.get("port", self.settings.rac_port)),
                        timeout=self.settings.rac_timeout,
                    ),
                }

                if cluster["id"]:
                    clusters.append(cluster)
                    logger.debug(
                        f"Найден кластер: {cluster['name']} ({cluster['id']}) [status: {cluster['status']}]"
                    )
            except Exception as e:
                logger.error(f"Ошибка парсинга кластера: {e}")

        self._clusters_cache = clusters
        return clusters

    def get_infobases(self, cluster_id: str) -> List[Dict]:
        """
        Получение информационных баз - точная копия get_infobases из run_direct.py

        Args:
            cluster_id: ID кластера

        Returns:
            Список информационных баз
        """
        cmd = [
            str(self.settings.rac_path),
            "infobase",
            "summary",
            "list",
            f"--cluster={cluster_id}",
        ]

        # Добавляем аутентификацию если есть
        if self.settings.user_name:
            cmd.append(f"--cluster-user={self.settings.user_name}")
        if self.settings.user_pass:
            cmd.append(f"--cluster-pwd={self.settings.user_pass}")

        cmd.append(f"{self.settings.rac_host}:{self.settings.rac_port}")

        result = self.rac.execute(cmd)
        if result and result["returncode"] == 0 and result["stdout"]:
            return parse_infobases(result["stdout"])

        return []

    def get_sessions(self, cluster_id: str) -> List[Dict]:
        """
        Получение сессий - точная копия get_sessions из run_direct.py

        Args:
            cluster_id: ID кластера

        Returns:
            Список сессий
        """
        cmd = [
            str(self.settings.rac_path),
            "session",
            "list",
            f"--cluster={cluster_id}",
        ]

        # Добавляем аутентификацию если есть
        if self.settings.user_name:
            cmd.append(f"--cluster-user={self.settings.user_name}")
        if self.settings.user_pass:
            cmd.append(f"--cluster-pwd={self.settings.user_pass}")

        cmd.append(f"{self.settings.rac_host}:{self.settings.rac_port}")

        result = self.rac.execute(cmd)
        if result and result["returncode"] == 0 and result["stdout"]:
            return parse_sessions(result["stdout"])

        return []

    def get_jobs(self, cluster_id: str) -> List[Dict]:
        """
        Получение фоновых заданий через connection list

        В версиях 1С до 8.3.24 нет команды 'job list',
        поэтому получаем задания из connection list:
        - BackgroundJob — фоновые задания пользователей
        - SystemBackgroundJob — системные фоновые задания
        - JobScheduler — планировщик регламентных заданий

        Args:
            cluster_id: ID кластера

        Returns:
            Список фоновых заданий
        """
        # Используем JobReader с получением из connection list
        from ...monitoring.jobs.reader import JobReader

        reader = JobReader(self.settings)
        return reader.get_jobs(cluster_id)

    def get_working_servers(self, cluster_id: str) -> List[WorkingServerInfo]:
        """
        Получение списка рабочих серверов кластера
        
        Команда: rac server list --cluster=<cluster_id> host:port
        
        Возвращаемые поля:
        - name: имя сервера
        - host: хост рабочего сервера
        - port: порт рабочего сервера
        - status: статус (working/not-working)
        - memory-used: используемая память (КБ)
        - memory-limit: лимит памяти (КБ)
        - start-time: время запуска сервера
        - current-connections: текущее количество сессий
        - limit-connections: лимит сессий на сервере
        
        Args:
            cluster_id: ID кластера
            
        Returns:
            Список рабочих серверов
        """
        logger.debug(f"Getting working servers for cluster {cluster_id}")
        
        # Формируем команду: rac.exe server list --cluster=cluster_id host:port
        cmd = [
            str(self.settings.rac_path),
            "server",
            "list",
            f"--cluster={cluster_id}",
            f"{self.settings.rac_host}:{self.settings.rac_port}",
        ]
        
        # Добавляем аутентификацию если есть
        if self.settings.user_name:
            cmd.append(f"--cluster-user={self.settings.user_name}")
        if self.settings.user_pass:
            cmd.append(f"--cluster-pwd={self.settings.user_pass}")
        
        result = self.rac.execute(cmd)
        
        if not result or result["returncode"] != 0 or not result["stdout"]:
            logger.debug(f"Server list returned empty or error for cluster {cluster_id}")
            return []
        
        # Парсим вывод
        servers_data = parse_working_servers(result["stdout"])
        servers = []
        
        for data in servers_data:
            try:
                # Определяем статус сервера
                # В 1С статус может быть "working" или "not-working"
                # Также может быть пустым или отсутствовать
                raw_status = data.get("status", "").lower()
                if raw_status == "working":
                    status = "working"
                elif raw_status == "not-working":
                    status = "not-working"
                else:
                    # Если статус не указан, считаем working если есть хост
                    status = "working" if data.get("host") else "unknown"
                
                server = WorkingServerInfo(
                    name=data.get("name", ""),
                    host=data.get("host", self.settings.rac_host),
                    port=int(data.get("port", self.settings.rac_port)),
                    status=status,
                    memory_used=int(data.get("memory-used", 0) or 0),
                    memory_limit=int(data.get("memory-limit", 0) or 0),
                    start_time=self._parse_datetime(data.get("start-time", "")),
                    current_connections=int(data.get("current-connections", 0) or 0),
                    limit_connections=int(data.get("limit-connections", 0) or 0),
                    cluster_id=data.get("cluster"),
                )
                
                servers.append(server)
                logger.debug(
                    f"Found working server: {server.name} ({server.host}:{server.port}) "
                    f"[status: {server.status}, memory: {server.memory_used}/{server.memory_limit} KB]"
                )
                
            except Exception as e:
                logger.error(f"Ошибка парсинга рабочего сервера: {e}")
        
        logger.debug(f"Found {len(servers)} working servers for cluster {cluster_id}")
        return servers
    
    def _parse_datetime(self, dt_string: str) -> Optional[datetime]:
        """
        Парсинг строки даты/времени из вывода rac
        
        Args:
            dt_string: Строка даты/времени в формате ISO
            
        Returns:
            datetime объект или None
        """
        if not dt_string:
            return None
        
        try:
            # Формат: 2024-01-15T10:30:00 или 2024-01-15T10:30:00Z
            dt_string = dt_string.replace("Z", "+00:00")
            return datetime.fromisoformat(dt_string)
        except (ValueError, TypeError):
            logger.debug(f"Не удалось распарсить дату: {dt_string}")
            return None

    def get_cluster_metrics(self, cluster_id: str) -> Optional[Dict]:
        """
        Получение метрик кластера

        Args:
            cluster_id: ID кластера

        Returns:
            Метрики кластера в формате dict
        """
        # Получаем информацию о кластере
        clusters = self.discover_clusters()
        cluster = None
        for c in clusters:
            if c["id"] == cluster_id:
                cluster = c
                break

        if not cluster:
            logger.error(f"Кластер {cluster_id} не найден")
            return None

        # Получаем сессии и задания
        sessions = self.get_sessions(cluster_id)
        jobs = self.get_jobs(cluster_id)
        
        # Получаем рабочие серверы
        working_servers = self.get_working_servers(cluster_id)

        if sessions is None:
            sessions = []

        # Подсчет метрик
        total_sessions = len(sessions)

        # Определение активности сессий по last-active-at
        # Основной критерий: last-active-at
        # - Если last-active-at <= порог → сессия активна
        # - Если last-active-at > порог → применяем дополнительные фильтры (hibernate, calls, bytes)
        #
        # Пороги по типам сессий:
        # - Designer (Конфигуратор): 10 минут
        # - Остальные: 5 минут
        from ...monitoring.session.filters import is_session_active

        def get_session_threshold(session: Dict) -> int:
            """Возвращает порог last-active-at в минутах по типу сессии"""
            app_id = session.get("app-id", "")

            if app_id == "Designer":
                return 10  # Конфигуратор — 10 минут
            else:
                return 5   # Остальные — 5 минут

        def is_session_active_custom(session: Dict) -> bool:
            """
            Проверка активности сессии:
            1. Если last-active-at <= порог → активна
            2. Если last-active-at > порог → проверяем hibernate, calls, bytes
            """
            threshold = get_session_threshold(session)

            # Проверяем last-active-at
            try:
                last_active_str = session.get("last-active-at", "")
                if not last_active_str:
                    return False

                last_active = datetime.fromisoformat(last_active_str.replace("Z", "+00:00"))
                if last_active.tzinfo:
                    now = datetime.now(last_active.tzinfo)
                else:
                    now = datetime.now()

                # Если last-active-at свежее порога → сессия активна
                if last_active >= now - timedelta(minutes=threshold):
                    return True

                # Если last-active-at старше порога → применяем строгие фильтры
                return is_session_active(
                    session,
                    threshold_minutes=threshold,
                    check_activity=True,
                    min_calls=1,
                    check_traffic=True,
                    min_bytes=1024,
                )

            except (ValueError, TypeError):
                return False

        active_sessions = sum(1 for s in sessions if is_session_active_custom(s))

        total_jobs = len(jobs)

        # Определение активности фоновых заданий по hibernate
        # Критерии активности по типам:
        # 1. JobScheduler — всегда активен (планировщик работает постоянно)
        # 2. SystemBackgroundJob — активен, если hibernate == 'no'
        # 3. BackgroundJob — активен, если hibernate == 'no'
        def is_job_active(job: Dict) -> bool:
            """Проверка активности задания по типу и hibernate"""
            app_id = job.get("app-id", "")
            hibernate = job.get("hibernate", "no")

            # JobScheduler всегда активен
            if app_id == "JobScheduler":
                return True

            # SystemBackgroundJob и BackgroundJob активны, если не в hibernate
            if app_id in ["SystemBackgroundJob", "BackgroundJob"]:
                return hibernate == "no"

            return False

        active_jobs = sum(1 for j in jobs if is_job_active(j))

        # Получаем лимиты сессий и памяти с рабочих серверов
        total_servers_count = len(working_servers)
        working_servers_count = sum(1 for s in working_servers if s.status == "working")
        
        # Суммарный лимит сессий по всем рабочим серверам
        total_server_session_limit = sum(s.limit_connections for s in working_servers)
        
        # Суммарная память и лимит памяти
        total_server_memory_used = sum(s.memory_used for s in working_servers)
        total_server_memory_limit = sum(s.memory_limit for s in working_servers)
        
        # Количество серверов, перезапущенных недавно (<5 мин)
        servers_restarted_recently = sum(
            1 for s in working_servers 
            if s.is_recently_restarted(threshold_minutes=5)
        )

        # Рассчитываем процент заполнения сессий (от лимита рабочих серверов)
        session_percent = 0.0
        if total_server_session_limit > 0:
            session_percent = round((total_sessions / total_server_session_limit) * 100, 2)

        # Рассчитываем процент использования памяти
        server_memory_percent = 0.0
        if total_server_memory_limit > 0:
            server_memory_percent = round((total_server_memory_used / total_server_memory_limit) * 100, 2)

        return {
            "cluster": {
                "id": cluster["id"],
                "name": cluster["name"],
                "status": cluster["status"],  # Статус для отправки в Zabbix
            },
            "metrics": {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_jobs": total_jobs,
                "active_jobs": active_jobs,
                "session_limit": total_server_session_limit,
                "session_percent": session_percent,
                "working_servers": working_servers_count,
                "total_servers": total_servers_count,
                "server_memory_used": total_server_memory_used,
                "server_memory_limit": total_server_memory_limit,
                "server_memory_percent": server_memory_percent,
                "servers_restarted_recently": servers_restarted_recently,
            },
            "working_servers": [
                {
                    "name": s.name,
                    "host": s.host,
                    "port": s.port,
                    "status": s.status,
                    "memory_used": s.memory_used,
                    "memory_limit": s.memory_limit,
                    "memory_percent": s.memory_percent,
                    "current_connections": s.current_connections,
                    "limit_connections": s.limit_connections,
                    "session_percent": s.session_percent,
                    "start_time": s.start_time.isoformat() if s.start_time else None,
                    "uptime_minutes": s.uptime_minutes,
                    "is_recently_restarted": s.is_recently_restarted,
                }
                for s in working_servers
            ],
        }
