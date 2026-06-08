import numpy as np
import pandas as pd
import pytest
from app.core.data.dataset import CustomMinMaxScaler, load_and_split_data, TimeSeriesWindowGenerator
from app.core.models.cnn_lstm import build_cnn_lstm_model
from app.core.models.metrics import calculate_mae, calculate_rmse, calculate_mape, evaluate_forecast
from app.core.exceptions import DataPreprocessingError


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
