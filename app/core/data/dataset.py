import logging
import os
from typing import Tuple, List, Optional
import numpy as np
import pandas as pd
from app.core.exceptions import DataPreprocessingError

logger = logging.getLogger(__name__)


class CustomMinMaxScaler:
    """Власний масштабувальник MinMaxScaler для усунення залежності від scikit-learn."""

    def __init__(self):
        self.min_values: Optional[pd.Series] = None
        self.max_values: Optional[pd.Series] = None
        self.diff_values: Optional[pd.Series] = None

    def fit(self, df: pd.DataFrame) -> None:
        """Обчислює мінімум та максимум для кожного стовпця."""
        self.min_values = df.min()
        self.max_values = df.max()
        self.diff_values = self.max_values - self.min_values
        
        # Обробляємо випадок константних ознак, щоб уникнути ділення на 0
        self.diff_values = self.diff_values.replace(0.0, 1.0)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Масштабує дані в діапазон [0, 1]."""
        if self.min_values is None or self.diff_values is None:
            raise DataPreprocessingError("Масштабувальник не навчено! Спочатку викличте метод fit().")
        return (df - self.min_values) / self.diff_values

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Навчає та масштабує дані."""
        self.fit(df)
        return self.transform(df)

    def inverse_transform_column(self, values: np.ndarray, column_name: str) -> np.ndarray:
        """Перетворює масштабовані значення назад до вихідних одиниць виміру."""
        if self.min_values is None or self.diff_values is None:
            raise DataPreprocessingError("Масштабувальник не навчено!")
        col_min = self.min_values[column_name]
        col_diff = self.diff_values[column_name]
        return values * col_diff + col_min


def load_and_split_data(
    csv_path: str,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Завантажує набір даних та розділяє його хронологічно на три частини (Train, Val, Test).

    Повертає:
        Кортеж з трьох DataFrame: (train_df, val_df, test_df)
    """
    if not os.path.exists(csv_path):
        raise DataPreprocessingError(f"Файл даних за шляхом {csv_path} не знайдено.")

    # Перевірка правильності сум коефіцієнтів
    if not np.isclose(train_ratio + val_ratio + test_ratio, 1.0):
        raise DataPreprocessingError("Сума часток розбиття (train, val, test) повинна дорівнювати 1.0.")

    logger.info(f"Завантаження даних для розбиття з {csv_path}...")
    df = pd.read_csv(csv_path)

    # Видаляємо timestamp для моделювання (зберігаємо лише числові ознаки)
    if "timestamp" in df.columns:
        df = df.drop(columns=["timestamp"])

    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    train_df = df.iloc[:train_end].copy()
    val_df = df.iloc[train_end:val_end].copy()
    test_df = df.iloc[val_end:].copy()

    logger.info(
        f"Дані успішно розділено хронологічно: "
        f"Train={len(train_df)} рядків ({train_ratio*100:.0f}%), "
        f"Val={len(val_df)} рядків ({val_ratio*100:.0f}%), "
        f"Test={len(test_df)} рядків ({test_ratio*100:.0f}%)."
    )

    return train_df, val_df, test_df


class TimeSeriesWindowGenerator:
    """Генератор ковзного вікна для перетворення часових рядів у входи нейромережі."""

    def __init__(
        self,
        lookback: int = 24,
        horizon: int = 1,
        target_column: str = "active_power_kw",
        feature_columns: Optional[List[str]] = None
    ):
        self.lookback = lookback
        self.horizon = horizon
        self.target_column = target_column
        self.feature_columns = feature_columns

    def generate_windows(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Створює матриці X та y за методом ковзного вікна.

        Повертає:
            X: np.ndarray розміром (samples, lookback, num_features)
            y: np.ndarray розміром (samples, horizon)
        """
        # Якщо колонки ознак не передано, використовуємо всі колонки
        cols = self.feature_columns if self.feature_columns is not None else list(df.columns)
        
        if self.target_column not in df.columns:
            raise DataPreprocessingError(f"Цільова колонка {self.target_column} відсутня у DataFrame.")
        for col in cols:
            if col not in df.columns:
                raise DataPreprocessingError(f"Колонка ознаки {col} відсутня у DataFrame.")

        features = df[cols].values
        target = df[self.target_column].values

        X_list: List[np.ndarray] = []
        y_list: List[np.ndarray] = []

        num_samples = len(df) - self.lookback - self.horizon + 1
        if num_samples <= 0:
            logger.warning("Розмір датафрейму менший за сумарну довжину вікна (lookback + horizon).")
            return (
                np.empty((0, self.lookback, len(cols)), dtype=np.float32),
                np.empty((0, self.horizon), dtype=np.float32)
            )

        for i in range(num_samples):
            # Вхідні дані: від кроку i до i + lookback - 1
            X_list.append(features[i : i + self.lookback])
            # Цільові дані: від кроку i + lookback до i + lookback + horizon - 1
            y_list.append(target[i + self.lookback : i + self.lookback + self.horizon])

        return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.float32)


def get_default_scaler() -> CustomMinMaxScaler:
    """Завантажує та навчає масштабувальник на навчальних даних або дефолтних фізичних межах."""
    scaler = CustomMinMaxScaler()
    csv_path = os.path.join("data", "raw", "pv_weather_data.csv")
    
    if os.path.exists(csv_path):
        try:
            train_df, _, _ = load_and_split_data(csv_path)
            scaler.fit(train_df)
            logger.info("Масштабувальник успішно навчено на історичному датасеті.")
            return scaler
        except Exception as e:
            logger.warning(f"Не вдалося навчити масштабувальник на CSV: {e}. Перехід до дефолтного.")
            
    # Запасний варіант з фізичними межами
    dummy_df = pd.DataFrame({
        "temperature_2m": [-10.0, 45.0],
        "relative_humidity_2m": [0.0, 100.0],
        "cloud_cover": [0.0, 100.0],
        "direct_normal_irradiance": [0.0, 1100.0],
        "diffuse_horizontal_irradiance": [0.0, 600.0],
        "global_horizontal_irradiance": [0.0, 1200.0],
        "active_power_kw": [0.0, 30.0]
    })
    scaler.fit(dummy_df)
    logger.info("Масштабувальник ініціалізовано дефолтними фізичними межами.")
    return scaler


# Глобальний екземпляр масштабувальника для всієї системи
global_scaler = get_default_scaler()

