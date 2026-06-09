import os
import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from app.core.data.dataset import CustomMinMaxScaler, load_and_split_data, TimeSeriesWindowGenerator
from app.core.models.cnn_lstm import build_cnn_lstm_model
from app.core.models.metrics import calculate_mae, calculate_rmse, calculate_mape, evaluate_forecast
from app.core.exceptions import DataPreprocessingError
from app.infrastructure.storage.model_registry import ModelRegistry
from app.core.models.online_learning import retrain_on_recent_data
from app.infrastructure.db.models import PVTelemetry




def test_custom_min_max_scaler():
    """Тестує роботу CustomMinMaxScaler."""
    data = pd.DataFrame({
        "A": [10.0, 20.0, 30.0],
        "B": [1.0, 2.0, 3.0]
    })
    
    scaler = CustomMinMaxScaler()
    scaler.fit(data)
    
    # Перевірка мінімумів та максимумів
    assert scaler.min_values["A"] == 10.0
    assert scaler.min_values["B"] == 1.0
    assert scaler.max_values["A"] == 30.0
    assert scaler.max_values["B"] == 3.0
    
    # Перевірка трансформації
    scaled = scaler.transform(data)
    assert scaled.loc[0, "A"] == 0.0
    assert scaled.loc[1, "A"] == 0.5
    assert scaled.loc[2, "A"] == 1.0
    assert scaled.loc[0, "B"] == 0.0
    assert scaled.loc[2, "B"] == 1.0
    
    # Перевірка зворотного перетворення
    inverse_col = scaler.inverse_transform_column(np.array([0.0, 0.5, 1.0]), "A")
    np.testing.assert_allclose(inverse_col, [10.0, 20.0, 30.0])


def test_load_and_split_data(tmp_path):
    """Тестує хронологічне розбиття датасету."""
    # Створюємо тимчасовий CSV-файл
    df = pd.DataFrame({
        "timestamp": pd.date_range("2017-03-01", periods=10, freq="h"),
        "active_power_kw": np.arange(10, dtype=float),
        "temp": np.arange(10, 20, dtype=float)
    })
    csv_file = tmp_path / "temp_data.csv"
    df.to_csv(csv_file, index=False)
    
    train_df, val_df, test_df = load_and_split_data(
        str(csv_file),
        train_ratio=0.6,
        val_ratio=0.2,
        test_ratio=0.2
    )
    
    assert len(train_df) == 6
    assert len(val_df) == 2
    assert len(test_df) == 2
    
    # Перевірка хронологічного порядку та відсутності timestamp
    assert "timestamp" not in train_df.columns
    assert list(train_df["active_power_kw"]) == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    assert list(val_df["active_power_kw"]) == [6.0, 7.0]
    assert list(test_df["active_power_kw"]) == [8.0, 9.0]


def test_window_generator():
    """Тестує формування вікон зсуву (lookback & horizon)."""
    df = pd.DataFrame({
        "active_power_kw": [10.0, 11.0, 12.0, 13.0, 14.0],
        "temp": [1.0, 2.0, 3.0, 4.0, 5.0]
    })
    
    # lookback=2, horizon=1
    generator = TimeSeriesWindowGenerator(
        lookback=2,
        horizon=1,
        target_column="active_power_kw",
        feature_columns=["active_power_kw", "temp"]
    )
    
    X, y = generator.generate_windows(df)
    
    # Кількість зразків: 5 - 2 - 1 + 1 = 3
    assert X.shape == (3, 2, 2)
    assert y.shape == (3, 1)
    
    # Перевірка першого вікна
    # X[0] = [[10.0, 1.0], [11.0, 2.0]]
    np.testing.assert_allclose(X[0], [[10.0, 1.0], [11.0, 2.0]])
    # y[0] = [12.0]
    np.testing.assert_allclose(y[0], [12.0])
    
    # Перевірка останнього вікна
    np.testing.assert_allclose(X[-1], [[12.0, 3.0], [13.0, 4.0]])
    np.testing.assert_allclose(y[-1], [14.0])


def test_cnn_lstm_model_shapes():
    """Тестує правильність розмірностей побудованої Keras моделі."""
    lookback = 24
    num_features = 7
    model = build_cnn_lstm_model(input_shape=(lookback, num_features))
    
    # Перевірка вхідної розмірності
    assert model.input_shape == (None, lookback, num_features)
    # Перевірка вихідної розмірності
    assert model.output_shape == (None, 1)


def test_metrics_calculation():
    """Тестує математичну точність метрик якості прогнозування."""
    y_true = np.array([2.0, 4.0, 6.0])
    y_pred = np.array([2.2, 3.8, 6.6])
    
    # MAE = (|2.0-2.2| + |4.0-3.8| + |6.0-6.6|) / 3 = (0.2 + 0.2 + 0.6) / 3 = 0.3333
    mae = calculate_mae(y_true, y_pred)
    assert pytest.approx(mae, abs=1e-4) == 0.3333
    
    # RMSE = sqrt(((0.2)^2 + (0.2)^2 + (0.6)^2) / 3) = sqrt((0.04 + 0.04 + 0.36) / 3) = sqrt(0.44 / 3) = 0.3830
    rmse = calculate_rmse(y_true, y_pred)
    assert pytest.approx(rmse, abs=1e-4) == 0.3830
    
    # MAPE = ( |0.2/2.0| + |0.2/4.0| + |0.6/6.0| ) / 3 * 100% = (0.1 + 0.05 + 0.1) / 3 * 100% = 8.3333%
    mape = calculate_mape(y_true, y_pred, threshold=0.1)
    assert pytest.approx(mape, abs=1e-4) == 8.3333
    
    # Тест оцінки
    metrics = evaluate_forecast(y_true, y_pred, threshold=0.1)
    assert "mae" in metrics
    assert "rmse" in metrics
    assert "mape" in metrics


def test_model_registry(tmp_path):
    """Тестує працездатність реєстру моделей."""
    model_file = tmp_path / "test_model.keras"
    # Створюємо реєстр моделей з тестовим шляхом
    registry = ModelRegistry(model_path=str(model_file))
    
    # 1. Перше завантаження (створення нової моделі, оскільки файлу немає)
    model = registry.get_model()
    assert model is not None
    
    # 2. Збереження моделі
    registry.save_model(model)
    assert model_file.exists()
    
    # 3. Перезавантаження моделі
    reloaded_model = registry.reload_model()
    assert reloaded_model is not None


@pytest.mark.anyio
async def test_retrain_on_recent_data_insufficient():
    """Тестує помилку при спробі донавчання на недостатній кількості даних."""
    mock_db = AsyncMock()
    mock_execute_result = MagicMock()
    # Повертаємо менше 25 записів (наприклад, 10)
    mock_execute_result.scalars.return_value.all.return_value = [
        MagicMock() for _ in range(10)
    ]
    mock_db.execute.return_value = mock_execute_result
    
    with pytest.raises(ValueError) as excinfo:
        await retrain_on_recent_data(mock_db, limit_hours=10)
    
    assert "Недостатньо даних" in str(excinfo.value)


@pytest.mark.anyio
async def test_retrain_on_recent_data_success(monkeypatch, tmp_path):
    """Тестує успішний запуск донавчання при достатній кількості даних."""
    mock_db = AsyncMock()
    mock_execute_result = MagicMock()
    
    # Тимчасовий шлях для моделі у глобальному реєстрі, щоб не пошкодити основну
    temp_model_path = tmp_path / "temp_saved_model.keras"
    from app.infrastructure.storage.model_registry import model_registry
    monkeypatch.setattr(model_registry, "model_path", str(temp_model_path))
    # Оновлюємо шляхи слотів мультимасштабного реєстру
    monkeypatch.setattr(model_registry, "_slot_paths", {
        "base": str(temp_model_path),
        "year": str(tmp_path / "saved_model_year.keras"),
        "month": str(tmp_path / "saved_model_month.keras"),
    })
    # Скидаємо модель в реєстрі, щоб вона ініціалізувалась наново за новим шляхом
    monkeypatch.setattr(model_registry, "_models", {"base": None, "year": None, "month": None})
    monkeypatch.setattr(model_registry, "_model", None)

    # Створюємо 30 фейкових записів телеметрії
    records = [
        PVTelemetry(
            timestamp=datetime(2026, 6, 8, 0, 0, 0) + timedelta(hours=i),
            temperature_2m=25.0,
            relative_humidity_2m=50.0,
            cloud_cover=20.0,
            direct_normal_irradiance=700.0,
            diffuse_horizontal_irradiance=100.0,
            global_horizontal_irradiance=800.0,
            active_power_kw=15.0
        )
        for i in range(30)
    ]
    
    mock_execute_result.scalars.return_value.all.return_value = records
    mock_db.execute.return_value = mock_execute_result
    
    # Викликаємо функцію донавчання на 2 епохи
    results = await retrain_on_recent_data(
        db=mock_db,
        limit_hours=30,
        epochs=2,
        learning_rate=0.0001,
        batch_size=10
    )
    
    assert results["status"] == "success"
    assert results["records_used"] == 30
    assert results["windows_generated"] == 30 - 24 - 1 + 1 # 6
    assert results["loss_before"] is not None
    assert results["loss_after"] is not None
    assert len(results["loss_history"]) == 2
    assert results["slot"] == "month"
    assert os.path.exists(model_registry._slot_paths["month"])


def test_model_registry_load_model_file_exception(tmp_path, monkeypatch):
    """Тестує обробку виключення при завантаженні файлу моделі."""
    from app.infrastructure.storage.model_registry import ModelRegistry
    import tensorflow as tf

    registry = ModelRegistry(model_path=str(tmp_path / "dummy.keras"))

    # Мокаємо tf.keras.models.load_model щоб він кидав Exception
    def mock_load_model(*args, **kwargs):
        raise Exception("Mocked load error")

    monkeypatch.setattr(tf.keras.models, "load_model", mock_load_model)

    # Мокаємо logger.error
    mock_logger = MagicMock()
    monkeypatch.setattr("app.infrastructure.storage.model_registry.logger", mock_logger)

    # Викликаємо приватний метод
    result = registry._load_model_file("fake_path.keras", "test_label")

    # Перевіряємо, що повернувся None
    assert result is None

    # Перевіряємо, що логер був викликаний з правильною помилкою
    mock_logger.error.assert_called_once()
    log_msg = mock_logger.error.call_args[0][0]
    assert "Помилка при завантаженні моделі" in log_msg or "Не вдалося завантажити" in log_msg
    assert "test_label" in log_msg
    assert "fake_path.keras" in log_msg
    assert "Mocked load error" in log_msg
