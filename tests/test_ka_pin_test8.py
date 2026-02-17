"""
Тест для проверки информационной базы ka_pin_test8
"""
import sys
import os

# Добавляем путь к src, чтобы можно было импортировать модули
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.zbx_1c.monitoring.infobase.finder import (
    get_infobases_for_cluster,
    get_infobase_sessions,
    get_infobase_connection_stats
)
from src.zbx_1c.monitoring.cluster.manager import get_cluster_ids

def test_ka_pin_test8():
    print("Тестирование информационной базы ka_pin_test8")
    print("="*50)
    
    cluster_ids = get_cluster_ids()
    print(f"Найдено кластеров: {len(cluster_ids)}")
    
    if cluster_ids:
        cluster_id = cluster_ids[0]
        print(f"Используем кластер: {cluster_id}")
        
        # Получаем все информационные базы
        infobases = get_infobases_for_cluster(cluster_id)
        print(f"Найдено информационных баз: {len(infobases)}")
        
        # Ищем ka_pin_test8
        ka_pin_test8 = None
        for ib in infobases:
            if ib.get('name') == 'ka_pin_test8':
                ka_pin_test8 = ib
                break
        
        if ka_pin_test8:
            infobase_id = ka_pin_test8.get('infobase')
            infobase_name = ka_pin_test8.get('name')
            print(f"\nНайдена база: {infobase_name} (ID: {infobase_id})")
            
            # Проверяем сессии для этой базы
            print(f"\nПроверка сессий для {infobase_name}:")
            sessions = get_infobase_sessions(infobase_id, cluster_id)
            print(f"  Найдено сессий: {len(sessions)}")
            
            if sessions:
                print("  Сессии:")
                for i, session in enumerate(sessions):
                    user_name = session.get('user-name', 'N/A')
                    app_id = session.get('app-id', 'N/A')
                    hibernate = session.get('hibernate', 'N/A')
                    last_active = session.get('last-active-at', 'N/A')
                    print(f"    [{i+1}] Пользователь: {user_name}, Приложение: {app_id}, Спит: {hibernate}, Последняя активность: {last_active}")
            else:
                print("  Нет сессий для этой базы")
            
            # Проверяем статистику подключений
            print(f"\nСтатистика подключений для {infobase_name}:")
            stats = get_infobase_connection_stats(infobase_id, cluster_id)
            print(f"  Всего сессий: {stats['total_sessions']}")
            print(f"  Активных сессий: {stats['active_sessions']}")
            print(f"  Неактивных сессий: {stats['inactive_sessions']}")
            print(f"  Уникальных пользователей: {stats['unique_users']}")
            print(f"  Пользователи: {stats['users_list']}")
            print(f"  Типы приложений: {stats['app_types']}")
        else:
            print("  База ka_pin_test8 не найдена")
            
            # Покажем все базы для проверки
            print(f"\nВсе найденные базы:")
            for i, ib in enumerate(infobases):
                name = ib.get('name', 'N/A')
                infobase_id = ib.get('infobase', 'N/A')
                print(f"  [{i+1}] {name} (ID: {infobase_id})")
    else:
        print("Нет доступных кластеров")
    
    print()
    print("="*50)
    print("Тестирование завершено")

if __name__ == "__main__":
    test_ka_pin_test8()