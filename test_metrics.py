#!/usr/bin/env python
"""
Тест получения метрик через ClusterManager
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from zbx_1c.core.config import Settings
from zbx_1c.monitoring.cluster.manager import ClusterManager


def main():
    settings = Settings()
    manager = ClusterManager(settings)

    # ID кластера
    cluster_id = "f93863ed-3fdb-4e01-a74c-e112c81b053b"

    # Получаем метрики
    metrics = manager.get_cluster_metrics(cluster_id)

    if metrics:
        print(json.dumps(metrics, indent=2, ensure_ascii=False, default=str))
    else:
        print("Не удалось получить метрики")
        sys.exit(1)


if __name__ == "__main__":
    main()
