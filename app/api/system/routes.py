from fastapi import APIRouter, Depends
from app.services.health_check import HealthCheckService
from app.core.dependencies import get_health_service

system_router = APIRouter(tags=["System"])

@system_router.get("/health-check", summary="System status check")
async def health_check(service: HealthCheckService = Depends(get_health_service)):
    return await service.check_health()
