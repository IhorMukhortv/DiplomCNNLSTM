from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, Float


class Base(DeclarativeBase):
    """Базовий клас для декларативних моделей SQLAlchemy."""
    pass


class PVTelemetry(Base):
    """ORM-модель для збереження телеметрії сонячної генерації ФЕС та погодних параметрів."""
    __tablename__ = "pv_telemetry"

    # У TimescaleDB колонка часу є обов'язковим первинним ключем (або його частиною)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        index=True,
        doc="Часова мітка запису в UTC"
    )
    
    temperature_2m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Температура повітря на висоті 2 м, °C"
    )
    
    relative_humidity_2m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Відносна вологість повітря на висоті 2 м, %"
    )
    
    cloud_cover: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Загальна хмарність, %"
    )
    
    direct_normal_irradiance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Пряма нормальна інсоляція (DNI), Вт/м²"
    )
    
    diffuse_horizontal_irradiance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Дифузна горизонтальна інсоляція (DHI), Вт/м²"
    )
    
    global_horizontal_irradiance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Глобальна горизонтальна інсоляція (GHI), Вт/м²"
    )
    
    active_power_kw: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Фактична вихідна активна потужність ФЕС, кВт"
    )
