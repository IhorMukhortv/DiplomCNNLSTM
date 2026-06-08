import os
import logging
import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib.pyplot as plt
from app.core.config import settings
from app.core.data.dataset import load_and_split_data, global_scaler, TimeSeriesWindowGenerator
from app.core.models.metrics import evaluate_forecast

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


def clone_keras_model(model: tf.keras.Model) -> tf.keras.Model:
    """Створює глибоку копію моделі Keras разом із її вагами."""
    cloned = tf.keras.models.clone_model(model)
    cloned.set_weights(model.get_weights())
    return cloned


def finetune_model(
    base_model: tf.keras.Model,
    X_train: np.ndarray,
    y_train: np.ndarray,
    epochs: int = 5,
    learning_rate: float = 0.0001,
    batch_size: int = 16
) -> tf.keras.Model:
    """
    Клонує базову модель та донавчає на переданих даних.
    Завжди починає з оригінальних ваг (без кумулятивного дрейфу).
    """
    model = clone_keras_model(base_model)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="mse",
        metrics=["mae"]
    )
    model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size, verbose=0)
    return model


def run_online_simulation(simulation_days: int = 7, retrain_interval_hours: int = 24):
    """
    Симулює процес мультимасштабного онлайн-навчання та ансамблювання.

    Порівнює 4 стратегії:
      1. Базова модель (без донавчання) — EMA-200 аналог.
      2. Адаптивна модель (одиночне Fine-Tuning на ~168 год, без ансамблю).
      3. Старий ансамбль (Базова + до 3 послідовних версій донавчання).
      4. Мультимасштабний ансамбль (Base + Year + Month) — EMA-аналогія.

    Мультимасштабний підхід:
      - Base:  Базова модель (навчена на всьому train set) → глобальні патерни
      - Year:  Клон базової, донавчений на останніх ~8760 год → сезонні тренди
      - Month: Клон базової, донавчений на останніх ~720 год → актуальні умови
    """
    logger.info("=" * 80)
    logger.info("ЗАПУСК СИМУЛЯЦІЇ МУЛЬТИМАСШТАБНОГО АНСАМБЛЮ (EMA-СТРАТЕГІЯ)")
    logger.info("=" * 80)

    csv_path = os.path.join(settings.RAW_DATA_DIR, "pv_weather_data.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Файл даних {csv_path} не знайдено.")

    # 1. Завантажуємо дані
    train_df, val_df, test_df = load_and_split_data(csv_path)

    # 2. Завантажуємо базову модель
    model_path = os.path.join("app", "core", "models", "saved_model.keras")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Навчену модель не знайдено за шляхом {model_path}.")

    base_model = tf.keras.models.load_model(model_path)
    online_model = tf.keras.models.load_model(model_path)

    # 3. Підготовка повних часових рядів для мультимасштабного донавчання
    # Для "річної" моделі — використовуємо train+val як "історичні" дані
    # Для "місячної" — останні 720 годин train+val
    full_history_df = pd.concat([train_df, val_df], ignore_index=True)

    logger.info(f"Повна історія: {len(full_history_df)} записів")
    logger.info(f"Тестова вибірка: {len(test_df)} записів")

    # 4. Налаштовуємо параметри симуляції
    lookback = 24
    simulation_hours = simulation_days * 24

    # Вибираємо фрагмент із тестової вибірки для симуляції
    start_idx = 0
    end_idx = start_idx + lookback + simulation_hours
    sim_df = test_df.iloc[start_idx:end_idx].copy().reset_index(drop=True)

    # Генератор вікон
    generator = TimeSeriesWindowGenerator(
        lookback=lookback,
        horizon=1,
        target_column=TARGET_COLUMN,
        feature_columns=FEATURE_COLUMNS
    )

    # 5. Готуємо мультимасштабні моделі перед початком симуляції
    logger.info("-" * 40)
    logger.info("Підготовка мультимасштабних моделей...")

    # Year model: донавчити на останніх 8760 год із повної історії (або скільки є)
    year_hours = min(8760, len(full_history_df))
    year_data = full_history_df.iloc[-year_hours:].copy()
    year_scaled = global_scaler.transform(year_data)
    X_year, y_year = generator.generate_windows(year_scaled)

    year_model = finetune_model(base_model, X_year, y_year, epochs=5, learning_rate=0.0001)
    logger.info(f"Year-модель: донавчена на {year_hours} год ({len(X_year)} вікон)")

    # Month model: донавчити на останніх 720 год із повної історії (або скільки є)
    month_hours = min(720, len(full_history_df))
    month_data = full_history_df.iloc[-month_hours:].copy()
    month_scaled = global_scaler.transform(month_data)
    X_month, y_month = generator.generate_windows(month_scaled)

    month_model = finetune_model(base_model, X_month, y_month, epochs=5, learning_rate=0.0001)
    logger.info(f"Month-модель: донавчена на {month_hours} год ({len(X_month)} вікон)")

    logger.info("-" * 40)

    # Результати
    actual_power = []
    base_predictions = []
    online_predictions = []
    old_ensemble_predictions = []
    multiscale_predictions = []

    # Старий ансамбль: до 3 послідовних версій
    old_ensemble_history = []

    logger.info(f"Довжина періоду симуляції: {simulation_hours} годин")

    # 6. Цикл симуляції по годинах
    for t in range(lookback, len(sim_df)):
        # Поточне ковзне вікно (останні 24 години)
        window_df = sim_df.iloc[t - lookback : t][FEATURE_COLUMNS].copy()
        window_scaled = global_scaler.transform(window_df)
        X_input = window_scaled.values
        X_input = np.expand_dims(X_input, axis=0).astype(np.float32)  # [1, 24, 7]

        # --- Прогноз 1: Базова модель ---
        base_pred_scaled = base_model.predict(X_input, verbose=0)[0, 0]
        base_pred = global_scaler.inverse_transform_column(np.array([base_pred_scaled]), TARGET_COLUMN)[0]
        base_pred_val = max(0.0, float(base_pred))

        # --- Прогноз 2: Одиночна адаптивна модель (кумулятивне донавчання) ---
        online_pred_scaled = online_model.predict(X_input, verbose=0)[0, 0]
        online_pred = global_scaler.inverse_transform_column(np.array([online_pred_scaled]), TARGET_COLUMN)[0]
        online_pred_val = max(0.0, float(online_pred))

        # --- Прогноз 3: Старий ансамбль (Base + до 3 послідовних версій) ---
        old_ens_preds = [base_pred_val]
        for m in old_ensemble_history:
            m_pred_scaled = m.predict(X_input, verbose=0)[0, 0]
            m_pred = global_scaler.inverse_transform_column(np.array([m_pred_scaled]), TARGET_COLUMN)[0]
            old_ens_preds.append(max(0.0, float(m_pred)))
        old_ensemble_pred_val = float(np.mean(old_ens_preds))

        # --- Прогноз 4: Мультимасштабний ансамбль (Base + Year + Month) ---
        multiscale_preds = [base_pred_val]

        # Year
        year_pred_scaled = year_model.predict(X_input, verbose=0)[0, 0]
        year_pred = global_scaler.inverse_transform_column(np.array([year_pred_scaled]), TARGET_COLUMN)[0]
        multiscale_preds.append(max(0.0, float(year_pred)))

        # Month
        month_pred_scaled = month_model.predict(X_input, verbose=0)[0, 0]
        month_pred = global_scaler.inverse_transform_column(np.array([month_pred_scaled]), TARGET_COLUMN)[0]
        multiscale_preds.append(max(0.0, float(month_pred)))

        multiscale_pred_val = float(np.mean(multiscale_preds))

        # Зберігаємо результати
        base_predictions.append(base_pred_val)
        online_predictions.append(online_pred_val)
        old_ensemble_predictions.append(old_ensemble_pred_val)
        multiscale_predictions.append(multiscale_pred_val)
        actual_power.append(float(sim_df.iloc[t][TARGET_COLUMN]))

        # Поточний крок у симуляції
        sim_step = t - lookback

        # Донавчаємо онлайн-модель кожні `retrain_interval_hours` годин
        if sim_step > 0 and sim_step % retrain_interval_hours == 0:
            logger.info(f"[Година {sim_step}] Виконується періодичне донавчання...")

            history_start = max(0, t - 168)
            history_df = sim_df.iloc[history_start:t][FEATURE_COLUMNS].copy()
            history_scaled = global_scaler.transform(history_df)
            X_train, y_train = generator.generate_windows(history_scaled)

            if len(X_train) > 0:
                # Донавчаємо онлайн-модель (кумулятивно)
                online_model.compile(
                    optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),
                    loss="mse",
                    metrics=["mae"]
                )
                online_model.fit(X_train, y_train, epochs=5, batch_size=16, verbose=0)

                # Копія для старого ансамблю
                new_version = clone_keras_model(online_model)
                old_ensemble_history.insert(0, new_version)
                if len(old_ensemble_history) > 3:
                    old_ensemble_history.pop()

                # Оновлюємо month-модель мультимасштабного ансамблю
                # (перенавчаємо від базової на розширеному місячному вікні)
                extended_month_hours = min(720, len(full_history_df) + t)
                # Збираємо повну доступну історію + дані симуляції до поточного моменту
                available_sim_data = sim_df.iloc[:t][FEATURE_COLUMNS].copy()
                combined_for_month = pd.concat(
                    [full_history_df[FEATURE_COLUMNS].iloc[-720:], available_sim_data],
                    ignore_index=True
                ).iloc[-720:]  # Останні 720 годин

                month_scaled_new = global_scaler.transform(combined_for_month)
                X_month_new, y_month_new = generator.generate_windows(month_scaled_new)

                if len(X_month_new) > 0:
                    month_model = finetune_model(
                        base_model, X_month_new, y_month_new,
                        epochs=5, learning_rate=0.0001
                    )
                    logger.info(
                        f"  Month-модель оновлена на {len(X_month_new)} вікнах "
                        f"(останні {len(combined_for_month)} год)"
                    )

                logger.info(f"  Старий ансамбль: {len(old_ensemble_history)} версій")

    # 7. Оцінка метрик якості
    actual_power = np.array(actual_power)
    base_predictions = np.array(base_predictions)
    online_predictions = np.array(online_predictions)
    old_ensemble_predictions = np.array(old_ensemble_predictions)
    multiscale_predictions = np.array(multiscale_predictions)

    base_metrics = evaluate_forecast(actual_power, base_predictions, threshold=0.2)
    online_metrics = evaluate_forecast(actual_power, online_predictions, threshold=0.2)
    old_ens_metrics = evaluate_forecast(actual_power, old_ensemble_predictions, threshold=0.2)
    multiscale_metrics = evaluate_forecast(actual_power, multiscale_predictions, threshold=0.2)

    logger.info("=" * 100)
    logger.info("РЕЗУЛЬТАТИ ПОРІВНЯННЯ СТРАТЕГІЙ АНСАМБЛЮВАННЯ (ПЕРІОД: 1 ТИЖДЕНЬ)")
    logger.info("-" * 100)
    logger.info(
        f"{'Метрика':<10} | {'Базова модель':<18} | {'Адаптивна (FT)':<18} | "
        f"{'Старий ансамбль':<18} | {'Мультимасштабний':<18}"
    )
    logger.info("-" * 100)
    logger.info(
        f"{'MAE':<10} | {base_metrics['mae']:.4f} кВт       | {online_metrics['mae']:.4f} кВт       | "
        f"{old_ens_metrics['mae']:.4f} кВт       | {multiscale_metrics['mae']:.4f} кВт"
    )
    logger.info(
        f"{'RMSE':<10} | {base_metrics['rmse']:.4f} кВт      | {online_metrics['rmse']:.4f} кВт      | "
        f"{old_ens_metrics['rmse']:.4f} кВт      | {multiscale_metrics['rmse']:.4f} кВт"
    )
    logger.info(
        f"{'MAPE':<10} | {base_metrics['mape']:.4f} %        | {online_metrics['mape']:.4f} %        | "
        f"{old_ens_metrics['mape']:.4f} %        | {multiscale_metrics['mape']:.4f} %"
    )
    logger.info("=" * 100)

    # Покращення відносно базової
    base_mape = base_metrics['mape']
    ms_mape = multiscale_metrics['mape']
    improvement = ((base_mape - ms_mape) / base_mape) * 100
    logger.info(
        f"Покращення MAPE мультимасштабного ансамблю відносно базової: "
        f"{improvement:+.2f}%"
    )

    # 8. Побудова порівняльного графіку
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), gridspec_kw={'height_ratios': [3, 1]})

    # Верхній графік — прогнози
    ax1 = axes[0]
    hours_to_plot = min(168, len(actual_power))
    time_axis = np.arange(hours_to_plot)

    ax1.plot(time_axis, actual_power[:hours_to_plot],
             label="Фактична генерація (кВт)", color="blue", linewidth=2)
    ax1.plot(time_axis, base_predictions[:hours_to_plot],
             label=f"Базова (MAPE={base_metrics['mape']:.2f}%)",
             color="red", linestyle="--", linewidth=1.2, alpha=0.7)
    ax1.plot(time_axis, old_ensemble_predictions[:hours_to_plot],
             label=f"Старий ансамбль (MAPE={old_ens_metrics['mape']:.2f}%)",
             color="orange", linestyle=":", linewidth=1.2, alpha=0.7)
    ax1.plot(time_axis, multiscale_predictions[:hours_to_plot],
             label=f"Мультимасштабний ансамбль (MAPE={multiscale_metrics['mape']:.2f}%)",
             color="green", linestyle="-", linewidth=2)

    ax1.set_title("Порівняння стратегій прогнозування: Базова vs Мультимасштабний ансамбль (EMA)", fontsize=13)
    ax1.set_xlabel("Час (години)")
    ax1.set_ylabel("Потужність (кВт)")
    ax1.legend(loc="upper right", fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Нижній графік — абсолютна похибка
    ax2 = axes[1]
    base_errors = np.abs(actual_power[:hours_to_plot] - base_predictions[:hours_to_plot])
    ms_errors = np.abs(actual_power[:hours_to_plot] - multiscale_predictions[:hours_to_plot])

    ax2.fill_between(time_axis, base_errors, alpha=0.3, color="red", label="Похибка базової")
    ax2.fill_between(time_axis, ms_errors, alpha=0.3, color="green", label="Похибка мультимасштабного")
    ax2.set_xlabel("Час (години)")
    ax2.set_ylabel("Абсолютна похибка (кВт)")
    ax2.legend(loc="upper right", fontsize=9)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    plot_path = os.path.join(settings.PLOTS_DIR, "online_learning_comparison.png")
    plt.savefig(plot_path, dpi=150)
    plt.close()
    logger.info(f"Порівняльний графік збережено у: {plot_path}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    run_online_simulation()
