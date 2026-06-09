import logging
import os
from typing import List, Optional
import httpx
import pandas as pd
from app.core.exceptions import DatasetLoaderError

logger = logging.getLogger(__name__)


class PVDatasetLoader:
    """Клас для завантаження та парсингу відкритих даних сонячної генерації ФЕС."""

    DRUIDS = {
        2017: "sm043zf7254",
        2018: "fb002mq9407",
        2019: "jj716hx9049"
    }

    def __init__(self, data_dir: str = "data/raw"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.timeout = 60.0

    def _get_download_url(self, year: int) -> str:
        """Повертає URL для завантаження CSV-файлу за вказаний рік."""
        if year not in self.DRUIDS:
            raise DatasetLoaderError(f"Немає даних для року {year}. Доступні роки: {list(self.DRUIDS.keys())}")
        
        druid = self.DRUIDS[year]
        return f"https://stacks.stanford.edu/file/druid:{druid}/{year}_pv_raw.csv"

    def _get_file_path(self, year: int) -> str:
        """Повертає шлях до локального файлу."""
        return os.path.join(self.data_dir, f"{year}_pv_raw.csv")

    async def download_year_data(self, year: int) -> str:
        """
        Асинхронно завантажує файл генерації за вказаний рік, якщо його немає локально.

        Повертає:
            Шлях до завантаженого файлу.
        """
        file_path = self._get_file_path(year)
        if os.path.exists(file_path):
            logger.info(f"Файл за {year} рік вже існує локально: {file_path}")
            return file_path

        url = self._get_download_url(year)
        logger.info(f"Завантаження даних генерації за {year} рік з {url}...")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Використовуємо streaming для великих файлів (хоча ці CSV ~15МБ)
                async with client.stream("GET", url) as response:
                    if response.status_code != 200:
                        error_msg = f"Помилка завантаження даних за {year} рік: HTTP {response.status_code}"
                        logger.error(error_msg)
                        raise DatasetLoaderError(error_msg)

                    with open(file_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                
                logger.info(f"Файл успішно завантажено та збережено: {file_path}")
            except Exception as e:
                if os.path.exists(file_path):
                    os.remove(file_path)
                error_msg = f"Критична помилка під час завантаження даних за {year} рік: {str(e)}"
                logger.error(error_msg)
                raise DatasetLoaderError(error_msg) from e

        return file_path

    async def download_all(self, years: Optional[List[int]] = None) -> List[str]:
        """Завантажує дані за всі вказані роки (за замовчуванням 2017-2019)."""
        if years is None:
            years = list(self.DRUIDS.keys())
        
        file_paths = []
        for year in years:
            path = await self.download_year_data(year)
            file_paths.append(path)
        return file_paths

    def load_year_data(self, year: int) -> pd.DataFrame:
        """
        Зчитує локальний CSV-файл сонячної генерації за вказаний рік.

        Повертає:
            Pandas DataFrame з колонками часу та потужності.
        """
        file_path = self._get_file_path(year)
        if not os.path.exists(file_path):
            raise DatasetLoaderError(f"Локальний файл для року {year} не знайдено. Спочатку завантажте його.")

        try:
            logger.debug(f"Зчитування файлу {file_path}...")
            # Зчитування файлу. Зазвичай там є колонка часу та колонка активної потужності.
            # Завантажимо перші декілька рядків, щоб автоматично розпізнати роздільник.
            df = pd.read_csv(file_path)
            
            # Стандартизація колонок. Перша колонка — час, друга — потужність.
            if len(df.columns) < 2:
                raise DatasetLoaderError(f"Файл {file_path} має містити щонайменше 2 колонки (час, потужність)")

            # Перейменовуємо для стандартизації: timestamp та active_power_kw
            time_col = df.columns[0]
            power_col = df.columns[1]
            
            df = df.rename(columns={
                time_col: "timestamp",
                power_col: "active_power_kw"
            })
            
            # Конвертація часу
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df["active_power_kw"] = pd.to_numeric(df["active_power_kw"], errors="coerce").fillna(0.0)
            
            logger.info(f"Успішно зчитано {len(df)} рядків даних генерації за {year} рік.")
            return df
        except Exception as e:
            error_msg = f"Помилка при зчитуванні даних за {year} рік з {file_path}: {str(e)}"
            logger.error(error_msg)
            raise DatasetLoaderError(error_msg) from e
