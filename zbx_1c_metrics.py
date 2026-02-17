#!/usr/bin/env python
"""
Скрипт для получения метрик кластера из Zabbix ExternalScript

Использование:
    python zbx_1c_metrics.py <cluster_id>
    
Вывод JSON для Zabbix trapper:
    python zbx_1c_metrics.py <cluster_id> | zabbix_sender -T -i -
"""

import sys
import json
from pathlib import Path

# Добавляем путь к проекту
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path / "src"))

from zbx_1c.core.config import Settings
from zbx_1c.monitoring.cluster.manager import ClusterManager


def get_metrics(cluster_id: str) -> dict:
    """Получение метрик кластера"""
    settings = Settings()
    manager = ClusterManager(settings)

    metrics = manager.get_cluster_metrics(cluster_id)

    if not metrics:
        return {"error": f"Cluster {cluster_id} not found"}

    return metrics


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Cluster ID required"}))
        sys.exit(1)

    cluster_id = sys.argv[1]
    result = get_metrics(cluster_id)

    # Вывод JSON для Zabbix (UTF-8 байты напрямую)
    json_str = json.dumps(result, ensure_ascii=False, default=str)
    if sys.platform == "win32":
        sys.stdout.buffer.write((json_str + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()
    else:
        print(json_str)
