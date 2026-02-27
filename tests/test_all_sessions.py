"""
Тест для проверки всех сессий в кластере

ПРИМЕЧАНИЕ: Этот файл содержит примеры тестов. Для реального тестирования
используйте pytest с fixtures и переменными окружения.
"""
import sys
import os

# Добавляем путь к src, чтобы можно было импортировать модули
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.zbx_1c.monitoring.cluster.manager import get_cluster_ids
from src.zbx_1c.monitoring.session.collector import fetch_raw_sessions

def test_all_sessions_in_cluster():
    print("Тестирование всех сессий в кластере")
    print("="*70)

    cluster_ids = get_cluster_ids()
    print(f"Найдено кластеров: {len(cluster_ids)}")

    if cluster_ids:
        cluster_id = cluster_ids[0]
        print(f"Используем кластер: {cluster_id}")

        # Получаем все сессии в кластере
        all_sessions = fetch_raw_sessions(cluster_id)
        print(f"Всего сессий в кластере: {len(all_sessions)}")

        # Пример работы с сессиями (без привязки к конкретным базам)
        if all_sessions:
            print("\nПримеры сессий в кластере (первые 10):")
            for i, session in enumerate(all_sessions[:10]):
                user_name = session.get('user-name', 'N/A')
                app_id = session.get('app-id', 'N/A')
                infobase = session.get('infobase', 'N/A')
                hibernate = session.get('hibernate', 'N/A')
                last_active = session.get('last-active-at', 'N/A')
                session_id = session.get('session-id', 'N/A')

                print(f"  [{i+1}] Session ID: {session_id}")
                print(f"        Пользователь: {user_name}")
                print(f"        Приложение: {app_id}")
                print(f"        База ID: {infobase}")
                print(f"        Спит: {hibernate}")
                print(f"        Последняя активность: {last_active}")
                print()
        else:
            print("Нет сессий в кластере")
    else:
        print("Нет доступных кластеров")

    print("="*70)
    print("Тестирование завершено")

if __name__ == "__main__":
    test_all_sessions_in_cluster()
