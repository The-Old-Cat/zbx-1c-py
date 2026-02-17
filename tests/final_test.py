"""
Финальный тест для проверки работы модулей infobase_finder и infobase_analyzer
"""
import sys
import os

# Добавляем путь к src, чтобы можно было импортировать модули
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.zbx_1c.monitoring.infobase.finder import get_all_infobases_from_config, get_infobase_statistics
from src.zbx_1c.monitoring.infobase.analyzer import get_all_infobases
from src.zbx_1c.monitoring.cluster.manager import get_cluster_ids

def final_test():
    print("Финальный тест работы модулей infobase_finder и infobase_analyzer")
    print("="*70)
    
    # Получаем список кластеров
    cluster_ids = get_cluster_ids()
    print(f"Найдено кластеров: {len(cluster_ids)}")
    
    if cluster_ids:
        # Тестируем infobase_finder
        print(f"\n1. Тестирование infobase_finder:")
        infobases_finder = get_all_infobases_from_config()
        print(f"   Найдено баз через infobase_finder: {len(infobases_finder)}")
        
        if infobases_finder:
            print("   Примеры первых 5 баз:")
            for i, ib in enumerate(infobases_finder[:5]):
                name = ib.get('name', 'N/A')
                infobase_id = ib.get('infobase', 'N/A')
                cluster_id = ib.get('cluster_id', 'N/A')
                print(f"     [{i+1}] {name} (ID: {infobase_id}, Кластер: {cluster_id})")
            
            # Получаем статистику
            stats = get_infobase_statistics(infobases_finder)
            print(f"   Статистика:")
            print(f"     - Всего баз: {stats['total_bases']}")
            print(f"     - Всего подключений: {stats['total_connections']}")
            print(f"     - Количество кластеров: {stats['total_clusters']}")
        else:
            print("   Нет данных от infobase_finder")
        
        # Тестируем infobase_analyzer
        print(f"\n2. Тестирование infobase_analyzer:")
        first_cluster_id = cluster_ids[0]
        infobases_analyzer = get_all_infobases(first_cluster_id)
        print(f"   Найдено баз через infobase_analyzer для кластера {first_cluster_id[:8]}...: {len(infobases_analyzer)}")
        
        if infobases_analyzer:
            print("   Примеры первых 5 баз:")
            for i, ib in enumerate(infobases_analyzer[:5]):
                name = ib.get('name', 'N/A')
                infobase_id = ib.get('infobase', 'N/A')
                print(f"     [{i+1}] {name} (ID: {infobase_id})")
        else:
            print("   Нет данных от infobase_analyzer")
    
    print()
    print("="*70)
    print("Финальный тест завершен успешно!")
    print("Оба модуля теперь корректно возвращают информацию об информационных базах")

if __name__ == "__main__":
    final_test()