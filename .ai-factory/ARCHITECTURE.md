# Архітектура: Структуровані модулі за технічними шарами (Structured Modules - Technical Layers)

## Огляд
Цей архітектурний шаблон ділить програмний застосунок на логічні технічні шари в межах єдиного модуля. Шари організовані зверху вниз за принципом зменшення абстракції: API (зовнішній інтерфейс) -> Core/Domain (бізнес-логіка та ML-моделі) -> Infrastructure (доступ до бази даних та зовнішніх систем). Такий підхід забезпечує чітке розділення обов'язків (Separation of Concerns), простоту в супроводі, а також легкість написання модульних та інтеграційних тестів.

## Обґрунтування вибору
- **Тип проекту:** Комп'ютерно-інтегрована система короткострокового прогнозування ФЕС із нейромережевим ядром та REST API.
- **Технологічний стек:** Python, FastAPI, TensorFlow/Keras, PostgreSQL (TimescaleDB), SQLAlchemy.
- **Основний фактор:** Проект потребує простого, але надійного способу інтеграції обробки даних (Data Pipeline), навчання нейромережі та обслуговування запитів користувачів через API без зайвої перевантаженості коду абстракціями, які властиві DDD/Clean Architecture на ранніх етапах.

## Структура папок (Folder Structure)
```
app/
│
├── api/                     # Презентаційний шар (FastAPI)
│   ├── v1/                  # Версія API 1
│   │   ├── endpoints/       # Роути для станцій, прогнозів, моделей
│   │   └── router.py        # Головний роутер версії 1
│   ├── dependencies.py      # FastAPI Depends (сесії БД, сервіси)
│   └── schemas.py           # Валідація даних Pydantic
│
├── core/                    # Шар бізнес-логіки та ML
│   ├── forecasting/         # Модуль CNN-LSTM
│   │   ├── model.py         # Опис архітектури мережі CNN-LSTM
│   │   ├── trainer.py       # Логіка навчання та валідації
│   │   └── pipeline.py      # Передобробка та ковзне вікно
│   ├── config.py            # Налаштування додатку (Pydantic Settings)
│   └── exceptions.py        # Кастомні бізнес-винятки
│
├── infrastructure/          # Шар інфраструктури та сервісів
│   ├── database/            # Підключення до БД та SQLAlchemy моделі
│   │   ├── session.py       # Асинхронна сесія БД
│   │   └── models.py        # Опис таблиць (станції, генерація)
│   ├── weather/             # Інтеграція з погодними сервісами
│   │   └── client.py        # HTTP-клієнт для прогнозів погоди
│   └── storage/             # Робота з файловою системою (моделі Keras)
│       └── model_registry.py# Завантаження та збереження моделей
│
└── main.py                  # Ініціалізація додатку FastAPI
```

## Правила залежностей (Dependency Rules)
Кожен шар може залежати лише від шарів, що знаходяться нижче або на одному рівні.
- ✅ `api` -> `core` (дозволено: роути викликають прогнозування та бізнес-логіку)
- ✅ `api` -> `infrastructure` (дозволено для ініціалізації сесій бази даних)
- ✅ `infrastructure` -> `core` (дозволено: реалізація інтерфейсів та моделей даних)
- ❌ `core` -> `api` (заборонено: бізнес-логіка не повинна знати про FastAPI чи HTTP)
- ❌ `core` -> `infrastructure` (заборонено: домен не має залежати від конкретної реалізації БД або метеоклієнта)

## Комунікація між шарами
- Запити приходять у шар `api` через HTTP.
- Шар `api` викликає функції або класи з шару `core` (наприклад, для запуску прогнозування).
- Дані передаються між шарами за допомогою Pydantic-схем або вбудованих типів Python.
- Шар `core` використовує абстракції інфраструктури, реалізовані у `infrastructure`.

## Основні принципи
1. **Асинхронність на першому місці:** Усі операції введення-виведення (I/O) — запити до БД, запити до API погоди — мають бути асинхронними (`async`/`await`).
2. **Єдине джерело правди для конфігурацій:** Усі налаштування зчитуються через `app/core/config.py` за допомогою `pydantic-settings`.
3. **Ізоляція ML-моделей:** Код навчання та прогнозування (`app/core/forecasting/`) не повинен переплітатися з кодом збереження у базу даних.

## Приклади коду

### Опис роуту API (app/api/v1/endpoints/forecasts.py)
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db
from app.api.schemas import ForecastRequest, ForecastResponse
from app.core.forecasting.pipeline import ForecastPipeline

router = APIRouter()

@router.post("/predict", response_model=ForecastResponse)
async def predict_generation(
    request: ForecastRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        pipeline = ForecastPipeline(db)
        prediction = await pipeline.run(request.station_id, request.target_time)
        return ForecastResponse(prediction=prediction)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Абстракція та реалізація інфраструктури (app/infrastructure/weather/client.py)
```python
import httpx
from app.core.exceptions import WeatherServiceError

class WeatherClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_forecast(self, lat: float, lon: float) -> dict:
        url = f"https://api.weather.com/v1/forecast?lat={lat}&lon={lon}&key={self.api_key}"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise WeatherServiceError(f"Помилка отримання прогнозу погоди: {e}")
```

## Антишаблони
- ❌ **Пряме використання синхронних клієнтів (наприклад, `requests`) в асинхронних роутах.** Це блокує єдиний потік event loop у FastAPI. Завжди використовуйте `httpx.AsyncClient` або аналогічні асинхронні клієнти.
- ❌ **Збереження стану ML-моделі у глобальних змінних без механізмів синхронізації.** Це може призвести до race conditions при паралельних запитах прогнозування.
