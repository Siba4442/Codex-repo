# backend/main.py
# Main app setup

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import health, phase1, phase2, phase3, phase4, jobs
from backend.config import get_settings
from backend.services.storage import get_storage_service
from backend.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run when app starts and stops
    # Setup: create folders and database
    get_storage_service()
    init_db()
    yield
    # Cleanup happens here if needed


def create_app() -> FastAPI:
    # Create the FastAPI app
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes
    app.include_router(health.router)
    app.include_router(phase1.router)
    app.include_router(phase2.router)
    app.include_router(phase3.router)
    app.include_router(phase4.router)
    app.include_router(jobs.router)

    return app


# Create the app instance
app = create_app()


@app.get("/")
async def root():
    # Basic info endpoint
    settings = get_settings()
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
