import logging
from datetime import timedelta
from typing import List, Optional
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db.session import get_db
from app.infrastructure.db.models import PVTelemetry
from app.core.data.dataset import global_scaler as scaler
from app.infrastructure.storage.model_registry import model_registry, ModelRegistry
from app.core.models.online_learning import retrain_on_recent_data

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


class RetrainRequest(BaseModel):
    """Схема запиту для запуску мультимасштабного донавчання."""
    slot: str = Field(
        ModelRegistry.SLOT_MONTH,
        description="Слот ансамблю: 'year' (річні патерни) або 'month' (місячні умови)"
    )
    limit_hours: Optional[int] = Field(
        None,
        ge=25,
        le=8760,
        description="Кількість годин телеметрії (за замовчуванням: year=8760, month=720)"
    )
    epochs: int = Field(5, ge=1, le=50, description="Кількість епох донавчання")
    learning_rate: float = Field(0.0001, ge=1e-6, le=1e-2, description="Швидкість навчання")
    batch_size: int = Field(16, ge=1, le=128, description="Розмір батчу")


class RetrainResponse(BaseModel):
    """Схема відповіді з результатами мультимасштабного донавчання."""
    status: str = Field(..., description="Статус виконання")
    slot: str = Field(..., description="Слот ансамблю, що був оновлений")
    records_used: int = Field(..., description="Кількість використаних записів")
    windows_generated: int = Field(..., description="Кількість згенерованих навчальних вікон")
    loss_before: float = Field(..., description="Помилка MSE до донавчання")
    loss_after: float = Field(..., description="Помилка MSE після донавчання")
    loss_history: List[float] = Field(..., description="Історія значень функції втрат")


@router.get("/")
async def predict_next_hour(db: AsyncSession = Depends(get_db)):
    """
    Завантажує останні 24 годинних записи з бази даних,
    масштабує їх та розраховує прогноз генерації на наступну годину
    з використанням мультимасштабного темпорального ансамблю.

    Ансамбль складається з:
      - Base (EMA-200): глобальні патерни
      - Year (EMA-50): сезонні тренди
      - Month (EMA-12): актуальні умови
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
    
    # 3. Інференс мультимасштабного ансамблю
    models = model_registry.get_models()
    labels = model_registry.get_model_labels()
    
    predictions = []
    model_details = []
    for m, label in zip(models, labels):
        try:
            pred_scaled = m.predict(X_input, verbose=0)
            pred_scaled_val = float(pred_scaled[0, 0])
            pred_kw = scaler.inverse_transform_column(np.array([pred_scaled_val]), "active_power_kw")[0]
            pred_kw = float(max(0.0, pred_kw))  # фізично потужність не може бути від'ємною
            predictions.append(pred_kw)
            model_details.append({"slot": label, "prediction_kw": round(pred_kw, 4)})
        except Exception as e:
            logger.error(f"Помилка інференсу моделі '{label}': {e}")

    if not predictions:
        raise HTTPException(
            status_code=500,
            detail="Внутрішня помилка розрахунку прогнозу: жодна модель з реєстру не повернула результат."
        )

    # Усереднення прогнозів мультимасштабного ансамблю
    ensemble_pred_kw = float(np.mean(predictions))
    
    # Час прогнозу — наступна година після останнього запису
    latest_time = records[-1].timestamp
    forecast_time = latest_time + timedelta(hours=1)
    
    logger.info(
        f"Мультимасштабний ансамблевий прогноз на {forecast_time} "
        f"(моделей: {len(predictions)}, слоти: {[d['slot'] for d in model_details]}): "
        f"{ensemble_pred_kw:.4f} кВт"
    )
    
    return {
        "forecast_timestamp": forecast_time.isoformat(),
        "input_last_timestamp": latest_time.isoformat(),
        "predicted_active_power_kw": round(ensemble_pred_kw, 4),
        "ensemble_details": model_details
    }


@router.post("/retrain", response_model=RetrainResponse, status_code=status.HTTP_200_OK)
async def retrain_model_endpoint(
    request: RetrainRequest = RetrainRequest(),
    db: AsyncSession = Depends(get_db)
):
    """
    Ендпоінт для запуску мультимасштабного донавчання (incremental fine-tuning)
    базової моделі CNN-LSTM та збереження результату у відповідний слот ансамблю.

    Слоти:
      - 'year':  Донавчання на ~8760 год → сезонні тренди
      - 'month': Донавчання на ~720 год → актуальні умови
    """
    logger.info(f"Отримано запит на донавчання моделі (слот: '{request.slot}')...")
    try:
        results = await retrain_on_recent_data(
            db=db,
            slot=request.slot,
            limit_hours=request.limit_hours,
            epochs=request.epochs,
            learning_rate=request.learning_rate,
            batch_size=request.batch_size
        )
        return results
    except ValueError as e:
        logger.warning(f"Неможливо виконати донавчання через брак даних: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Помилка під час донавчання моделі: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутрішня помилка під час донавчання: {e}"
        )
