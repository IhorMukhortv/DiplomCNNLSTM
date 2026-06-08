from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class TelemetryCreate(BaseModel):
    """Схема валідації вхідних даних телеметрії ФЕС та метеорологічних параметрів."""
    timestamp: datetime = Field(..., description="Часова мітка запису в UTC")
    temperature_2m: float = Field(..., description="Температура повітря на висоті 2 м, °C")
    relative_humidity_2m: float = Field(..., description="Відносна вологість повітря, %", ge=0.0, le=100.0)
    cloud_cover: float = Field(..., description="Загальна хмарність, %", ge=0.0, le=100.0)
    direct_normal_irradiance: float = Field(..., description="Пряма нормальна інсоляція (DNI), Вт/м²", ge=0.0)
    diffuse_horizontal_irradiance: float = Field(..., description="Дифузна горизонтальна інсоляція (DHI), Вт/м²", ge=0.0)
    global_horizontal_irradiance: float = Field(..., description="Глобальна горизонтальна інсоляція (GHI), Вт/м²", ge=0.0)
    active_power_kw: float = Field(..., description="Фактична вихідна активна потужність ФЕС, кВт", ge=0.0)


class TelemetryResponse(TelemetryCreate):
    """Схема відповіді для підтвердження успішного запису телеметрії."""
    model_config = ConfigDict(from_attributes=True)
