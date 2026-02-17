#!/usr/bin/env python
"""
Отправка статуса кластера в Zabbix

Использование:
    python send_cluster_status.py <cluster_id>
    python send_cluster_status.py --all  # отправить все кластеры

Требует установленного zabbix_sender в PATH
"""

import sys
import os
import subprocess
from pathlib import Path

# Добавляем путь к проекту
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path / "src"))

from zbx_1c.core.config import Settings
from zbx_1c.monitoring.cluster.discovery import discover_clusters


def send_status(cluster_id: str, status: str, zabbix_host: str = None, host_name: str = None) -> bool:
    """
    Отправка статуса кластера в Zabbix через zabbix_sender
    
    Args:
        cluster_id: ID кластера
        status: Статус (available/unavailable/unknown)
        zabbix_host: Хост Zabbix сервера
        host_name: Имя хоста в Zabbix
        
    Returns:
        True если успешно
    """
    settings = Settings()
    
    if not zabbix_host:
        zabbix_host = os.environ.get('ZABBIX_SERVER', '127.0.0.1')
    if not host_name:
        host_name = os.environ.get('ZABBIX_HOST', '1C Cluster')
    
    cmd = [
        'zabbix_sender',
        '-z', zabbix_host,
        '-s', host_name,
        '-k', f'zbx1cpy.cluster.status[{cluster_id}]',
        '-o', status
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"[OK] Sent status '{status}' for cluster {cluster_id}")
            return True
        else:
            print(f"[ERROR] zabbix_sender failed: {result.stderr}")
            return False
    except FileNotFoundError:
        print(f"[ERROR] zabbix_sender not found in PATH")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to send status: {e}")
        return False


def send_all_statuses():
    """Отправить статусы всех кластеров"""
    settings = Settings()
    clusters = discover_clusters(settings)
    
    if not clusters:
        print("[WARN] No clusters found")
        return False
    
    success_count = 0
    for cluster in clusters:
        if send_status(str(cluster.id), cluster.status):
            success_count += 1
    
    print(f"\n[INFO] Sent {success_count}/{len(clusters)} cluster statuses")
    return success_count == len(clusters)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python send_cluster_status.py <cluster_id>")
        print("  python send_cluster_status.py --all")
        print("\nEnvironment variables:")
        print("  ZABBIX_SERVER - Zabbix server host (default: 127.0.0.1)")
        print("  ZABBIX_HOST   - Host name in Zabbix (default: '1C Cluster')")
        sys.exit(1)
    
    if sys.argv[1] == '--all':
        success = send_all_statuses()
        sys.exit(0 if success else 1)
    else:
        cluster_id = sys.argv[1]
        settings = Settings()
        clusters = discover_clusters(settings)
        
        cluster = next((c for c in clusters if str(c.id) == cluster_id), None)
        if not cluster:
            print(f"[ERROR] Cluster {cluster_id} not found")
            sys.exit(1)
        
        success = send_status(cluster_id, cluster.status)
        sys.exit(0 if success else 1)
