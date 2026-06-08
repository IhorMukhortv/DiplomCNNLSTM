---
name: cnn-lstm-forecasting
description: Розробка, навчання та прогнозування за допомогою гібридної нейромережі CNN-LSTM для короткострокового прогнозування генерації ФЕС.
---

# Гібридне прогнозування CNN-LSTM

Ця навичка містить інструкції, архітектурні шаблони та готові приклади коду для побудови, передобробки даних та навчання гібридної моделі CNN-LSTM для прогнозування часових рядів генерації сонячних електростанцій.

## Коли використовувати цю навичку

- Створення архітектури нейронної мережі CNN-LSTM (Conv1D + LSTM).
- Підготовка даних часових рядів за методом ковзного вікна (sliding window).
- Навчання моделі, збереження ваг та оцінка якості за метриками MAE, RMSE, MAPE.
- Запуск інференсу (прогнозування) на основі нових метеорологічних даних та історії генерації.

## Архітектура моделі CNN-LSTM

Гібридна модель поєднує:
1. **CNN (Conv1D):** Вилучає локальні просторово-часові ознаки та взаємозв'язки між різними метеопараметрами (інтенсивність випромінювання, температура, вологість).
2. **LSTM:** Моделює тривалі часові залежності та динаміку зміни генерації протягом доби.

### Приклад коду моделі (Keras / TensorFlow)

```python
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, LSTM, Dense, Dropout, Flatten

def build_cnn_lstm_model(input_shape, output_horizon):
    """
    input_shape: (lookback_steps, num_features)
    output_horizon: кількість кроків прогнозування вперед (наприклад, 24 для 24 годин)
    """
    model = Sequential([
        # Шар CNN для вилучення ознак
        Conv1D(filters=64, kernel_size=3, activation='relu', input_shape=input_shape),
        MaxPooling1D(pool_size=2),
        Dropout(0.2),
        
        # Шар LSTM для часової послідовності
        LSTM(units=100, activation='tanh', return_sequences=False),
        Dropout(0.2),
        
        # Повнозв'язні шари для виходу
        Dense(units=50, activation='relu'),
        Dense(units=output_horizon)  # Прогнозовані значення генерації
    ])
    
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model
```

## Конвеєр підготовки даних (Data Pipeline)

Для передачі в CNN-LSTM вхідні дані мають бути перетворені у 3D-тензор: `(кількість_зразків, lookback_steps, num_features)`.

### Створення ковзного вікна

```python
import numpy as np

def create_sliding_windows(data, target, lookback, horizon):
    """
    data: масив ознак (history_generation + weather_forecasts) shape (N, num_features)
    target: масив цільової генерації shape (N,)
    """
    X, y = [], []
    for i in range(len(data) - lookback - horizon + 1):
        X.append(data[i:(i + lookback)])
        y.append(target[(i + lookback):(i + lookback + horizon)])
    return np.array(X), np.array(y)
```

## Метрики оцінки якості

Для оцінки моделі використовуються такі метрики:
1. **MAE (Mean Absolute Error):**
   $$MAE = \frac{1}{n} \sum_{i=1}^{n} |y_i - \hat{y}_i|$$
2. **RMSE (Root Mean Squared Error):**
   $$RMSE = \sqrt{\frac{1}{n} \sum_{i=1}^{n} (y_i - \hat{y}_i)^2}$$
3. **MAPE (Mean Absolute Percentage Error):**
   $$MAPE = \frac{100\%}{n} \sum_{i=1}^{n} \left| \frac{y_i - \hat{y}_i}{y_i} \right|$$
