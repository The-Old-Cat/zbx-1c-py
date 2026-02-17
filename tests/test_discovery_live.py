"""
Тест discovery кластеров на реальных данных
Проверка LLD вывода для Zabbix
"""

import sys
import os
import json
from pathlib import Path

# Устанавливаем кодировку UTF-8 для Windows
if sys.platform == "win32":
    os.system("chcp 65001 >nul")

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zbx_1c.core.config import Settings
from zbx_1c.monitoring.cluster.discovery import discover_clusters
from zbx_1c.monitoring.cluster.manager import ClusterManager
from zbx_1c.utils.rac_client import RACClient
from zbx_1c.utils.converters import format_lld_data


def test_discovery():
    """Тестирование обнаружения кластеров"""
    print("=" * 60)
    print("ТЕСТ: Обнаружение кластеров 1С (discovery)")
    print("=" * 60)
    
    # Загружаем настройки
    settings = Settings()
    
    print(f"\n[INFO] RAC_PATH: {settings.rac_path}")
    print(f"[INFO] RAS: {settings.rac_host}:{settings.rac_port}")
    print(f"[INFO] TIMEOUT: {settings.rac_timeout} сек")
    
    # Проверяем существование rac.exe
    if not settings.rac_path.exists():
        print(f"[ERROR] RAC executable не найден: {settings.rac_path}")
        return False
    
    print(f"[OK] RAC executable найден")
    
    # Тестируем RACClient напрямую
    print("\n--- Тест RACClient ---")
    rac = RACClient(settings)
    
    cmd = [
        str(settings.rac_path),
        "cluster",
        "list",
        f"{settings.rac_host}:{settings.rac_port}",
    ]
    
    print(f"Выполняю команду: {' '.join(cmd)}")
    result = rac.execute(cmd)
    
    if result is None:
        print("[ERROR] RACClient.execute вернул None")
        return False
    
    print(f"returncode: {result['returncode']}")
    print(f"stdout (длина): {len(result['stdout'])} символов")
    print(f"stderr (длина): {len(result['stderr'])} символов")
    
    if result['returncode'] != 0:
        print(f"[ERROR] Ошибка выполнения: {result['stderr'][:500]}")
        return False
    
    # Тестируем discover_clusters
    print("\n--- Тест discover_clusters ---")
    clusters = discover_clusters(settings)
    
    print(f"\n[OK] Найдено кластеров: {len(clusters)}")
    
    if not clusters:
        print("[WARN] Кластеры не найдены")
        return True  # Не ошибка, просто нет кластеров
    
    print("\n--- Список кластеров ---")
    for i, cluster in enumerate(clusters, 1):
        # Безопасный вывод с заменой некорректных символов
        name_safe = cluster.name.encode('cp1251', errors='replace').decode('cp1251')
        print(f"\n{i}. {name_safe}")
        print(f"   ID:   {cluster.id}")
        print(f"   Host: {cluster.host}")
        print(f"   Port: {cluster.port}")
        print(f"   Status: {cluster.status}")
    
    # Тестируем ClusterManager
    print("\n--- Тест ClusterManager ---")
    manager = ClusterManager(settings)
    clusters_dict = manager.discover_clusters()
    print(f"[OK] ClusterManager вернул: {len(clusters_dict)} кластеров")
    
    # Тестируем LLD формат
    print("\n--- Тест format_lld_data (Zabbix LLD) ---")
    lld_output = format_lld_data(clusters_dict)
    lld_json = json.dumps(lld_output, ensure_ascii=False, indent=2, default=str)
    print(lld_json)
    
    # Проверяем наличие статуса в LLD
    has_status = all("{#CLUSTER.STATUS}" in item for item in lld_output["data"])
    if has_status:
        print("\n[OK] LLD содержит {#CLUSTER.STATUS} для всех кластеров")
    else:
        print("\n[ERROR] LLD не содержит {#CLUSTER.STATUS}")
        return False
    
    print("\n" + "=" * 60)
    print("[OK] ТЕСТ ПРОЙДЕН УСПЕШНО")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = test_discovery()
        sys.exit(0 if success else 1)
    except Exception as e:
        error_msg = f"\n[ERROR] КРИТИЧЕСКАЯ ОШИБКА: {e}"
        try:
            print(error_msg.encode('cp1251', errors='replace').decode('cp1251'))
        except Exception:
            print(str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)
