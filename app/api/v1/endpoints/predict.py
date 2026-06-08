import logging
import os
from datetime import timedelta
import numpy as np
import pandas as pd
import tensorflow as tf
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db.session import get_db
from app.infrastructure.db.models import PVTelemetry
from app.core.models.cnn_lstm import build_cnn_lstm_model
from app.core.data.dataset import CustomMinMaxScaler, load_and_split_data

logger = logging.getLogger(__name__)

router = APIRouter()

# Ознаки у правильному порядку
FEATURE_COLUMNS = [
    "temperature_2m",
    "relative_humidity_2m",
    "cloud_cover",
    "direct_normal_irradiance",
    "diffuse_horizontal_irradiance",
    "global_horizontal_irradiance",
    "active_power_kw"
]


def load_scaler() -> CustomMinMaxScaler:
    """Завантажує та навчає масштабувальник на навчальних даних або дефолтних межах."""
    scaler = CustomMinMaxScaler()
    csv_path = os.path.join("data", "raw", "pv_weather_data.csv")
    
    if os.path.exists(csv_path):
        try:
            train_df, _, _ = load_and_split_data(csv_path)
            scaler.fit(train_df)
            logger.info("Масштабувальник для API успішно навчено на історичному датасеті.")
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
    logger.info("Масштабувальник для API ініціалізовано дефолтними фізичними межами.")
    return scaler


# Ініціалізація глобальних об'єктів при старті модуля
scaler = load_scaler()

# Спроба завантажити збережену навчену модель, інакше створюється екземпляр з випадковими вагами для тестів
model_path = os.path.join("app", "core", "models", "saved_model.keras")
if os.path.exists(model_path):
    try:
        model = tf.keras.models.load_model(model_path)
        logger.info(f"Навчену модель успішно завантажено з {model_path}.")
    except Exception as e:
        logger.error(f"Помилка завантаження моделі Keras: {e}. Створення тестової випадкової моделі.")
        model = build_cnn_lstm_model(input_shape=(24, len(FEATURE_COLUMNS)))
else:
    logger.warning("Збережену модель saved_model.keras не знайдено. Ініціалізація випадкової моделі.")
    model = build_cnn_lstm_model(input_shape=(24, len(FEATURE_COLUMNS)))


@router.get("/")
async def predict_next_hour(db: AsyncSession = Depends(get_db)):
    """
    Завантажує останні 24 годинних записи з бази даних,
    масштабує їх та розраховує прогноз генерації на наступну годину.
    """
    logger.info("Отримано запит на розрахунок короткострокового прогнозу...")
    
    # Отримуємо останні 24 записи за спаданням часу
    stmt = select(PVTelemetry).order_by(PVTelemetry.timestamp.desc()).limit(24)
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    if len(records) < 24:
        logger.warning(f"Недостатньо записів у базі даних: знайдено лише {len(records)} з 24.")
        raise HTTPException(
            status_code=400,
            detail=(
                f"Недостатньо даних для прогнозування. Потрібно мінімум 24 послідовних "
                f"годинних записів телеметрії, знайдено лише {len(records)}."
            )
        )
        
    # Хронологічний порядок має бути зростаючим
    records = list(reversed(records))
    
    # Формуємо DataFrame
    data_list = []
    for r in records:
        data_list.append({
            "temperature_2m": r.temperature_2m,
            "relative_humidity_2m": r.relative_humidity_2m,
            "cloud_cover": r.cloud_cover,
            "direct_normal_irradiance": r.direct_normal_irradiance,
            "diffuse_horizontal_irradiance": r.diffuse_horizontal_irradiance,
            "global_horizontal_irradiance": r.global_horizontal_irradiance,
            "active_power_kw": r.active_power_kw
        })
        
    df = pd.DataFrame(data_list)
    
    # 1. Масштабування
    df_scaled = scaler.transform(df)
    
    # 2. Перетворення в NumPy-тензор [1, 24, 7]
    X_input = df_scaled[FEATURE_COLUMNS].values
    X_input = np.expand_dims(X_input, axis=0).astype(np.float32)
    
    # 3. Інференс моделі
    try:
        pred_scaled = model.predict(X_input, verbose=0)
        pred_scaled_val = float(pred_scaled[0, 0])
    except Exception as e:
        logger.error(f"Помилка інференсу моделі CNN-LSTM: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Внутрішня помилка розрахунку прогнозу нейромережею: {e}"
        )
        
    # 4. Зворотна денормалізація виходу
    pred_kw = scaler.inverse_transform_column(np.array([pred_scaled_val]), "active_power_kw")[0]
    pred_kw = float(max(0.0, pred_kw)) # фізично потужність не може бути від'ємною
    
    # Час прогнозу — наступна година після останнього запису
    latest_time = records[-1].timestamp
    forecast_time = latest_time + timedelta(hours=1)
    
    logger.info(f"Прогноз на {forecast_time} успішно розраховано: {pred_kw:.4f} кВт")
    
    return {
        "forecast_timestamp": forecast_time.isoformat(),
        "input_last_timestamp": latest_time.isoformat(),
        "predicted_active_power_kw": round(pred_kw, 4)
    }
