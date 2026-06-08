import argparse
import logging
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tensorflow as tf
from app.core.config import settings
from app.core.data.dataset import load_and_split_data, CustomMinMaxScaler, TimeSeriesWindowGenerator
from app.core.models.cnn_lstm import build_cnn_lstm_model
from app.core.models.metrics import evaluate_forecast

logger = logging.getLogger(__name__)

# Списки колонок для моделювання
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


def train_pipeline(epochs: int, batch_size: int, patience: int) -> None:
    """Запускає повний конвеєр навчання та оцінки моделі CNN-LSTM."""
    logger.info("Запуск конвеєра навчання моделі...")
    
    csv_path = os.path.join(settings.RAW_DATA_DIR, "pv_weather_data.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"Не знайдено файл даних {csv_path}. Будь ласка, спочатку запустіть scripts/collect_data.py"
        )
        
    # 1. Розподіл даних хронологічно
    train_df, val_df, test_df = load_and_split_data(csv_path)
    
    # 2. Масштабування
    scaler = CustomMinMaxScaler()
    scaler.fit(train_df)
    
    train_scaled = scaler.transform(train_df)
    val_scaled = scaler.transform(val_df)
    test_scaled = scaler.transform(test_df)
    
    # 3. Генерація вікон [Samples, Lookback, Features]
    lookback = 24
    horizon = 1
    generator = TimeSeriesWindowGenerator(
        lookback=lookback,
        horizon=horizon,
        target_column=TARGET_COLUMN,
        feature_columns=FEATURE_COLUMNS
    )
    
    X_train, y_train = generator.generate_windows(train_scaled)
    X_val, y_val = generator.generate_windows(val_scaled)
    X_test, y_test = generator.generate_windows(test_scaled)
    
    logger.info(f"Розмірності навчальних вибірок: X={X_train.shape}, y={y_train.shape}")
    logger.info(f"Розмірності валідаційних вибірок: X={X_val.shape}, y={y_val.shape}")
    logger.info(f"Розмірності тестових вибірок: X={X_test.shape}, y={y_test.shape}")
    
    # 4. Побудова моделі
    input_shape = (lookback, len(FEATURE_COLUMNS))
    model = build_cnn_lstm_model(input_shape=input_shape)
    
    # 5. Колбеки для навчання
    model_save_path = os.path.join("app", "core", "models", "saved_model.keras")
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
    
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=patience,
            restore_best_weights=True,
            verbose=1
        ),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=model_save_path,
            monitor="val_loss",
            save_best_only=True,
            verbose=1
        )
    ]
    
    # 6. Навчання
    logger.info(f"Початок навчання моделі: epochs={epochs}, batch_size={batch_size}...")
    history = model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        verbose=1
    )
    
    logger.info("Навчання завершено успішно.")
    
    # 7. Збереження графіку кривих втрат
    plt.figure(figsize=(10, 5))
    plt.plot(history.history["loss"], label="Train Loss (MSE)")
    plt.plot(history.history["val_loss"], label="Validation Loss (MSE)")
    plt.title("Крива втрат моделі CNN-LSTM")
    plt.xlabel("Епоха")
    plt.ylabel("Втрати (MSE)")
    plt.legend()
    plt.grid(True)
    
    loss_plot_path = os.path.join(settings.PLOTS_DIR, "training_loss.png")
    plt.savefig(loss_plot_path)
    plt.close()
    logger.info(f"Графік кривих втрат збережено у: {loss_plot_path}")
    
    # 8. Завантаження найкращої збереженої моделі та інференс на тест-вибірці
    if os.path.exists(model_save_path):
        model = tf.keras.models.load_model(model_save_path)
        
    y_pred_scaled = model.predict(X_test, verbose=0)
    
    # Денормалізація виходу назад у фізичні одиниці (кВт)
    # Зверніть увагу: y_test та y_pred_scaled мають розмірність [samples, 1]
    y_test_kw = scaler.inverse_transform_column(y_test.flatten(), TARGET_COLUMN)
    y_pred_kw = scaler.inverse_transform_column(y_pred_scaled.flatten(), TARGET_COLUMN)
    
    # Потужність не може бути від'ємною
    y_pred_kw = np.clip(y_pred_kw, 0.0, None)
    
    # 9. Оцінка точності
    metrics = evaluate_forecast(y_test_kw, y_pred_kw, threshold=0.2)
    logger.info("================ Результати оцінки точності на тестовій вибірці ================")
    logger.info(f"MAE  (Середня абсолютна помилка):  {metrics['mae']:.4f} кВт")
    logger.info(f"RMSE (Середньоквадратична помилка): {metrics['rmse']:.4f} кВт")
    logger.info(f"MAPE (Середня відсоткова помилка):  {metrics['mape']:.4f} %  (для фактичних значень >= 0.2 кВт)")
    logger.info("================================================================================")
    
    # 10. Побудова порівняльного графіку Факт vs Прогноз
    # Для візуалізації виберемо фрагмент тестової вибірки (наприклад, 1 тиждень = 168 годин)
    plot_len = min(168, len(y_test_kw))
    
    plt.figure(figsize=(15, 6))
    plt.plot(y_test_kw[:plot_len], label="Фактична генерація (кВт)", color="blue", linewidth=2)
    plt.plot(y_pred_kw[:plot_len], label="Прогнозована генерація (кВт)", color="orange", linestyle="--", linewidth=2)
    plt.title(f"Порівняння фактичної та прогнозованої генерації ФЕС на тестовому періоді ({plot_len} годин)")
    plt.xlabel("Час (години)")
    plt.ylabel("Активна потужність (кВт)")
    plt.legend()
    plt.grid(True)
    
    comparison_plot_path = os.path.join(settings.PLOTS_DIR, "actual_vs_predicted.png")
    plt.savefig(comparison_plot_path)
    plt.close()
    logger.info(f"Порівняльний графік факт/прогноз збережено у: {comparison_plot_path}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="Скрипт для навчання нейромережі CNN-LSTM")
    parser.add_argument("--epochs", type=int, default=50, help="Кількість епох навчання")
    parser.add_argument("--batch_size", type=int, default=32, help="Розмір батчу для навчання")
    parser.add_argument("--patience", type=int, default=5, help="Кількість епох очікування EarlyStopping")
    
    args = parser.parse_args()
    
    train_pipeline(
        epochs=args.epochs,
        batch_size=args.batch_size,
        patience=args.patience
    )
