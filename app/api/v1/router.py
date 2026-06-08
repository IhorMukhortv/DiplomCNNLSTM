from fastapi import APIRouter
from app.api.v1.endpoints import telemetry, predict

api_router = APIRouter()
api_router.include_router(telemetry.router, prefix="/telemetry", tags=["telemetry"])
api_router.include_router(predict.router, prefix="/predict", tags=["predict"])
