"""
Тест для проверки детального статуса информационной базы

ПРИМЕЧАНИЕ: Используйте переменные окружения для указания тестовой базы:
- TEST_INFOBASE_ID
"""
import sys
import os

# Добавляем путь к src, чтобы можно было импортировать модули
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.zbx_1c.monitoring.infobase.finder import get_detailed_infobase_status
from src.zbx_1c.monitoring.cluster.manager import get_cluster_ids

def test_detailed_status():
    print("Тестирование детального статуса информационной базы")
    print("="*65)

    # Получаем ID тестовой базы из переменных окружения
    test_infobase_id = os.environ.get("TEST_INFOBASE_ID")

    cluster_ids = get_cluster_ids()
    print(f"Найдено кластеров: {len(cluster_ids)}")

    if cluster_ids:
        cluster_id = cluster_ids[0]
        print(f"Используем кластер: {cluster_id}")

        if test_infobase_id:
            print(f"Тестируем базу из TEST_INFOBASE_ID: {test_infobase_id}")
        else:
            print("\nTEST_INFOBASE_ID не задан. Получаем список баз...")
            # Можно получить список баз и выбрать первую
            from src.zbx_1c.monitoring.infobase.finder import get_infobases_for_cluster
            infobases = get_infobases_for_cluster(cluster_id)
            if infobases:
                test_infobase_id = infobases[0].get('infobase')
                print(f"Используем первую найденную базу: {test_infobase_id}")
            else:
                print("Нет доступных информационных баз")
                return

        print(f"\nПроверка детального статуса для ID: {test_infobase_id}")

        status = get_detailed_infobase_status(test_infobase_id, cluster_id)

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
    else:
        print("Нет доступных кластеров")

    print()
    print("="*65)
    print("Тестирование детального статуса завершено")

if __name__ == "__main__":
    test_detailed_status()
