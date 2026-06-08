import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфігурація додатку з використанням Pydantic Settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Директорії для збереження даних
    BASE_DATA_DIR: str = "data"
    RAW_DATA_DIR: str = "data/raw"
    PROCESSED_DATA_DIR: str = "data/processed"
    PLOTS_DIR: str = "docs/images"

    # Рівень логування
    LOG_LEVEL: str = "INFO"

    # Параметри гео-локації (за замовчуванням координати 30 кВт сонячної установки)
    STATION_LATITUDE: float = 37.4275
    STATION_LONGITUDE: float = -122.1697
    STATION_CAPACITY_KW: float = 30.0


# Створення синглтону налаштувань
settings = Settings()

# Забезпечуємо створення необхідних папок при імпорті конфігурації
os.makedirs(settings.RAW_DATA_DIR, exist_ok=True)
os.makedirs(settings.PROCESSED_DATA_DIR, exist_ok=True)
os.makedirs(settings.PLOTS_DIR, exist_ok=True)
