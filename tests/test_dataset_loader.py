import os
import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from app.infrastructure.solar.dataset_loader import PVDatasetLoader
from app.core.exceptions import DatasetLoaderError


class AsyncContextManagerMock:
    """Допоміжний клас для мокування асинхронних контекстних менеджерів."""
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.mark.asyncio
async def test_download_year_data_success(tmp_path):
    # Використовуємо тимчасову директорію для тесту
    loader = PVDatasetLoader(data_dir=str(tmp_path))
    year = 2017
    
    mock_csv_content = b"time,power\n2017-03-01 00:00:00,0.0\n2017-03-01 00:01:00,0.1\n"
    
    # Мокаємо httpx stream response
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    
    # Мокаємо асинхронний ітератор по байтах
    async def mock_aiter_bytes(*args, **kwargs):
        yield mock_csv_content

    mock_response.aiter_bytes = mock_aiter_bytes
    
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.stream = MagicMock(return_value=AsyncContextManagerMock(mock_response))
    
    with patch("httpx.AsyncClient", return_value=mock_client):
        file_path = await loader.download_year_data(year)
        
        assert os.path.exists(file_path)
        with open(file_path, "rb") as f:
            content = f.read()
        assert content == mock_csv_content


@pytest.mark.asyncio
async def test_download_year_data_already_exists(tmp_path):
    loader = PVDatasetLoader(data_dir=str(tmp_path))
    year = 2017
    file_path = loader._get_file_path(year)
    
    # Створюємо файл локально
    with open(file_path, "w") as f:
        f.write("time,power\n")
        
    with patch("httpx.AsyncClient") as mock_client:
        path = await loader.download_year_data(year)
        assert path == file_path
        # Клієнт не повинен викликатися, якщо файл вже є
        mock_client.assert_not_called()


def test_load_year_data_success(tmp_path):
    loader = PVDatasetLoader(data_dir=str(tmp_path))
    year = 2017
    file_path = loader._get_file_path(year)
    
    # Записуємо тестовий CSV
    df_raw = pd.DataFrame({
        "Date Time": ["2017-03-01 12:00:00", "2017-03-01 12:01:00"],
        "Output Power (kW)": [15.5, 16.2]
    })
    df_raw.to_csv(file_path, index=False)
    
    df_loaded = loader.load_year_data(year)
    
    assert list(df_loaded.columns) == ["timestamp", "active_power_kw"]
    assert len(df_loaded) == 2
    assert df_loaded["active_power_kw"].iloc[0] == 15.5
    assert isinstance(df_loaded["timestamp"].iloc[0], pd.Timestamp)


def test_load_year_data_not_found(tmp_path):
    loader = PVDatasetLoader(data_dir=str(tmp_path))
    with pytest.raises(DatasetLoaderError) as exc_info:
        loader.load_year_data(2017)
    assert "не знайдено. Спочатку завантажте його" in str(exc_info.value)
