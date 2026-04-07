"""Запуск FastAPI сервиса для мониторинга техжурнала 1С"""

import uvicorn


def run_server(host: str = "0.0.0.0", port: int = 8001, reload: bool = False):
    """
    Запуск сервера.

    Args:
        host: Хост для прослушивания.
        port: Порт для прослушивания.
        reload: Перезагрузка при изменении кода (для разработки).
    """
    uvicorn.run(
        "zbx_1c_techlog.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


def main():
    """Точка входа для CLI"""
    import argparse

    parser = argparse.ArgumentParser(description="Zabbix 1C TechJournal Monitoring API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    run_server(host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
