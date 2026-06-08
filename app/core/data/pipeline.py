import logging
import os
from typing import Optional
import pandas as pd
from app.core.config import settings
from app.core.exceptions import DataPreprocessingError
from app.infrastructure.weather.client import WeatherClient
from app.infrastructure.solar.dataset_loader import PVDatasetLoader

logger = logging.getLogger(__name__)


class DataPipeline:
    """Конвеєр збору, обробки та об'єднання даних сонячної генерації та погоди."""

    def __init__(
        self,
        weather_client: Optional[WeatherClient] = None,
        dataset_loader: Optional[PVDatasetLoader] = None
    ):
        self.weather_client = weather_client or WeatherClient()
        self.dataset_loader = dataset_loader or PVDatasetLoader(data_dir=settings.RAW_DATA_DIR)

    async def run(self, start_date: str = "2017-03-01", end_date: str = "2019-12-31") -> str:
        """
        Запускає конвеєр збору та об'єднання даних.

        Параметри:
            start_date: початкова дата у форматі YYYY-MM-DD.
            end_date: кінцева дата у форматі YYYY-MM-DD.

        Повертає:
            Шлях до збереженого CSV-файлу з об'єднаними даними.
        """
        logger.info(f"Запуск конвеєра збору даних за період з {start_date} по {end_date}...")

        # 1. Завантаження та зчитування даних сонячної генерації (2017-2019)
        # Визначаємо роки, які входять у період
        start_year = int(start_date.split("-")[0])
        end_year = int(end_date.split("-")[0])
        years_to_load = [y for y in range(start_year, end_year + 1) if y in [2017, 2018, 2019]]

        if not years_to_load:
            raise DataPreprocessingError(
                f"Вказаний період {start_date} - {end_date} не містить підтримуваних років (2017-2019)."
            )

        logger.info(f"Завантаження даних генерації за роки: {years_to_load}")
        await self.dataset_loader.download_all(years_to_load)

        # Зчитування та об'єднання даних генерації
        pv_dfs = []
        for year in years_to_load:
            df_year = self.dataset_loader.load_year_data(year)
            pv_dfs.append(df_year)

        pv_df = pd.concat(pv_dfs, ignore_index=True)
        logger.info(f"Загалом зчитано {len(pv_df)} похвилинних записів сонячної генерації.")

        # 2. Адаптація часового поясу та агрегація даних генерації до годинного інтервалу
        try:
            # Дані ФЕС записані за місцевим часом (тихоокеанський час Америки - PST/PDT).
            # Конвертуємо їх у UTC для відповідності з даними погоди.
            pv_df["timestamp"] = pv_df["timestamp"].dt.tz_localize(
                "America/Los_Angeles", ambiguous="NaT", nonexistent="shift_forward"
            )
            pv_df = pv_df.dropna(subset=["timestamp"])
            pv_df["timestamp"] = pv_df["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
        except Exception as e:
            logger.warning(
                f"Не вдалося виконати конвертацію часового поясу: {e}. "
                "Продовжуємо роботу з часом без змін поясу."
            )

        # Агрегація до годинних інтервалів (середнє значення потужності в kW за годину)
        pv_df = pv_df.set_index("timestamp")
        pv_hourly = pv_df.resample("h").mean()
        # Якщо в якусь годину не було записів, заповнюємо NaN
        pv_hourly = pv_hourly.reset_index()
        logger.info(f"Дані генерації агреговані до {len(pv_hourly)} годинних записів.")

        # 3. Отримання даних погоди через асинхронний клієнт
        logger.info(
            f"Завантаження погодних даних для координат ({settings.STATION_LATITUDE}, {settings.STATION_LONGITUDE})..."
        )
        weather_data = await self.weather_client.get_historical_weather(
            latitude=settings.STATION_LATITUDE,
            longitude=settings.STATION_LONGITUDE,
            start_date=start_date,
            end_date=end_date
        )

        # Парсинг погоди
        hourly_weather = weather_data.get("hourly", {})
        weather_df = pd.DataFrame({
            "timestamp": pd.to_datetime(hourly_weather.get("time", [])),
            "temperature_2m": hourly_weather.get("temperature_2m", []),
            "relative_humidity_2m": hourly_weather.get("relative_humidity_2m", []),
            "cloud_cover": hourly_weather.get("cloud_cover", []),
            "direct_normal_irradiance": hourly_weather.get("direct_normal_irradiance", []),
            "diffuse_horizontal_irradiance": hourly_weather.get("diffuse_radiation", []),
            "global_horizontal_irradiance": hourly_weather.get("shortwave_radiation", [])
        })
        
        # Конвертуємо час погоди у tz-naive UTC для коректного об'єднання
        if weather_df["timestamp"].dt.tz is not None:
            weather_df["timestamp"] = weather_df["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
            
        logger.info(f"Завантажено {len(weather_df)} годинних записів погоди.")

        # 4. Об'єднання (join) даних за часовою міткою
        logger.info("Об'єднання метеоданих та телеметрії генерації ФЕС...")
        merged_df = pd.merge(weather_df, pv_hourly, on="timestamp", how="left")

        # Очищення та заповнення пропусків
        # Якщо генерація відсутня (наприклад, вночі або під час технічного обслуговування):
        # Якщо GHI (глобальна інсоляція) дорівнює 0, то генерація точно дорівнює 0.0
        if "active_power_kw" in merged_df.columns:
            # Заповнюємо нулями там, де немає інсоляції
            merged_df.loc[merged_df["global_horizontal_irradiance"] == 0, "active_power_kw"] = 0.0
            # Для інших пропусків використовуємо лінійну інтерполяцію (або заповнюємо нулями)
            merged_df["active_power_kw"] = merged_df["active_power_kw"].interpolate(method="linear").fillna(0.0)
            # Забезпечуємо, щоб генерація не була від'ємною
            merged_df["active_power_kw"] = merged_df["active_power_kw"].clip(lower=0.0)

        # 5. Збереження результату
        output_path = os.path.join(settings.RAW_DATA_DIR, "pv_weather_data.csv")
        merged_df.to_csv(output_path, index=False)
        logger.info(
            f"Конвеєр успішно завершив роботу. Об'єднаний набір даних збережено у {output_path} "
            f"({len(merged_df)} рядків, {len(merged_df.columns)} колонок)."
        )

        return output_path
