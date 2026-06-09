import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
from app.core.data.pipeline import DataPipeline
from app.infrastructure.weather.client import WeatherClient
from app.infrastructure.solar.dataset_loader import PVDatasetLoader

async def main():
    print("Setting up benchmark...")

    # Mock weather client so we don't benchmark API calls
    mock_weather_client = MagicMock(spec=WeatherClient)
    mock_weather_data = {
        "hourly": {
            "time": ["2017-03-01T08:00:00Z"],
            "temperature_2m": [15.0],
            "relative_humidity_2m": [50],
            "cloud_cover": [10],
            "direct_normal_irradiance": [100.0],
            "diffuse_radiation": [50.0],
            "shortwave_radiation": [150.0]
        }
    }
    mock_weather_client.get_historical_weather = AsyncMock(return_value=mock_weather_data)

    dataset_loader = PVDatasetLoader()
    pipeline = DataPipeline(
        weather_client=mock_weather_client,
        dataset_loader=dataset_loader
    )

    # Ensure data is downloaded first so we only benchmark read/concat and processing
    print("Pre-downloading dataset files to ensure cache hit...")
    await dataset_loader.download_all([2017, 2018, 2019])

    print("Running baseline benchmark (5 iterations)...")
    times = []
    for i in range(5):
        start_time = time.perf_counter()
        await pipeline.run(start_date="2017-01-01", end_date="2019-12-31")
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        times.append(elapsed)
        print(f"Iteration {i+1}: {elapsed:.4f} seconds")

    avg_time = sum(times) / len(times)
    print(f"Average execution time: {avg_time:.4f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
