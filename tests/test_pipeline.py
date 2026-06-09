import os
import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.config import settings
from app.core.data.pipeline import DataPipeline
from app.core.exceptions import DataPreprocessingError


@pytest.mark.asyncio
async def test_pipeline_run_success(tmp_path):
    # Тимчасово перевизначаємо папки для збереження результатів тесту
    test_raw_dir = str(tmp_path)
    
    # Створюємо мок-клієнт погоди
    mock_weather_client = MagicMock()
    mock_weather_data = {
        "hourly": {
            "time": ["2017-03-01T08:00:00Z", "2017-03-01T09:00:00Z", "2017-03-01T10:00:00Z"],
            "temperature_2m": [15.0, 16.0, 17.0],
            "relative_humidity_2m": [50, 48, 45],
            "cloud_cover": [10, 20, 30],
            "direct_normal_irradiance": [100.0, 200.0, 300.0],
            "diffuse_radiation": [50.0, 60.0, 70.0],
            "shortwave_radiation": [150.0, 260.0, 370.0]
        }
    }
    mock_weather_client.get_historical_weather = AsyncMock(return_value=mock_weather_data)

    # Створюємо мок-завантажувач датасету ФЕС
    mock_dataset_loader = MagicMock()
    mock_dataset_loader.download_all = AsyncMock()
    
    # Створюємо похвилинні дані для тесту
    # Для простоти, запишемо за місцевим часом (UTC-8)
    pv_time_range = pd.date_range(start="2017-03-01 00:00:00", end="2017-03-01 02:00:00", freq="min")
    pv_raw_df = pd.DataFrame({
        "timestamp": pv_time_range,
        "active_power_kw": [10.0] * len(pv_time_range)
    })
    mock_dataset_loader.load_year_data.return_value = pv_raw_df

    # Патчимо settings.RAW_DATA_DIR
    with patch.object(settings, "RAW_DATA_DIR", test_raw_dir):
        pipeline = DataPipeline(
            weather_client=mock_weather_client,
            dataset_loader=mock_dataset_loader
        )
        
        output_path = await pipeline.run(start_date="2017-03-01", end_date="2017-03-01")
        
        # Перевірка результату
        assert output_path == os.path.join(test_raw_dir, "pv_weather_data.csv")
        assert os.path.exists(output_path)
        
        # Перевіряємо вміст згенерованого файлу
        df_res = pd.read_csv(output_path)
        
        assert len(df_res) == 3  # Має бути 3 годинних записи з погодних даних
        assert "active_power_kw" in df_res.columns
        assert "temperature_2m" in df_res.columns
        assert "global_horizontal_irradiance" in df_res.columns
        
        # Перевіряємо, що інсоляція відповідає
        assert df_res["global_horizontal_irradiance"].iloc[0] == 150.0
        
        # Перевіряємо, що генерація заповнена (оскільки ми агрегували середнє)
        # 2017-03-01 00:00:00 за місцевим часом = 2017-03-01 08:00:00 UTC
        # Так як ми заповнили 10.0 kW похвилинно, середнє годинне має бути 10.0
        assert df_res["active_power_kw"].iloc[0] == 10.0

@pytest.mark.asyncio
async def test_pipeline_run_tz_localize_failure(tmp_path):
    # Тимчасово перевизначаємо папки для збереження результатів тесту
    test_raw_dir = str(tmp_path)

    # Створюємо мок-клієнт погоди
    mock_weather_client = MagicMock()
    mock_weather_data = {
        "hourly": {
            "time": ["2017-03-01T08:00:00Z", "2017-03-01T09:00:00Z", "2017-03-01T10:00:00Z"],
            "temperature_2m": [15.0, 16.0, 17.0],
            "relative_humidity_2m": [50, 48, 45],
            "cloud_cover": [10, 20, 30],
            "direct_normal_irradiance": [100.0, 200.0, 300.0],
            "diffuse_radiation": [50.0, 60.0, 70.0],
            "shortwave_radiation": [150.0, 260.0, 370.0]
        }
    }
    mock_weather_client.get_historical_weather = AsyncMock(return_value=mock_weather_data)

    # Створюємо мок-завантажувач датасету ФЕС
    mock_dataset_loader = MagicMock()
    mock_dataset_loader.download_all = AsyncMock()

    # Створюємо похвилинні дані для тесту
    pv_time_range = pd.date_range(start="2017-03-01 00:00:00", end="2017-03-01 02:00:00", freq="min")
    pv_raw_df = pd.DataFrame({
        "timestamp": pv_time_range,
        "active_power_kw": [10.0] * len(pv_time_range)
    })
    mock_dataset_loader.load_year_data.return_value = pv_raw_df


    # Мокаємо tz_localize, щоб він кидав помилку лише для America/Los_Angeles
    original_tz_localize = pd.core.indexes.accessors.DatetimeProperties.tz_localize
    def side_effect_tz_localize(self, *args, **kwargs):
        if args and args[0] == "America/Los_Angeles":
            raise Exception("mocked tz error")
        return original_tz_localize(self, *args, **kwargs)

    # Патчимо settings.RAW_DATA_DIR і pandas tz_localize
    with patch.object(settings, "RAW_DATA_DIR", test_raw_dir), \
         patch("pandas.core.indexes.accessors.DatetimeProperties.tz_localize", autospec=True, side_effect=side_effect_tz_localize), \
         patch("app.core.data.pipeline.logger.warning") as mock_logger_warning:


        pipeline = DataPipeline(
            weather_client=mock_weather_client,
            dataset_loader=mock_dataset_loader
        )

        output_path = await pipeline.run(start_date="2017-03-01", end_date="2017-03-01")

        # Перевірка результату
        assert output_path == os.path.join(test_raw_dir, "pv_weather_data.csv")
        assert os.path.exists(output_path)

        # Перевіряємо, що логер викликався з попередженням
        mock_logger_warning.assert_called_once()
        warning_msg = mock_logger_warning.call_args[0][0]
        assert "Не вдалося виконати конвертацію часового поясу" in warning_msg
        assert "mocked tz error" in warning_msg
