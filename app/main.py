from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import init_db
from app.errors import http_exception_handler, rate_limit_handler
from app.rate_limit import limiter
from app.routers import frontend, health, notifications, summary, transcription, upload


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Set up and tear down the app."""
    # create database tables on startup
    await init_db()
    yield
    # cleanup would go here if needed


# create the app instance
app = FastAPI(
    title=settings.app_name,
    description="API for processing meeting recordings into actionable notes",
    version="0.1.0",
    lifespan=lifespan,
)

# set up rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# custom error handling for better messages
app.add_exception_handler(HTTPException, http_exception_handler)

# serve static files (css, js)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# hook up our routers
app.include_router(frontend.router)  # serves the UI at /
app.include_router(health.router)
app.include_router(upload.router, prefix="/api")
app.include_router(transcription.router, prefix="/api")
app.include_router(summary.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
