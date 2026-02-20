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
    parse_rac_output,
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

        Команда: rac server --cluster=<cluster_id> list --cluster-user=... --cluster-pwd=... host:port

        Возвращаемые поля (rac server list):
        - server: UUID сервера
        - agent-host: хост агента сервера
        - agent-port: порт агента сервера
        - name: имя сервера
        - using: назначение (main/secondary)
        - memory-limit: лимит памяти (КБ)
        - connections-limit: лимит сессий
        - cluster-port: порт кластера

        Args:
            cluster_id: ID кластера

        Returns:
            Список рабочих серверов
        """
        logger.debug(f"Getting working servers for cluster {cluster_id}")

        # Формируем команду: rac.exe server --cluster=cluster_id list host:port
        cmd = [
            str(self.settings.rac_path),
            "server",
            f"--cluster={cluster_id}",
            "list",
        ]

        # Добавляем аутентификацию если есть
        if self.settings.user_name:
            cmd.append(f"--cluster-user={self.settings.user_name}")
        if self.settings.user_pass:
            cmd.append(f"--cluster-pwd={self.settings.user_pass}")

        cmd.append(f"{self.settings.rac_host}:{self.settings.rac_port}")

        result = self.rac.execute(cmd)

        if not result or result["returncode"] != 0 or not result["stdout"]:
            logger.debug(f"Server list returned empty or error for cluster {cluster_id}")
            return []

        # Парсим вывод
        servers_data = parse_working_servers(result["stdout"])
        servers = []

        for data in servers_data:
            try:
                # Используем agent-host и agent-port из rac server list
                agent_host = data.get("agent-host", self.settings.rac_host)
                agent_port = data.get("agent-port", 1540)
                
                # memory-limit может быть строкой "0" или None
                memory_limit_raw = data.get("memory-limit", 0)
                try:
                    memory_limit = int(memory_limit_raw) if memory_limit_raw else 0
                except (ValueError, TypeError):
                    memory_limit = 0
                
                # connections-limit
                limit_conn_raw = data.get("connections-limit", 0)
                try:
                    limit_connections = int(limit_conn_raw) if limit_conn_raw else 0
                except (ValueError, TypeError):
                    limit_connections = 0

                # Статус определяем по наличию agent-host
                status = "working" if agent_host else "unknown"

                server = WorkingServerInfo(
                    name=data.get("name", ""),
                    host=agent_host,
                    port=int(agent_port) if agent_port else 1540,
                    status=status,
                    memory_used=0,  # rac server list не возвращает memory-used
                    memory_limit=memory_limit,
                    start_time=None,  # rac server list не возвращает start-time
                    current_connections=0,  # rac server list не возвращает current-connections
                    limit_connections=limit_connections,
                    cluster_id=data.get("server"),  # UUID сервера
                )

                servers.append(server)
                logger.debug(
                    f"Found working server: {server.name} ({server.host}:{server.port}) "
                    f"[status: {server.status}, memory_limit: {server.memory_limit} KB, "
                    f"limit_connections: {server.limit_connections}]"
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

    def get_server_processes(self, cluster_id: str) -> List[Dict[str, Any]]:
        """
        Получение списка рабочих процессов (rphost) кластера через process list

        Возвращаемые поля из rac process list:
        - process: UUID процесса
        - host: хост сервера
        - port: порт процесса
        - pid: PID процесса
        - started-at: время запуска
        - memory-size: размер памяти (байты)
        - connections: количество подключений
        - running: статус (yes/no)
        - use: используется (used/unused)

        Args:
            cluster_id: ID кластера

        Returns:
            Список рабочих процессов
        """
        logger.debug(f"Getting server processes for cluster {cluster_id}")

        # Формируем команду: rac.exe process --cluster=cluster_id list host:port
        cmd = [
            str(self.settings.rac_path),
            "process",
            f"--cluster={cluster_id}",
            "list",
        ]

        # Добавляем аутентификацию если есть
        if self.settings.user_name:
            cmd.append(f"--cluster-user={self.settings.user_name}")
        if self.settings.user_pass:
            cmd.append(f"--cluster-pwd={self.settings.user_pass}")

        cmd.append(f"{self.settings.rac_host}:{self.settings.rac_port}")

        result = self.rac.execute(cmd)

        if not result or result["returncode"] != 0 or not result["stdout"]:
            logger.debug(f"Process list returned empty or error for cluster {cluster_id}")
            return []

        # Парсим вывод
        processes_data = parse_rac_output(result["stdout"])
        processes = []

        for data in processes_data:
            try:
                # memory-size в байтах
                memory_raw = data.get("memory-size", 0)
                try:
                    memory_size = int(memory_raw) if memory_raw else 0
                except (ValueError, TypeError):
                    memory_size = 0

                process = {
                    "process": data.get("process", ""),
                    "host": data.get("host", ""),
                    "port": int(data.get("port", 0)) if data.get("port") else 0,
                    "pid": int(data.get("pid", 0)) if data.get("pid") else 0,
                    "started_at": self._parse_datetime(data.get("started-at", "")),
                    "memory_size": memory_size,  # в байтах
                    "memory_size_kb": memory_size // 1024,  # конвертируем в КБ
                    "connections": int(data.get("connections", 0)) if data.get("connections") else 0,
                    "running": data.get("running", "no") == "yes",
                    "use": data.get("use", ""),
                }
                processes.append(process)

            except Exception as e:
                logger.error(f"Ошибка парсинга рабочего процесса: {e}")

        logger.debug(f"Found {len(processes)} server processes for cluster {cluster_id}")
        return processes

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
        from ...monitoring.session.filters import is_session_active as is_session_active_strict

        def get_session_threshold(session: Dict) -> int:
            """Возвращает порог last-active-at в минутах по типу сессии"""
            app_id = session.get("app-id", "")

            if app_id == "Designer":
                return 10  # Конфигуратор — 10 минут
            else:
                return 5   # Остальные — 5 минут

        def _is_session_active_with_threshold(session: Dict) -> bool:
            """
            Проверка активности сессии:
            1. Если last-active-at <= порог → активна
            2. Если last-active-at > порог → применяем строгие фильтры (hibernate, calls, bytes)
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
                return is_session_active_strict(
                    session,
                    threshold_minutes=threshold,
                    check_activity=True,
                    min_calls=1,
                    check_traffic=True,
                    min_bytes=1024,
                )

            except (ValueError, TypeError):
                return False

        active_sessions = sum(1 for s in sessions if _is_session_active_with_threshold(s))

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

        # Метрика "Фоновые задания" — фильтрация по типу "длительные" и проверка >30 мин
        # Длительные задания: BackgroundJob и SystemBackgroundJob (исключая JobScheduler)
        # Задание считается "зависшим" если оно активно (hibernate=no) и выполняется >30 минут
        
        def is_long_running_job(job: Dict) -> bool:
            """Проверка: является ли задание длительным (фоновое или системное)"""
            app_id = job.get("app-id", "")
            return app_id in ["BackgroundJob", "SystemBackgroundJob"]
        
        def get_job_duration_minutes(job: Dict) -> float:
            """Расчет времени выполнения задания в минутах"""
            started_at_str = job.get("started-at", "")
            if not started_at_str:
                return 0.0
            
            try:
                started_at = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
                now = datetime.now(started_at.tzinfo) if started_at.tzinfo else datetime.now()
                duration = now - started_at
                return duration.total_seconds() / 60.0
            except (ValueError, TypeError):
                return 0.0
        
        def is_job_stuck(job: Dict, threshold_minutes: int = 30) -> bool:
            """
            Проверка: задание висит дольше порога
            Критерии:
            1. Задание длительное (BackgroundJob или SystemBackgroundJob)
            2. Задание активное (hibernate=no)
            3. Время выполнения > threshold_minutes
            """
            if not is_long_running_job(job):
                return False
            
            hibernate = job.get("hibernate", "no")
            if hibernate != "no":
                return False  # Задание в спящем режиме — не зависло
            
            duration = get_job_duration_minutes(job)
            return duration > threshold_minutes
        
        # Подсчет метрик по фоновым заданиям
        long_running_jobs = sum(1 for j in jobs if is_long_running_job(j))
        stuck_jobs = sum(1 for j in jobs if is_job_stuck(j, threshold_minutes=30))
        
        # Получаем максимальное время выполнения среди активных заданий для отладки
        max_job_duration = 0.0
        for j in jobs:
            if is_job_active(j):
                duration = get_job_duration_minutes(j)
                if duration > max_job_duration:
                    max_job_duration = duration

        # Получаем рабочие процессы для расчета памяти и времени рестарта
        processes = self.get_server_processes(cluster_id)

        # Получаем лимиты сессий и памяти с рабочих серверов
        total_servers_count = len(working_servers)
        working_servers_count = sum(1 for s in working_servers if s.status == "working")

        # Расчет лимита сессий
        # Архитектура 1С: connections-limit — это лимит НА ПРОЦЕСС rphost
        # Общий лимит кластера = Σ(connections-limit × количество процессов на сервере)
        # 
        # ВАЖНО: НЕ использовать фиксированное значение!
        # Лимит берется из параметров рабочего сервера:
        # - connections-limit: максимальное число подключений на один процесс
        # - processes_count: количество запущенных процессов rphost на сервере
        # 
        # Пример: если connections-limit=128 и запущено 2 процесса, лимит сервера = 256
        
        # Считаем количество процессов на каждом хосте
        from collections import defaultdict
        processes_per_host = defaultdict(int)
        for p in processes:
            host = p.get("host", "")
            if host:
                processes_per_host[host] += 1
        
        # Обновляем processes_count в working_servers
        for server in working_servers:
            server.processes_count = processes_per_host.get(server.host, 1)
        
        # Суммарный лимит сессий по всем рабочим серверам
        # Формула: Σ(connections-limit × processes_count)
        total_server_session_limit = sum(
            s.limit_connections * getattr(s, 'processes_count', 1) 
            for s in working_servers
        )
        
        logger.debug(
            f"Session limit calculation: "
            f"servers={len(working_servers)}, "
            f"limit={total_server_session_limit}, "
            f"processes_per_host={dict(processes_per_host)}"
        )

        # Расчет памяти по рабочим процессам (process list)
        # memory-size из process list — это фактическое использование памяти процессом rphost
        total_server_memory_used = sum(p.get("memory_size_kb", 0) for p in processes)
        
        # Лимит памяти берем из working servers (memory-limit)
        # Если memory-limit = 0, значит лимит не задан
        total_server_memory_limit = sum(s.memory_limit for s in working_servers)

        # Расчет времени работы по процессам
        # Используем min started-at среди процессов на каждом хосте как время запуска сервера
        # Группируем процессы по хостам
        from collections import defaultdict
        processes_by_host = defaultdict(list)
        for p in processes:
            if p.get("host"):
                processes_by_host[p["host"]].append(p)
        
        # Находим минимальное время запуска для каждого хоста
        min_start_times = {}
        for host, procs in processes_by_host.items():
            started_procs = [p for p in procs if p.get("started_at")]
            if started_procs:
                min_start_times[host] = min(p["started_at"] for p in started_procs)

        # Обновляем start_time в working_servers на основе процессов
        for server in working_servers:
            if server.host in min_start_times:
                server.start_time = min_start_times[server.host]

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
        # Архитектура: память считается по процессам rphost на хосте рабочего сервера
        # Лимит задается в настройках рабочего сервера в консоли кластера
        # Если лимит не задан (memory-limit=0), используем абсолютное значение
        server_memory_percent = 0.0
        memory_limit_set = total_server_memory_limit > 0
        
        if memory_limit_set:
            # Лимит задан — считаем процент
            server_memory_percent = round((total_server_memory_used / total_server_memory_limit) * 100, 2)
        else:
            # Лимит не задан — выводим 0, но добавляем флаг и абсолютное значение
            # Для Zabbix настраиваем триггер по абсолютному значению (например, >10 ГБ)
            server_memory_percent = 0.0

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
                "server_memory_used": total_server_memory_used,  # КБ — фактическое использование
                "server_memory_limit": total_server_memory_limit,  # КБ — лимит (0 если не задан)
                "server_memory_percent": server_memory_percent,  # % если лимит задан, иначе 0
                "servers_restarted_recently": servers_restarted_recently,
                "memory_limit_set": 1 if memory_limit_set else 0,  # Флаг: задан ли лимит памяти
                # Метрики по фоновым заданиям
                "long_running_jobs": long_running_jobs,  # Количество длительных заданий
                "stuck_jobs": stuck_jobs,  # Задания, висящие >30 мин
                "max_job_duration": round(max_job_duration, 2),  # Максимальное время выполнения (мин)
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
                    "processes_count": s.processes_count,  # Количество процессов rphost
                    "session_limit": s.limit_connections * s.processes_count,  # Лимит сервера
                    "session_percent": s.session_percent,
                    "start_time": s.start_time.isoformat() if s.start_time else None,
                    "uptime_minutes": s.uptime_minutes,
                    "is_recently_restarted": s.is_recently_restarted(),
                }
                for s in working_servers
            ],
            "processes": [
                {
                    "process": p.get("process", ""),
                    "host": p.get("host", ""),
                    "port": p.get("port", 0),
                    "pid": p.get("pid", 0),
                    "started_at": p.get("started_at", "").isoformat() if p.get("started_at") else None,
                    "memory_size": p.get("memory_size", 0),
                    "memory_size_kb": p.get("memory_size_kb", 0),
                    "connections": p.get("connections", 0),
                    "running": p.get("running", False),
                    "use": p.get("use", ""),
                }
                for p in processes
            ],
        }
