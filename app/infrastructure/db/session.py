import logging
from collections.abc import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.infrastructure.db.models import Base

logger = logging.getLogger(__name__)

# Створення асинхронного двигуна підключення
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True
)

# Створення фабрики асинхронних сесій
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db() -> None:
    """Створює таблиці та перетворює pv_telemetry у гіпертаблицю TimescaleDB."""
    async with engine.begin() as conn:
        logger.info("Ініціалізація бази даних та створення таблиць...")
        await conn.run_sync(Base.metadata.create_all)
        
        # Перетворення у гіпертаблицю TimescaleDB
        try:
            # Запит виконується лише якщо СУБД є PostgreSQL
            if conn.dialect.name == "postgresql":
                await conn.execute(
                    text("SELECT create_hypertable('pv_telemetry', 'timestamp', if_not_exists => TRUE);")
                )
                logger.info("Таблицю 'pv_telemetry' перетворено у гіпертаблицю TimescaleDB.")
        except Exception as e:
            logger.warning(
                f"Не вдалося виконати запит create_hypertable (можливо, розширення TimescaleDB не встановлене): {e}"
            )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection для отримання асинхронної сесії БД у FastAPI."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
