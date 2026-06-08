import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.infrastructure.db.session import get_db
from app.infrastructure.db.models import PVTelemetry
from app.schemas.telemetry import TelemetryCreate, TelemetryResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=TelemetryResponse, status_code=status.HTTP_201_CREATED)
async def create_telemetry(data: TelemetryCreate, db: AsyncSession = Depends(get_db)):
    """
    Записує новий годинний рядок телеметрії ФЕС та метео-параметрів у базу даних.
    """
    logger.debug(f"Отримано нову телеметрію за час: {data.timestamp}")
    
    db_telemetry = PVTelemetry(
        timestamp=data.timestamp,
        temperature_2m=data.temperature_2m,
        relative_humidity_2m=data.relative_humidity_2m,
        cloud_cover=data.cloud_cover,
        direct_normal_irradiance=data.direct_normal_irradiance,
        diffuse_horizontal_irradiance=data.diffuse_horizontal_irradiance,
        global_horizontal_irradiance=data.global_horizontal_irradiance,
        active_power_kw=data.active_power_kw
    )
    
    db.add(db_telemetry)
    try:
        await db.commit()
        await db.refresh(db_telemetry)
        return db_telemetry
    except IntegrityError as e:
        await db.rollback()
        logger.warning(f"Спроба запису дублікату мітки часу {data.timestamp}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Запис із цією часовою міткою вже присутній у базі даних."
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Помилка при збереженні телеметрії: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутрішня помилка сервера при збереженні даних."
        )
