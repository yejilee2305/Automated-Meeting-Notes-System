from fastapi import FastAPI

from app.config import settings
from app.routers import health, upload

# create the app instance
app = FastAPI(
    title=settings.app_name,
    description="API for processing meeting recordings into actionable notes",
    version="0.1.0",
)

# hook up our routers
app.include_router(health.router)
app.include_router(upload.router, prefix="/api")
