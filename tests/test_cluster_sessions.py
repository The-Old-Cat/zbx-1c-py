"""
Дополнительный тест для проверки сессий в кластере
"""
import sys
import os

# Добавляем путь к src, чтобы можно было импортировать модули
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.zbx_1c.monitoring.cluster.manager import get_cluster_ids
from src.zbx_1c.monitoring.session.collector import fetch_raw_sessions

def test_cluster_sessions():
    print("Тестирование сессий в кластере")
    print("="*50)
    
    cluster_ids = get_cluster_ids()
    print(f"Найдено кластеров: {len(cluster_ids)}")
    
    if cluster_ids:
        cluster_id = cluster_ids[0]
        print(f"Используем кластер: {cluster_id}")
        
        # Получаем все сессии в кластере
        all_sessions = fetch_raw_sessions(cluster_id)
        print(f"Всего сессий в кластере: {len(all_sessions)}")
        
        if all_sessions:
            print("\nПримеры первых 10 сессий:")
            for i, session in enumerate(all_sessions[:10]):
                user_name = session.get('user-name', 'N/A')
                app_id = session.get('app-id', 'N/A')
                infobase = session.get('infobase', 'N/A')
                hibernate = session.get('hibernate', 'N/A')
                print(f"  [{i+1}] Пользователь: {user_name}, Приложение: {app_id}, База: {infobase}, Спит: {hibernate}")
            
            # Проверим, есть ли сессии для конкретной информационной базы
            print(f"\nПроверка сессий для конкретных информационных баз:")
            infobase_counts = {}
            for session in all_sessions:
                infobase = session.get('infobase', 'Unknown')
                infobase_counts[infobase] = infobase_counts.get(infobase, 0) + 1
            
            print("Количество сессий по информационным базам:")
            for infobase_id, count in sorted(infobase_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {infobase_id}: {count} сессий")
        else:
            print("В кластере нет активных сессий")
    else:
        print("Нет доступных кластеров")
    
    print()
    print("="*50)
    print("Тестирование завершено")

if __name__ == "__main__":
    test_cluster_sessions()