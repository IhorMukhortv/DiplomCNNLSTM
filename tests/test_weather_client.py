import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from app.infrastructure.weather.client import WeatherClient
from app.core.exceptions import WeatherServiceError


@pytest.mark.asyncio
async def test_get_historical_weather_success():
    client = WeatherClient()
    mock_response_data = {
        "latitude": 37.43,
        "longitude": -122.17,
        "generationtime_ms": 0.5,
        "utc_offset_seconds": 0,
        "timezone": "GMT",
        "timezone_abbreviation": "GMT",
        "elevation": 32.0,
        "hourly_units": {
            "time": "iso8601",
            "temperature_2m": "°C"
        },
        "hourly": {
            "time": ["2017-03-01T00:00:00Z", "2017-03-01T01:00:00Z"],
            "temperature_2m": [12.5, 11.8],
            "relative_humidity_2m": [80, 82],
            "cloud_cover": [20, 25],
            "direct_normal_irradiance": [0.0, 0.0],
            "diffuse_radiation": [0.0, 0.0],
            "shortwave_radiation": [0.0, 0.0]
        }
    }

    # Створюємо мок для httpx.AsyncClient.get
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", return_value=mock_response) as mock_get:
        data = await client.get_historical_weather(37.43, -122.17, "2017-03-01", "2017-03-01")

        mock_get.assert_called_once()
        assert data == mock_response_data
        assert data["hourly"]["temperature_2m"][0] == 12.5


@pytest.mark.asyncio
async def test_get_historical_weather_http_error():
    client = WeatherClient()

    # Створюємо мок для httpx.AsyncClient.get, який викликає HTTPStatusError
    mock_response = httpx.Response(404, request=httpx.Request("GET", "https://archive-api.open-meteo.com/v1/archive"))
    
    with patch("httpx.AsyncClient.get", side_effect=httpx.HTTPStatusError("Not Found", request=mock_response.request, response=mock_response)):
        with pytest.raises(WeatherServiceError) as exc_info:
            await client.get_historical_weather(37.43, -122.17, "2017-03-01", "2017-03-01")
        
        assert "HTTP помилка при запиті до погоди" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_historical_weather_api_error_response():
    client = WeatherClient()
    mock_error_data = {
        "error": True,
        "reason": "Latitude must be between -90 and 90 degrees."
    }

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = mock_error_data
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        with pytest.raises(WeatherServiceError) as exc_info:
            await client.get_historical_weather(95.0, -122.17, "2017-03-01", "2017-03-01")
        
        assert "Помилка API Open-Meteo" in str(exc_info.value)
