from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import get_settings
from ..core.logging import setup_logging
from .routes import router

# Настройка логирования
setup_logging()

# Создание приложения
app = FastAPI(
    title="Zabbix-1C Integration API", description="API для интеграции 1С с Zabbix", version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение маршрутов
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {"name": "Zabbix-1C Integration", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health():
    """Проверка здоровья"""
    settings = get_settings()
    return {
        "status": "healthy",
        "rac_path": str(settings.rac_path),
        "rac_host": settings.rac_host,
        "rac_port": settings.rac_port,
    }
