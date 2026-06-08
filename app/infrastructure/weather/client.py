import logging
from typing import Dict, Any
import httpx
from app.core.exceptions import WeatherServiceError

logger = logging.getLogger(__name__)

class WeatherClient:
    """Асинхронний клієнт для отримання архівних погодних даних з Open-Meteo API."""

    def __init__(self, base_url: str = "https://archive-api.open-meteo.com/v1/archive"):
        self.base_url = base_url
        self.timeout = 30.0

    async def get_historical_weather(
        self, latitude: float, longitude: float, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """
        Отримує історичні годинні погодні дані за вказаний період.

        Параметри:
            latitude: широта локації.
            longitude: довгота локації.
            start_date: початкова дата у форматі YYYY-MM-DD.
            end_date: кінцева дата у форматі YYYY-MM-DD.

        Повертає:
            Словник з годинними метеорологічними даними.
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "timezone": "UTC",
            "hourly": (
                "temperature_2m,"
                "relative_humidity_2m,"
                "cloud_cover,"
                "direct_normal_irradiance,"
                "diffuse_radiation,"
                "shortwave_radiation"
            ),
        }

        logger.debug(
            f"Запит до Open-Meteo Archive API: URL={self.base_url}, "
            f"координати=({latitude}, {longitude}), період=[{start_date}, {end_date}]"
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP помилка при запиті до погоди: {e.response.status_code} - {e.response.text}"
                logger.error(error_msg)
                raise WeatherServiceError(error_msg) from e
            except httpx.RequestError as e:
                error_msg = f"Помилка мережі при запиті до погоди: {str(e)}"
                logger.error(error_msg)
                raise WeatherServiceError(error_msg) from e

        data = response.json()
        
        # Перевірка на наявність помилок в самому тілі успішної відповіді Open-Meteo
        if "error" in data:
            error_msg = f"Помилка API Open-Meteo: {data.get('reason', 'Невідома помилка')}"
            logger.error(error_msg)
            raise WeatherServiceError(error_msg)

        hourly_data = data.get("hourly", {})
        time_records = hourly_data.get("time", [])
        
        logger.info(
            f"Успішно отримано дані погоди: {len(time_records)} годинних записів за період від "
            f"{start_date} до {end_date}"
        )
        
        return data
