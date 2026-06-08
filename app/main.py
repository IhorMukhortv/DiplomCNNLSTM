import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router
from app.infrastructure.db.session import init_db

# Налаштування логування відповідно до конфігурації
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Життєвий цикл додатку: ініціалізація БД при старті."""
    logger.info("Запуск серверу FastAPI: ініціалізація компонентів інфраструктури...")
    try:
        await init_db()
    except Exception as e:
        logger.critical(f"Помилка ініціалізації бази даних при старті: {e}")
    yield
    logger.info("Зупинка серверу FastAPI...")


app = FastAPI(
    title="PV Forecasting API",
    description=(
        "Асинхронний REST API комп'ютерно-інтегрованої системи короткострокового "
        "прогнозування сонячної генерації на основі гібридних мереж CNN-LSTM."
    ),
    version="1.0.0",
    lifespan=lifespan
)

# Дозволяємо CORS для інтеграції з веб-інтерфейсом (якщо буде розроблятися далі)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Підключення маршрутизаторів API з префіксом версіонування
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["health"])
async def root():
    """Ендпоінт перевірки працездатності системи (Health Check)."""
    return {
        "status": "healthy",
        "system": "PV Forecasting System",
        "version": "1.0.0",
        "station_capacity_kw": settings.STATION_CAPACITY_KW
    }
