"""
Модуль мониторинга информационных баз 1С.
"""
import json
import subprocess
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from zbx_1c.core.config import settings
from zbx_1c.utils.converters import parse_rac_output

def get_infobase_monitoring_data(cluster_id: str) -> Dict[str, Any]:
    """
    Собирает данные мониторинга для информационных баз в указанном кластере.
    
    Args:
        cluster_id (str): Идентификатор кластера
        
    Returns:
        Dict[str, Any]: Данные мониторинга информационных баз
    """
    infobases = get_all_infobases_for_cluster(cluster_id)
    sessions = get_all_sessions_for_cluster(cluster_id)
    
    # Группируем сессии по информационным базам
    sessions_by_infobase = {}
    for session in sessions:
        ib_name = session.get("infobase")
        if ib_name not in sessions_by_infobase:
            sessions_by_infobase[ib_name] = []
        sessions_by_infobase[ib_name].append(session)
    
    # Формируем данные мониторинга
    monitoring_data = {
        "cluster_id": cluster_id,
        "timestamp": datetime.now().isoformat(),
        "infobases": []
    }
    
    for infobase in infobases:
        ib_name = infobase.get("infobase", "")
        ib_sessions = sessions_by_infobase.get(ib_name, [])
        
        active_sessions = [s for s in ib_sessions if is_session_active(s)]
        
        ib_data = {
            "name": ib_name,
            "alias": infobase.get("alias", ""),
            "description": infobase.get("description", ""),
            "total_sessions": len(ib_sessions),
            "active_sessions": len(active_sessions),
            "unique_users": len(set(s.get("user-name", "") for s in ib_sessions)),
            "applications": list(set(s.get("app-id", "") for s in ib_sessions)),
            "has_active_sessions": len(active_sessions) > 0
        }
        
        monitoring_data["infobases"].append(ib_data)
    
    return monitoring_data

def get_all_infobases_for_cluster(cluster_id: str) -> List[Dict[str, Any]]:
    """
    Получает список всех информационных баз для указанного кластера.

    Args:
        cluster_id (str): Идентификатор кластера

    Returns:
        List[Dict[str, Any]]: Список информационных баз
    """
    rac_path = settings.rac_path
    ras_address = f"{settings.rac_host}:{settings.rac_port}"

    cmd = [
        str(rac_path),
        "infobase", "summary", "list",
        "--cluster", cluster_id,
        ras_address
    ]

    # Добавляем авторизацию, если параметры заданы в конфиге
    if settings.user_name:
        cmd.extend(["--cluster-user", settings.user_name])
    if settings.user_pass:
        cmd.extend(["--cluster-pwd", settings.user_pass])

    try:
        result = subprocess.run(cmd, capture_output=True, check=False, timeout=15)

        if result.returncode == 0:
            stdout_text = result.stdout.decode("cp866" if os.name == "nt" else "utf-8", errors="replace")
            return parse_rac_output(stdout_text)

        stderr_text = result.stderr.decode("cp866" if os.name == "nt" else "utf-8", errors="replace")
        print(f"RAC ошибка (код {result.returncode}): {stderr_text}")

    except FileNotFoundError:
        print(f"Файл rac.exe не найден по пути: {settings.rac_path}")
    except subprocess.TimeoutExpired:
        print(f"Превышено время ожидания при запросе к {ras_address}")
    except subprocess.SubprocessError as e:
        print(f"Системная ошибка при запуске процесса: {str(e)}")

    return []

def get_all_sessions_for_cluster(cluster_id: str) -> List[Dict[str, Any]]:
    """
    Получает список всех сессий для указанного кластера.

    Args:
        cluster_id (str): Идентификатор кластера

    Returns:
        List[Dict[str, Any]]: Список сессий
    """
    from zbx_1c.monitoring.session.collector import SessionCollector
    collector = SessionCollector(settings)
    sessions = collector.get_sessions(cluster_id)
    # SessionCollector уже возвращает List[Dict]
    return sessions

def is_session_active(session: Dict[str, Any], threshold_minutes: int = 10) -> bool:
    """
    Проверяет, является ли сессия активной.

    Args:
        session (Dict[str, Any]): Данные сессии
        threshold_minutes (int): Порог времени неактивности в минутах

    Returns:
        bool: True, если сессия активна, иначе False
    """
    from zbx_1c.monitoring.session.filters import is_session_active as check_session_active
    return check_session_active(session, threshold_minutes)

def get_detailed_infobase_status(cluster_id: str, infobase_name: str) -> Dict[str, Any]:
    """
    Получает детальный статус указанной информационной базы.
    
    Args:
        cluster_id (str): Идентификатор кластера
        infobase_name (str): Имя информационной базы
        
    Returns:
        Dict[str, Any]: Детальный статус информационной базы
    """
    infobases = get_all_infobases_for_cluster(cluster_id)
    target_infobase = next((ib for ib in infobases if ib.get("name") == infobase_name), None)
    
    if not target_infobase:
        return {"error": f"Информационная база '{infobase_name}' не найдена в кластере {cluster_id}"}
    
    sessions = get_all_sessions_for_cluster(cluster_id)
    ib_sessions = [s for s in sessions if s.get("infobase") == infobase_name]
    active_sessions = [s for s in ib_sessions if is_session_active(s)]
    
    return {
        "infobase": target_infobase,
        "total_sessions": len(ib_sessions),
        "active_sessions": len(active_sessions),
        "sessions_detail": ib_sessions,
        "status": "active" if len(active_sessions) > 0 else "inactive",
        "last_activity": get_last_activity_time(ib_sessions)
    }

def get_last_activity_time(sessions: List[Dict[str, Any]]) -> str:
    """
    Получает время последней активности из списка сессий.

    Args:
        sessions (List[Dict[str, Any]]): Список сессий

    Returns:
        str: Время последней активности
    """
    if not sessions:
        return ""

    # Находим самое позднее время активности
    last_times: List[str] = []
    for session in sessions:
        last_active = session.get("last-active-at") or session.get("started-at")
        if last_active:
            last_times.append(str(last_active))

    if last_times:
        # Возвращаем самое позднее время
        return max(last_times)

    return ""

def export_monitoring_data_to_json(monitoring_data: Dict[str, Any], filename: Optional[str] = None) -> str:
    """
    Экспортирует данные мониторинга в JSON-файл.
    
    Args:
        monitoring_data (Dict[str, Any]): Данные мониторинга
        filename (str): Имя файла для экспорта (опционально)
        
    Returns:
        str: Путь к файлу экспорта
    """
    import os
    from datetime import datetime
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"infobase_monitoring_{timestamp}.json"
    
    filepath = os.path.join(settings.log_path or ".", filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(monitoring_data, f, ensure_ascii=False, indent=2)
    
    return filepath

if __name__ == "__main__":
    # Тестирование функций
    print("Модуль мониторинга информационных баз 1С")
    print("Для тестирования укажите ID кластера:")
    # Пример: print(get_infobase_monitoring_data("your-cluster-id"))