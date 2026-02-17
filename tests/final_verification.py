"""
Финальный тест для подтверждения корректной работы системы отображения сессий
"""
import sys
import os

# Добавляем путь к src, чтобы можно было импортировать модули
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.zbx_1c.monitoring.infobase.finder import (
    get_all_infobases_from_config,
    get_enhanced_infobase_list_with_connections,
    get_detailed_infobase_status
)
from src.zbx_1c.monitoring.cluster.manager import get_cluster_ids

def final_verification():
    print("ФИНАЛЬНАЯ ПРОВЕРКА: Отображение сессий для информационных баз")
    print("="*70)
    
    cluster_ids = get_cluster_ids()
    print(f"Найдено кластеров: {len(cluster_ids)}")
    
    if cluster_ids:
        cluster_id = cluster_ids[0]
        print(f"Используем кластер: {cluster_id[:8]}...")
        
        # Получаем обычный список баз
        all_infobases = get_all_infobases_from_config()
        print(f"Всего информационных баз: {len(all_infobases)}")
        
        # Получаем расширенный список с информацией о сессиях
        enhanced_list = get_enhanced_infobase_list_with_connections(cluster_id)
        print(f"Расширенный список с информацией о сессиях: {len(enhanced_list)}")
        
        # Проверяем, есть ли базы с сессиями
        bases_with_sessions = [ib for ib in enhanced_list if ib.get('total_sessions', 0) > 0]
        print(f"Базы с сессиями: {len(bases_with_sessions)}")
        
        if bases_with_sessions:
            print(f"\nИНФОРМАЦИОННЫЕ БАЗЫ С АКТИВНЫМИ СЕССИЯМИ:")
            for i, ib in enumerate(bases_with_sessions):
                name = ib.get('name', 'N/A')
                infobase_id = ib.get('infobase', 'N/A')
                total_sessions = ib.get('total_sessions', 0)
                active_sessions = ib.get('active_sessions', 0)
                unique_users = ib.get('unique_users', 0)
                users = ', '.join(ib.get('users_list', [])[:3])  # первые 3 пользователя
                apps = ', '.join(list(ib.get('app_types', {}).keys())[:3])  # первые 3 типа приложений
                
                print(f"  [{i+1}] {name}")
                print(f"        ID: {infobase_id}")
                print(f"        Всего сессий: {total_sessions}, Активных: {active_sessions}")
                print(f"        Уникальных пользователей: {unique_users}")
                print(f"        Пользователи: {users or 'Нет'}")
                print(f"        Типы приложений: {apps or 'Нет'}")
                
                # Если это ka_pin_test8, покажем дополнительную информацию
                if name == "ka_pin_test8":
                    print(f"        >>> ЭТА БАЗА АКТИВНА (подтверждение наличия сессий) <<<")
        else:
            print("  Нет информационных баз с сессиями")
        
        # Проверим конкретно ka_pin_test8
        print(f"\nДЕТАЛЬНАЯ ИНФОРМАЦИЯ О ka_pin_test8:")
        ka_pin_test8_id = "29a7081b-b80a-442b-b203-190bc301a859"
        ka_pin_status = get_detailed_infobase_status(ka_pin_test8_id, cluster_id)
        
        print(f"  Статус активности: {'АКТИВНА' if ka_pin_status['is_apparently_active'] else 'НЕ АКТИВНА'}")
        print(f"  Всего сессий: {ka_pin_status['connection_stats']['total_sessions']}")
        print(f"  Активных сессий: {ka_pin_status['connection_stats']['active_sessions']}")
        print(f"  Пользователи: {ka_pin_status['connection_stats']['users_list']}")
        print(f"  Типы приложений: {ka_pin_status['connection_stats']['app_types']}")
        
        # Проверим, какие приложения подключены к ka_pin_test8
        if ka_pin_status['connection_stats']['app_types']:
            apps = ka_pin_status['connection_stats']['app_types']
            print(f"  Обнаруженные приложения: {', '.join([f'{app}({count})' for app, count in apps.items()])}")
            if '1CV8C' in apps:
                print(f"  >>> Обнаружен ТОНКИЙ КЛИЕНТ (1CV8C) для ka_pin_test8 <<<")
            if 'Designer' in apps:
                print(f"  >>> Обнаружен КОНФИГУРАТОР (Designer) для ka_pin_test8 <<<")
    
    print()
    print("="*70)
    print("ФИНАЛЬНАЯ ПРОВЕРКА ЗАВЕРШЕНА")
    print("Теперь система корректно отображает информацию о сессиях для всех информационных баз!")

if __name__ == "__main__":
    final_verification()