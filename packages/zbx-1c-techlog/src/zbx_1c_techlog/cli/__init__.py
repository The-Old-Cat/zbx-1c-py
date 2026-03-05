"""CLI модуль для zbx-1c-techlog"""

from .__main__ import cli

# Экспорт команд для entry points
collect = cli.commands["collect"]
send = cli.commands["send"]
summary = cli.commands["summary"]
check_logs = cli.commands["check"]

__all__ = [
    "cli",
    "collect",
    "send",
    "summary",
    "check_logs",
]
