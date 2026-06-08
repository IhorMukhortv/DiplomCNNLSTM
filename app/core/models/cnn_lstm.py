import logging
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Conv1D, MaxPooling1D, LSTM, Dense, Dropout

logger = logging.getLogger(__name__)


def build_cnn_lstm_model(
    input_shape: tuple,
    conv_filters: int = 64,
    kernel_size: int = 3,
    pool_size: int = 2,
    lstm_units: int = 50,
    dropout_rate: float = 0.2,
    learning_rate: float = 0.001
) -> Model:
    """
    Будує та компілює гібридну модель CNN-LSTM для короткострокового прогнозування генерації ФЕС.

    Параметри:
        input_shape: Кортеж (lookback, num_features), що описує вхідну розмірність.
        conv_filters: Кількість фільтрів для одновимірного згорткового шару (Conv1D).
        kernel_size: Розмір ядра згортки.
        pool_size: Розмір вікна субдискретизації (MaxPooling1D).
        lstm_units: Кількість рекурентних осередків LSTM.
        dropout_rate: Коефіцієнт регуляризації Dropout для запобігання перенавчанню.
        learning_rate: Швидкість навчання для оптимізатора Adam.

    Повертає:
        Компіловану модель tf.keras.Model.
    """
    logger.info(
        f"Побудова моделі CNN-LSTM: input_shape={input_shape}, "
        f"conv_filters={conv_filters}, kernel_size={kernel_size}, "
        f"pool_size={pool_size}, lstm_units={lstm_units}, dropout={dropout_rate}"
    )

    inputs = Input(shape=input_shape, name="input_features")

    # 1. Шари CNN для аналізу локальних взаємозв'язків погодних чинників
    x = Conv1D(
        filters=conv_filters,
        kernel_size=kernel_size,
        activation="relu",
        padding="same",
        name="conv_extractor"
    )(inputs)
    
    x = MaxPooling1D(
        pool_size=pool_size,
        name="max_pooling"
    )(x)

    # 2. Шар LSTM для моделювання довгострокової часової динаміки
    x = LSTM(
        units=lstm_units,
        activation="tanh",
        return_sequences=False,
        name="lstm_temporal"
    )(x)

    # 3. Регуляризація та повнозв'язний шар відображення ознак
    x = Dropout(rate=dropout_rate, name="dropout_reg")(x)
    x = Dense(units=32, activation="relu", name="dense_dense")(x)

    # 4. Вихідний регресійний шар для прогнозування активної потужності (кВт)
    outputs = Dense(units=1, name="output_power")(x)

    model = Model(inputs=inputs, outputs=outputs, name="CNN_LSTM_PV_Forecaster")

    # Компіляція моделі з оптимізатором Adam та функцією втрат MSE
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="mse",
        metrics=["mae"]
    )

    logger.info("Модель CNN-LSTM успішно побудовано та скомпільовано.")
    return model
