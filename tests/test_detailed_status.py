"""
Тест для проверки детального статуса информационной базы ka_pin_test8
"""
import sys
import os

# Добавляем путь к src, чтобы можно было импортировать модули
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.zbx_1c.monitoring.infobase.finder import get_detailed_infobase_status
from src.zbx_1c.monitoring.cluster.manager import get_cluster_ids

def test_detailed_status():
    print("Тестирование детального статуса информационной базы ka_pin_test8")
    print("="*65)
    
    cluster_ids = get_cluster_ids()
    print(f"Найдено кластеров: {len(cluster_ids)}")
    
    if cluster_ids:
        cluster_id = cluster_ids[0]
        print(f"Используем кластер: {cluster_id}")
        
        # Тестируем ka_pin_test8
        infobase_id = "29a7081b-b80a-442b-b203-190bc301a859"  # ka_pin_test8
        infobase_name = "ka_pin_test8"
        
        print(f"\nПроверка детального статуса для: {infobase_name} (ID: {infobase_id})")
        
        status = get_detailed_infobase_status(infobase_id, cluster_id)
        
        print(f"\nДетальный статус информационной базы:")
        print(f"  ID базы: {status['infobase_id']}")
        print(f"  ID кластера: {status['cluster_id']}")
        print(f"  Есть активные сессии: {status['has_active_sessions']}")
        print(f"  Есть любые сессии: {status['has_any_sessions']}")
        print(f"  Похоже активна: {status['is_apparently_active']}")
        
        print(f"\nСтатистика подключений:")
        conn_stats = status['connection_stats']
        print(f"  Всего сессий: {conn_stats['total_sessions']}")
        print(f"  Активных сессий: {conn_stats['active_sessions']}")
        print(f"  Неактивных сессий: {conn_stats['inactive_sessions']}")
        print(f"  Уникальных пользователей: {conn_stats['unique_users']}")
        print(f"  Пользователи: {conn_stats['users_list']}")
        print(f"  Типы приложений: {conn_stats['app_types']}")
        
        print(f"\nИнформация о базе:")
        infobase_info = status['infobase_info']
        if infobase_info:
            for key, value in infobase_info.items():
                if key not in ['infobase_info', 'connection_stats']:  # Исключаем вложенные структуры
                    print(f"  {key}: {value}")
        else:
            print("  Нет дополнительной информации о базе")
        
        # Также проверим базу, у которой есть сессии, для сравнения
        print(f"\n" + "="*65)
        print(f"СРАВНЕНИЕ: Детальный статус базы bp_korp_test_kiselev (с сессией)")
        
        active_infobase_id = "72293841-4df1-4c61-9cb7-ae33b2fa0cad"  # bp_korp_test_kiselev
        active_infobase_name = "bp_korp_test_kiselev"
        
        active_status = get_detailed_infobase_status(active_infobase_id, cluster_id)
        
        print(f"  Есть активные сессии: {active_status['has_active_sessions']}")
        print(f"  Есть любые сессии: {active_status['has_any_sessions']}")
        print(f"  Похоже активна: {active_status['is_apparently_active']}")
        
        print(f"  Всего сессий: {active_status['connection_stats']['total_sessions']}")
        print(f"  Активных сессий: {active_status['connection_stats']['active_sessions']}")
        print(f"  Пользователи: {active_status['connection_stats']['users_list']}")
        print(f"  Типы приложений: {active_status['connection_stats']['app_types']}")
    else:
        print("Нет доступных кластеров")
    
    print()
    print("="*65)
    print("Тестирование детального статуса завершено")

if __name__ == "__main__":
    test_detailed_status()