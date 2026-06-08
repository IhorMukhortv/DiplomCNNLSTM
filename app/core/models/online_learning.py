import asyncio
import logging
import tensorflow as tf
import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db.models import PVTelemetry
from app.core.data.dataset import global_scaler, TimeSeriesWindowGenerator
from app.infrastructure.storage.model_registry import model_registry, ModelRegistry

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = [
    "temperature_2m",
    "relative_humidity_2m",
    "cloud_cover",
    "direct_normal_irradiance",
    "diffuse_horizontal_irradiance",
    "global_horizontal_irradiance",
    "active_power_kw"
]
TARGET_COLUMN = "active_power_kw"

# Параметри горизонтів за замовчуванням (в годинах)
HORIZON_HOURS = {
    ModelRegistry.SLOT_YEAR: 8760,   # ~1 рік
    ModelRegistry.SLOT_MONTH: 720,   # ~1 місяць
}


async def retrain_on_recent_data(
    db: AsyncSession,
    slot: str = ModelRegistry.SLOT_MONTH,
    limit_hours: int = None,
    epochs: int = 5,
    learning_rate: float = 0.0001,
    batch_size: int = 16
) -> dict:
    """
    Завантажує останні N записів телеметрії з бази даних, формує ковзні вікна,
    виконує дрібнокрокове донавчання (Fine-Tuning) базової моделі та зберігає
    результат у відповідний слот мультимасштабного ансамблю.

    Мультимасштабний підхід (аналогія з EMA у трейдингу):
      - slot='year':  Донавчання на ~8760 годин → сезонні патерни (EMA-50)
      - slot='month': Донавчання на ~720 годин → актуальні умови (EMA-12)

    Параметри:
        db: Асинхронна сесія бази даних.
        slot: Ім'я слоту реєстру ('year' або 'month').
        limit_hours: Кількість годин для вибірки (за замовчуванням — з HORIZON_HOURS).
        epochs: Кількість епох навчання.
        learning_rate: Знижена швидкість навчання для запобігання катастрофічному забуванню.
        batch_size: Розмір батчу.
    """
    if slot not in [ModelRegistry.SLOT_YEAR, ModelRegistry.SLOT_MONTH]:
        raise ValueError(f"Невідомий слот: {slot}. Допустимі: 'year', 'month'.")

    # Визначаємо горизонт за замовчуванням, якщо не задано
    if limit_hours is None:
        limit_hours = HORIZON_HOURS[slot]

    logger.info(
        f"Запуск донавчання: slot='{slot}', limit_hours={limit_hours}, "
        f"epochs={epochs}, lr={learning_rate}"
    )

    # 1. Завантажуємо записи телеметрії з бази
    stmt = select(PVTelemetry).order_by(PVTelemetry.timestamp.desc()).limit(limit_hours)
    result = await db.execute(stmt)
    records = result.scalars().all()

    # Для вікон lookback=24 та horizon=1 необхідно щонайменше 25 послідовних записів
    required_records = 25
    if len(records) < required_records:
        logger.warning(f"Недостатньо записів для донавчання: знайдено {len(records)} з {required_records} необхідних.")
        raise ValueError(
            f"Недостатньо даних для донавчання моделі. Потрібно мінімум {required_records} "
            f"послідовних записів, знайдено лише {len(records)}."
        )

    # 2. Сортуємо в хронологічному порядку (зростання часу)
    records = list(reversed(records))

    # 3. Перетворюємо у DataFrame
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

    # 4. Масштабування
    df_scaled = global_scaler.transform(df)

    # 5. Генерація вікон
    generator = TimeSeriesWindowGenerator(
        lookback=24,
        horizon=1,
        target_column=TARGET_COLUMN,
        feature_columns=FEATURE_COLUMNS
    )
    X, y = generator.generate_windows(df_scaled)

    # 6. Завжди донавчаємо КОПІЮ базової моделі (не кумулятивно!)
    #    Це запобігає дрейфу та катастрофічному забуванню.
    models = model_registry.get_models()
    base_model = models[0]  # Перша модель завжди base

    # Клонуємо базову модель та її ваги
    model = tf.keras.models.clone_model(base_model)
    model.set_weights(base_model.get_weights())

    # Компілюємо з новим learning rate
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="mse",
        metrics=["mae"]
    )

    # 7. Оцінка помилки до навчання
    loss_before = float(model.evaluate(X, y, verbose=0)[0])
    logger.info(f"MSE до донавчання (слот '{slot}'): {loss_before:.6f}")

    # 8. Донавчання у фоновому потоці, щоб не блокувати event loop
    def fit_model():
        fit_history = model.fit(
            X,
            y,
            epochs=epochs,
            batch_size=batch_size,
            verbose=0
        )
        return fit_history.history["loss"]

    loss_history = await asyncio.to_thread(fit_model)

    # 9. Оцінка помилки після навчання
    loss_after = float(model.evaluate(X, y, verbose=0)[0])
    logger.info(f"MSE після донавчання (слот '{slot}'): {loss_after:.6f}")

    # 10. Збереження у відповідний слот реєстру
    model_registry.save_slot_model(model, slot)

    return {
        "status": "success",
        "slot": slot,
        "records_used": len(records),
        "windows_generated": len(X),
        "loss_before": round(loss_before, 6),
        "loss_after": round(loss_after, 6),
        "loss_history": [round(float(l), 6) for l in loss_history]
    }
