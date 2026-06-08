import numpy as np


def calculate_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Обчислює середню абсолютну помилку (MAE).

    $$MAE = \\frac{1}{n} \\sum_{i=1}^n |y_i - \\hat{y}_i|$$
    """
    return float(np.mean(np.abs(y_true - y_pred)))


def calculate_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Обчислює середньоквадратичну помилку (RMSE).

    $$RMSE = \\sqrt{\\frac{1}{n} \\sum_{i=1}^n (y_i - \\hat{y}_i)^2}$$
    """
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def calculate_mape(y_true: np.ndarray, y_pred: np.ndarray, threshold: float = 0.2) -> float:
    """
    Обчислює середню абсолютну відсоткову помилку (MAPE).
    
    $$MAPE = \\frac{100\\%}{n} \\sum_{i=1}^n \\left| \\frac{y_i - \\hat{y}_i}{y_i} \\right|$$

    Для уникнення ділення на нуль та некоректних відсоткових помилок під час нічного
    часу або низької генерації, розрахунок проводиться лише для значень, де
    фактична генерація перевищує встановлений поріг (за замовчуванням 0.2 кВт).
    """
    y_true_flat = y_true.flatten()
    y_pred_flat = y_pred.flatten()
    
    # Фільтрація значень нижче порогу
    mask = y_true_flat >= threshold
    if not np.any(mask):
        return 0.0
        
    return float(np.mean(np.abs((y_true_flat[mask] - y_pred_flat[mask]) / y_true_flat[mask])) * 100.0)


def evaluate_forecast(y_true: np.ndarray, y_pred: np.ndarray, threshold: float = 0.2) -> dict:
    """
    Обчислює всі метрики якості прогнозу (MAE, RMSE, MAPE) та повертає їх у вигляді словника.
    """
    return {
        "mae": calculate_mae(y_true, y_pred),
        "rmse": calculate_rmse(y_true, y_pred),
        "mape": calculate_mape(y_true, y_pred, threshold)
    }
