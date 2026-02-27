"""
Тест для проверки новых функций на информационной базе с сессией

ПРИМЕЧАНИЕ: Используйте переменные окружения для указания тестовой базы:
- TEST_INFOBASE_ID
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
            from src.zbx_1c.monitoring.infobase.finder import get_infobases_for_cluster
            infobases = get_infobases_for_cluster(cluster_id)
            if infobases:
                test_infobase_id = infobases[0].get('infobase')
                print(f"Используем первую найденную базу: {test_infobase_id}")
            else:
                print("Нет доступных информационных баз")
                return

        print(f"\nТестируем базу ID: {test_infobase_id}")

        # Тестируем получение сессий для информационной базы
        print(f"\n1. Тестирование get_infobase_sessions():")
        sessions = get_infobase_sessions(test_infobase_id, cluster_id)
        print(f"   Найдено сессий: {len(sessions)}")

        if sessions:
            print("   Найденные сессии:")
            for i, session in enumerate(sessions):
                user_name = session.get('user-name', 'N/A')
                app_id = session.get('app-id', 'N/A')
                hibernate = session.get('hibernate', 'N/A')
                last_active = session.get('last-active-at', 'N/A')
                print(f"     [{i+1}] Пользователь: {user_name}, Приложение: {app_id}")
        else:
            print("   Нет сессий для этой информационной базы")

        # Тестируем получение статистики подключений
        print(f"\n2. Тестирование get_infobase_connection_stats():")
        stats = get_infobase_connection_stats(test_infobase_id, cluster_id)
        print(f"   Статистика подключений:")
        print(f"     - Всего сессий: {stats['total_sessions']}")
        print(f"     - Активных сессий: {stats['active_sessions']}")
        print(f"     - Неактивных сессий: {stats['inactive_sessions']}")
        print(f"     - Уникальных пользователей: {stats['unique_users']}")
        print(f"     - Типы приложений: {list(stats['app_types'].keys())}")
    else:
        print("   Нет доступных кластеров для тестирования")

    print()
    print("="*60)
    print("Тестирование завершено")

if __name__ == "__main__":
    test_infobase_with_session()
