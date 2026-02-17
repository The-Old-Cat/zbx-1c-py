"""
Тест для проверки работы модуля infobase_finder с учетными данными
"""
import sys
import os

# Добавляем путь к src, чтобы можно было импортировать модули
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.zbx_1c.core.config import settings
from src.zbx_1c.monitoring.infobase.finder import get_infobases_for_cluster
from src.zbx_1c.monitoring.cluster.manager import get_cluster_ids

def test_with_credentials():
    print("Тестирование модуля infobase_finder с учетными данными")
    print("="*60)
    
    print(f"Текущие настройки:")
    print(f"  RAC Host: {settings.rac_host}")
    print(f"  RAC Port: {settings.rac_port}")
    print(f"  RAC Path: {settings.rac_path}")
    print(f"  User Name: '{settings.user_name}'")
    print(f"  User Pass: '{settings.user_pass}'")
    print()
    
    # Получаем список кластеров
    cluster_ids = get_cluster_ids()
    print(f"Найдено кластеров: {len(cluster_ids)}")
    
    if cluster_ids:
        for cluster_id in cluster_ids:
            print(f"\nПроверяем кластер: {cluster_id}")
            
            # Пробуем получить инфобазы для кластера
            infobases = get_infobases_for_cluster(cluster_id)
            print(f"  Найдено инфобаз: {len(infobases)}")
            
            if infobases:
                for i, ib in enumerate(infobases[:5]):  # Показываем первые 5
                    name = ib.get('name', 'N/A')
                    infobase_id = ib.get('infobase', 'N/A')
                    print(f"    [{i+1}] {name} (ID: {infobase_id})")
            else:
                print("    Нет данных - возможно, проблема с аутентификацией")
                
                # Проверим, можем ли мы хотя бы получить список кластеров
                from src.zbx_1c.monitoring.cluster.manager import get_all_clusters
                clusters = get_all_clusters()
                print(f"    Но кластеры получить удалось: {len(clusters)} шт.")
                if clusters:
                    print(f"    Пример кластера: {clusters[0].get('name', 'N/A')} (ID: {clusters[0].get('cluster', 'N/A')})")
    else:
        print("Нет доступных кластеров - проверьте настройки подключения к RAS")
    
    print()
    print("="*60)
    print("Тестирование завершено")

if __name__ == "__main__":
    test_with_credentials()