from fastapi import FastAPI
from app.core.config import settings
from app.routes import register_routes

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.APP_VERSION,
        docs_url=settings.DOCS_URL,
        redoc_url=settings.REDOC_URL,
    )
    
    register_routes(app)
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.SERVER_HOST, port=settings.SERVER_PORT, reload=settings.AUTO_RELOAD)
