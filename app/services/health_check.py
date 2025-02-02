from datetime import datetime

class HealthCheckService:
    async def check_health(self) -> dict:
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
        }
