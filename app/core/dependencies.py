from app.services.health_check import HealthCheckService

def get_health_service() -> HealthCheckService:
    return HealthCheckService()
