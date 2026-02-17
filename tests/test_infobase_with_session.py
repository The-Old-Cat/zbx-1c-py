"""
Тест для проверки новых функций на информационной базе с сессией
"""
import sys
import os

# Добавляем путь к src, чтобы можно было импортировать модули
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.zbx_1c.monitoring.infobase.finder import (
    get_infobase_sessions, 
    get_infobase_connection_stats
)
from src.zbx_1c.monitoring.cluster.manager import get_cluster_ids

def test_infobase_with_session():
    print("Тестирование новых функций на информационной базе с сессией")
    print("="*60)
    
    cluster_ids = get_cluster_ids()
    print(f"Найдено кластеров: {len(cluster_ids)}")
    
    if cluster_ids:
        cluster_id = cluster_ids[0]
        print(f"Используем кластер: {cluster_id}")
        
        # Используем информационную базу, у которой мы знаем, что есть сессия
        infobase_id = "72293841-4df1-4c61-9cb7-ae33b2fa0cad"  # bp_korp_test_kiselev
        infobase_name = "bp_korp_test_kiselev"
        
        print(f"\nТестируем базу: {infobase_name} (ID: {infobase_id})")
        
        # Тестируем получение сессий для информационной базы
        print(f"\n1. Тестирование get_infobase_sessions():")
        sessions = get_infobase_sessions(infobase_id, cluster_id)
        print(f"   Найдено сессий для базы '{infobase_name}': {len(sessions)}")
        
        if sessions:
            print("   Найденные сессии:")
            for i, session in enumerate(sessions):
                user_name = session.get('user-name', 'N/A')
                app_id = session.get('app-id', 'N/A')
                hibernate = session.get('hibernate', 'N/A')
                last_active = session.get('last-active-at', 'N/A')
                print(f"     [{i+1}] Пользователь: {user_name}, Приложение: {app_id}, Спит: {hibernate}, Последняя активность: {last_active}")
        else:
            print("   Нет сессий для этой информационной базы")
        
        # Тестируем получение статистики подключений
        print(f"\n2. Тестирование get_infobase_connection_stats():")
        stats = get_infobase_connection_stats(infobase_id, cluster_id)
        print(f"   Статистика подключений для базы '{infobase_name}':")
        print(f"     - Всего сессий: {stats['total_sessions']}")
        print(f"     - Активных сессий: {stats['active_sessions']}")
        print(f"     - Неактивных сессий: {stats['inactive_sessions']}")
        print(f"     - Уникальных пользователей: {stats['unique_users']}")
        print(f"     - Пользователи: {stats['users_list']}")
        print(f"     - Типы приложений: {stats['app_types']}")
    else:
        print("   Нет доступных кластеров для тестирования")
    
    print()
    print("="*60)
    print("Тестирование завершено")

if __name__ == "__main__":
    test_infobase_with_session()