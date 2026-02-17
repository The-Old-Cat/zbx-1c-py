"""
Тестовый файл для проверки работы модулей infobase_finder и infobase_analyzer
"""
import sys
import os

# Добавляем путь к src, чтобы можно было импортировать модули
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.zbx_1c.monitoring.infobase.finder import get_all_infobases_from_config
from src.zbx_1c.monitoring.infobase.analyzer import get_all_infobases
from src.zbx_1c.core.config import settings

def test_infobase_modules():
    print("Тестирование модулей infobase_finder и infobase_analyzer")
    print("="*60)
    
    print(f"Текущие настройки:")
    print(f"  RAC Host: {settings.rac_host}")
    print(f"  RAC Port: {settings.rac_port}")
    print(f"  RAC Path: {settings.rac_path}")
    print()
    
    # Тестируем infobase_finder
    print("1. Тестирование get_all_infobases_from_config() из infobase_finder:")
    try:
        infobases_finder = get_all_infobases_from_config()
        print(f"   Найдено баз через infobase_finder: {len(infobases_finder)}")
        if infobases_finder:
            for i, ib in enumerate(infobases_finder[:3]):  # Показываем первые 3
                name = ib.get('name', 'N/A')
                infobase_id = ib.get('infobase', 'N/A')
                print(f"   [{i+1}] {name} (ID: {infobase_id})")
        else:
            print("   Нет данных - возможно, проблема с подключением к RAS или кластерам")
    except Exception as e:
        print(f"   Ошибка при вызове get_all_infobases_from_config(): {e}")
    
    print()
    
    # Тестируем infobase_analyzer
    print("2. Тестирование get_all_infobases() из infobase_analyzer:")
    try:
        # Сначала получим список кластеров
        from src.zbx_1c.monitoring.cluster.manager import get_cluster_ids
        cluster_ids = get_cluster_ids()
        
        if cluster_ids:
            print(f"   Найдено кластеров: {len(cluster_ids)}")
            # Пробуем получить инфобазы для первого кластера
            first_cluster_id = cluster_ids[0]
            print(f"   Получение инфобаз для кластера: {first_cluster_id}")
            infobases_analyzer = get_all_infobases(first_cluster_id)
            print(f"   Найдено баз через infobase_analyzer: {len(infobases_analyzer)}")
            if infobases_analyzer:
                for i, ib in enumerate(infobases_analyzer[:3]):  # Показываем первые 3
                    name = ib.get('name', 'N/A')
                    infobase_id = ib.get('infobase', 'N/A')
                    print(f"   [{i+1}] {name} (ID: {infobase_id})")
            else:
                print("   Нет данных для этого кластера - возможно, нет инфобаз или проблемы с доступом")
        else:
            print("   Нет доступных кластеров - невозможно протестировать get_all_infobases()")
    except Exception as e:
        print(f"   Ошибка при вызове get_all_infobases(): {e}")
    
    print()
    print("="*60)
    print("Тестирование завершено")

if __name__ == "__main__":
    test_infobase_modules()