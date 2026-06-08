class ForecastingSystemError(Exception):
    """Базовий виняток для всієї системи прогнозування."""
    pass


class WeatherServiceError(ForecastingSystemError):
    """Виняток, що виникає при помилках отримання даних про погоду."""
    pass


class DatasetLoaderError(ForecastingSystemError):
    """Виняток, що виникає при завантаженні або парсингу наборів даних."""
    pass


class DataPreprocessingError(ForecastingSystemError):
    """Виняток, що виникає при обробці чи агрегації даних."""
    pass
