"""CLI модуль для zbx-1c-rac"""

from .__main__ import cli

# Экспорт команд для entry points
check_ras = cli.commands["check"]
discovery = cli.commands["discovery"]
list_clusters = cli.commands["clusters"]
get_metrics = cli.commands["metrics"]
get_cluster_status = cli.commands["status"]
get_infobases_cmd = cli.commands["infobases"]
get_sessions_cmd = cli.commands["sessions"]
get_jobs_cmd = cli.commands["jobs"]
get_process_memory = cli.commands["memory"]
test_connection = cli.commands["test"]
check_config_cmd = cli.commands["check-config"]

__all__ = [
    "cli",
    "check_ras",
    "discovery",
    "list_clusters",
    "get_metrics",
    "get_cluster_status",
    "get_infobases_cmd",
    "get_sessions_cmd",
    "get_jobs_cmd",
    "get_process_memory",
    "test_connection",
    "check_config_cmd",
]
