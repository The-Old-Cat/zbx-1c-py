"""
Тест для проверки новых функций отображения сессий в infobase_finder
"""
import sys
import os

# Добавляем путь к src, чтобы можно было импортировать модули
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.zbx_1c.monitoring.infobase.finder import (
    get_infobase_sessions, 
    get_infobase_connection_stats,
    get_enhanced_infobase_list_with_connections
)
from src.zbx_1c.monitoring.cluster.manager import get_cluster_ids

def test_session_functions():
    print("Тестирование новых функций отображения сессий в infobase_finder")
    print("="*70)
    
    cluster_ids = get_cluster_ids()
    print(f"Найдено кластеров: {len(cluster_ids)}")
    
    if cluster_ids:
        cluster_id = cluster_ids[0]
        print(f"Используем кластер: {cluster_id}")
        
        # Получаем список информационных баз для кластера
        from src.zbx_1c.monitoring.infobase.finder import get_infobases_for_cluster
        infobases = get_infobases_for_cluster(cluster_id)
        print(f"Найдено информационных баз: {len(infobases)}")
        
        if infobases:
            # Берем первую информационную базу для тестирования
            first_infobase = infobases[0]
            infobase_id = first_infobase.get('infobase')
            infobase_name = first_infobase.get('name', 'N/A')
            
            print(f"\nТестируем базу: {infobase_name} (ID: {infobase_id})")
            
            # Тестируем получение сессий для информационной базы
            print(f"\n1. Тестирование get_infobase_sessions():")
            sessions = get_infobase_sessions(infobase_id, cluster_id)
            print(f"   Найдено сессий для базы '{infobase_name}': {len(sessions)}")
            
            if sessions:
                print("   Примеры первых 5 сессий:")
                for i, session in enumerate(sessions[:5]):
                    user_name = session.get('user-name', 'N/A')
                    app_id = session.get('app-id', 'N/A')
                    hibernate = session.get('hibernate', 'N/A')
                    print(f"     [{i+1}] Пользователь: {user_name}, Приложение: {app_id}, Спит: {hibernate}")
            
            # Тестируем получение статистики подключений
            print(f"\n2. Тестирование get_infobase_connection_stats():")
            stats = get_infobase_connection_stats(infobase_id, cluster_id)
            print(f"   Статистика подключений для базы '{infobase_name}':")
            print(f"     - Всего сессий: {stats['total_sessions']}")
            print(f"     - Активных сессий: {stats['active_sessions']}")
            print(f"     - Неактивных сессий: {stats['inactive_sessions']}")
            print(f"     - Уникальных пользователей: {stats['unique_users']}")
            print(f"     - Типы приложений: {dict(list(stats['app_types'].items())[:5])}")  # первые 5
            
            # Тестируем получение расширенного списка информационных баз
            print(f"\n3. Тестирование get_enhanced_infobase_list_with_connections():")
            enhanced_list = get_enhanced_infobase_list_with_connections(cluster_id)
            print(f"   Найдено расширенных записей: {len(enhanced_list)}")
            
            if enhanced_list:
                print("   Пример первой информационной базы с деталями подключений:")
                first_enhanced = enhanced_list[0]
                print(f"     Название: {first_enhanced.get('name', 'N/A')}")
                print(f"     Всего сессий: {first_enhanced.get('total_sessions', 0)}")
                print(f"     Активных сессий: {first_enhanced.get('active_sessions', 0)}")
                print(f"     Уникальных пользователей: {first_enhanced.get('unique_users', 0)}")
                print(f"     Типы приложений: {dict(list(first_enhanced.get('app_types', {}).items())[:3])}")
        else:
            print("   Нет доступных информационных баз для тестирования")
    else:
        print("   Нет доступных кластеров для тестирования")
    
    print()
    print("="*70)
    print("Тестирование новых функций завершено")

if __name__ == "__main__":
    test_session_functions()