from datetime import datetime, timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.infrastructure.db.session import get_db
from app.infrastructure.db.models import PVTelemetry

# Використовуємо pytest-asyncio та aiohttp/httpx для асинхронного тестування


@pytest.fixture
def mock_db():
    """Фікстура для створення моку сесії бази даних."""
    db = AsyncMock()
    # add є синхронним методом в SQLAlchemy Session, тому використовуємо MagicMock
    db.add = MagicMock()
    return db



@pytest.fixture
async def client(mock_db):
    """Фікстура для отримання асинхронного клієнта FastAPI з перевантаженою сесією БД."""
    # Перевантажуємо залежність get_db для використання нашого моку
    app.dependency_overrides[get_db] = lambda: mock_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac
        
    # Очищуємо перевантажені залежності після закінчення тесту
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_health_check(client):
    """Перевіряє роботу кореневого health-check ендпоінту."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "system" in data
    assert "version" in data


@pytest.mark.anyio
async def test_create_telemetry_success(client, mock_db):
    """Перевіряє успішний запис нових телеметричних даних ФЕС."""
    # Налаштовуємо мок для імітації успішного збереження
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    
    payload = {
        "timestamp": "2026-06-08T12:00:00Z",
        "temperature_2m": 24.5,
        "relative_humidity_2m": 55.0,
        "cloud_cover": 20.0,
        "direct_normal_irradiance": 750.0,
        "diffuse_horizontal_irradiance": 120.0,
        "global_horizontal_irradiance": 800.0,
        "active_power_kw": 22.4
    }
    
    response = await client.post("/api/v1/telemetry/", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["temperature_2m"] == 24.5
    assert data["active_power_kw"] == 22.4
    
    # Перевіряємо виклики методів сесії БД
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.anyio
async def test_predict_insufficient_data(client, mock_db):
    """Перевіряє, що модель повертає помилку 400 при недостатній кількості записів у БД."""
    # Налаштовуємо мок на повернення 5 записів замість 24
    mock_records = [
        PVTelemetry(
            timestamp=datetime(2026, 6, 8, i, 0, 0),
            temperature_2m=20.0,
            relative_humidity_2m=50.0,
            cloud_cover=10.0,
            direct_normal_irradiance=500.0,
            diffuse_horizontal_irradiance=100.0,
            global_horizontal_irradiance=600.0,
            active_power_kw=15.0
        )
        for i in range(5)
    ]
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = mock_records
    mock_db.execute = AsyncMock(return_value=mock_execute_result)
    
    response = await client.get("/api/v1/predict/")
    assert response.status_code == 400
    
    data = response.json()
    assert "Недостатньо даних" in data["detail"]


@pytest.mark.anyio
async def test_predict_success(client, mock_db):
    """Перевіряє успішний розрахунок прогнозу при наявності 24 записів у БД."""
    # Створюємо 24 тестові записи в базі
    mock_records = [
        PVTelemetry(
            timestamp=datetime(2026, 6, 8, i, 0, 0),
            temperature_2m=20.0 + i * 0.1,
            relative_humidity_2m=60.0 - i * 0.5,
            cloud_cover=10.0,
            direct_normal_irradiance=600.0,
            diffuse_horizontal_irradiance=100.0,
            global_horizontal_irradiance=700.0,
            active_power_kw=12.0 + i * 0.5
        )
        for i in range(24)
    ]
    
    mock_execute_result = MagicMock()
    # scalars().all() має повернути список із 24 елементів
    mock_execute_result.scalars.return_value.all.return_value = mock_records
    mock_db.execute = AsyncMock(return_value=mock_execute_result)
    
    response = await client.get("/api/v1/predict/")
    assert response.status_code == 200
    
    data = response.json()
    assert "predicted_active_power_kw" in data
    assert "forecast_timestamp" in data
    assert "input_last_timestamp" in data
    
    # Потужність не може бути від'ємною
    assert data["predicted_active_power_kw"] >= 0.0


@pytest.mark.anyio
async def test_retrain_endpoint_insufficient(client, mock_db):
    """Перевіряє, що роут донавчання повертає помилку 400 при недостатній кількості записів у БД."""
    # Повертаємо 5 записів замість 25 необхідних
    mock_records = [
        PVTelemetry(
            timestamp=datetime(2026, 6, 8, i, 0, 0),
            temperature_2m=20.0,
            relative_humidity_2m=50.0,
            cloud_cover=10.0,
            direct_normal_irradiance=500.0,
            diffuse_horizontal_irradiance=100.0,
            global_horizontal_irradiance=600.0,
            active_power_kw=15.0
        )
        for i in range(5)
    ]
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = mock_records
    mock_db.execute = AsyncMock(return_value=mock_execute_result)
    
    response = await client.post("/api/v1/predict/retrain", json={"limit_hours": 30, "epochs": 2})
    assert response.status_code == 400
    data = response.json()
    assert "Недостатньо даних" in data["detail"]


@pytest.mark.anyio
async def test_retrain_endpoint_success(client, mock_db, monkeypatch, tmp_path):
    """Перевіряє успішне виконання донавчання через API роут."""
    # Тимчасовий реєстр моделей, щоб не зіпсувати основний saved_model.keras
    temp_model_path = tmp_path / "temp_saved_model.keras"
    from app.infrastructure.storage.model_registry import model_registry
    monkeypatch.setattr(model_registry, "model_path", str(temp_model_path))
    monkeypatch.setattr(model_registry, "_model", None)

    # 30 записів для успіху
    mock_records = [
        PVTelemetry(
            timestamp=datetime(2026, 6, 8, 0, 0, 0) + timedelta(hours=i),
            temperature_2m=20.0,
            relative_humidity_2m=50.0,
            cloud_cover=10.0,
            direct_normal_irradiance=500.0,
            diffuse_horizontal_irradiance=100.0,
            global_horizontal_irradiance=600.0,
            active_power_kw=15.0
        )
        for i in range(30)
    ]
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = mock_records
    mock_db.execute = AsyncMock(return_value=mock_execute_result)
    
    payload = {
        "limit_hours": 30,
        "epochs": 2,
        "learning_rate": 0.0001,
        "batch_size": 10
    }
    
    response = await client.post("/api/v1/predict/retrain", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"
    assert data["records_used"] == 30
    assert "loss_before" in data
    assert "loss_after" in data
    assert len(data["loss_history"]) == 2

