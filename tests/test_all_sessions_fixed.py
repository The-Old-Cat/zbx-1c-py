"""
Тест для проверки всех сессий в кластере и поиска сессий для ka_pin_test8
"""
import sys
import os

# Добавляем путь к src, чтобы можно было импортировать модули
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.zbx_1c.monitoring.cluster.manager import get_cluster_ids
from src.zbx_1c.monitoring.session.collector import fetch_raw_sessions

def test_all_sessions_in_cluster():
    print("Тестирование всех сессий в кластере для поиска сессий ka_pin_test8")
    print("="*70)
    
    cluster_ids = get_cluster_ids()
    print(f"Найдено кластеров: {len(cluster_ids)}")
    
    if cluster_ids:
        cluster_id = cluster_ids[0]
        print(f"Используем кластер: {cluster_id}")
        
        # Получаем все сессии в кластере
        all_sessions = fetch_raw_sessions(cluster_id)
        print(f"Всего сессий в кластере: {len(all_sessions)}")
        
        # Ищем сессии, связанные с ka_pin_test8
        ka_pin_test8_id = "29a7081b-b80a-442b-b203-190bc301a859"  # ID для ka_pin_test8
        
        ka_pin_test8_sessions = []
        for session in all_sessions:
            if session.get('infobase') == ka_pin_test8_id:
                ka_pin_test8_sessions.append(session)
        
        print(f"\nНайдено сессий для ka_pin_test8 (ID: {ka_pin_test8_id}): {len(ka_pin_test8_sessions)}")
        
        if ka_pin_test8_sessions:
            print("Детали сессий для ka_pin_test8:")
            for i, session in enumerate(ka_pin_test8_sessions):
                user_name = session.get('user-name', 'N/A')
                app_id = session.get('app-id', 'N/A')
                hibernate = session.get('hibernate', 'N/A')
                last_active = session.get('last-active-at', 'N/A')
                session_id = session.get('session-id', 'N/A')
                print(f"  [{i+1}] Session ID: {session_id}")
                print(f"        Пользователь: {user_name}")
                print(f"        Приложение: {app_id}")
                print(f"        Спит: {hibernate}")
                print(f"        Последняя активность: {last_active}")
        else:
            print("  Нет активных сессий для ka_pin_test8")
            
            # Проверим, есть ли вообще какие-то сессии в кластере
            if all_sessions:
                print(f"\nПримеры других сессий в кластере (всего {len(all_sessions)}):")
                for i, session in enumerate(all_sessions[:10]):  # Показываем первые 10
                    user_name = session.get('user-name', 'N/A')
                    app_id = session.get('app-id', 'N/A')
                    infobase = session.get('infobase', 'N/A')
                    hibernate = session.get('hibernate', 'N/A')
                    last_active = session.get('last-active-at', 'N/A')
                    session_id = session.get('session-id', 'N/A')
                    
                    # Попробуем определить имя базы по ID
                    infobase_names = {
                        "72293841-4df1-4c61-9cb7-ae33b2fa0cad": "bp_korp_test_kiselev",
                        "449d5d03-28a9-4dd0-8973-6d54624763af": "bp_korp_party_test",
                        "77fe84d3-7c28-4a87-9c4a-590a88f66a07": "bp_korp_test",
                        "29a7081b-b80a-442b-b203-190bc301a859": "ka_pin_test8",
                        "5a3a2d85-cb1a-46e8-9456-00b6bc966674": "ka_pin_test",
                        "49c22e03-3aa1-461b-a439-3720819c4e13": "ka_pin_test2",
                        "f7acfa34-c4be-4ab6-97e1-c66e47afed69": "ka_pin_test3",
                        "12e10bed-5edb-449d-92d0-46b357835695": "ka_pin_test4",
                        "2dd487e2-ee0a-4522-b4fd-ee3287c5668e": "ka_pin",
                        "8e898898-9bae-489c-8428-821508e45065": "ka_pin_test5",
                        "715adebf-c94a-4cce-bf6a-53b4f9e449a4": "ka_pin_test6",
                        "f046e079-9289-4f8c-a40f-47ebe2959724": "ka_pin_test7",
                        "931f5915-9161-4d82-a28a-ceac0a2e1590": "pinavto_test2",
                        "a2360541-f4b2-431e-a2cf-e1edf4de161b": "pinavto_test7",
                        "f9d7f402-6cb6-40e2-8783-31104436cba3": "pinavto_test8",
                        "fb474a9b-31ee-46fa-938f-210754f62814": "pinavto_test9",
                        "e271a9ab-108a-4c7c-9d6a-b22f5399a373": "checkup_HRM3",
                        "377dc3d7-c6b9-4f97-8cf5-0bf1f4c92c15": "Acc_cp_test",
                        "6e148cdd-acce-4998-b0f8-ca99c18abe61": "Accounting_copy_test",
                        "44f52259-9f5f-44c3-b627-7fe949729af8": "HRM3_test",
                        "68186041-dcde-4b9e-8c00-4ac51d9a0fd4": "HRM3_test_dev",
                        "81e5faa0-d6f8-4d11-8d20-a3c024f2e472": "bp_korp_test_dev",
                        "385d0ac8-22ec-40ee-9771-4936ef918c72": "Accounting_copy_test2",
                        "2df79626-6d6d-4533-8338-934367633c47": "Accounting_korp_test",
                        "4c1890ea-2a99-4ac9-99e0-4b00f1335c08": "cleverence",
                        "294ec8d1-f29a-4551-972a-470fbf34c56d": "alfa_pin_test",
                        "9d62ad8f-ba88-46e9-8a16-2c1392340faa": "pinavto_crm",
                        "03c9551d-16dc-41cd-9657-a73f499cfd20": "ka_pin_kalmykov",
                        "b23eeac2-348c-4d06-aaab-84cb722fdda7": "pinavto_test10"
                    }
                    
                    infobase_name = infobase_names.get(infobase, infobase)
                    
                    print(f"  [{i+1}] Session ID: {session_id}")
                    print(f"        Пользователь: {user_name}")
                    print(f"        Приложение: {app_id}")
                    print(f"        База: {infobase_name}")
                    print(f"        Спит: {hibernate}")
                    print(f"        Последняя активность: {last_active}")
                    print()
            else:
                print("Нет сессий в кластере")
    else:
        print("Нет доступных кластеров")
    
    print()
    print("="*70)
    print("Тестирование завершено")

if __name__ == "__main__":
    test_all_sessions_in_cluster()